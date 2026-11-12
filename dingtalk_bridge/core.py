from __future__ import annotations
import hashlib
import fcntl
import json
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from .text_limits import PERSONAL_TEXT_UNITS, utf16_units
from .rejection import read_length_rejection


class BridgeError(Exception):
    pass


class DWSRequestRejected(BridgeError):
    """Explicit server invalid-request response, never a timeout inference."""
    def __init__(self, diagnostic):
        super().__init__('PARAM_ERROR')
        self.diagnostic = diagnostic


class DWS:
    def __init__(self, root, config):
        self.root, self.config = Path(root), config
        self.binary = str((self.root / config['binary']).resolve())

    def call(self, args):
        try:
            p = subprocess.run([self.binary, *args, '--profile', self.config['profile'],
                                '--format', 'json'], cwd=self.root, capture_output=True,
                               text=True, timeout=90)
        except subprocess.TimeoutExpired as e:
            raise BridgeError('DWS timeout; reconcile before retry') from e
        try:
            data = json.loads(p.stdout or p.stderr)
        except ValueError as e:
            raise BridgeError('DWS returned no valid JSON') from e
        if p.returncode or data.get('success') in (False, 'false') or data.get('ok') is False:
            error = data.get('error', {})
            if error.get('reason') == 'invalid_request' and error.get('server_error_code') == 'PARAM_ERROR':
                raise DWSRequestRejected({'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR'})
            raise BridgeError(str(error.get('server_error_code') or error.get('reason') or 'DWS business failure'))
        if 'outcome' in data and isinstance(data.get('data'), dict):
            data = data['data']
        if data.get('success') in (False, 'false') or data.get('ok') is False:
            raise BridgeError('DWS inner business failure')
        return data

    def upload_image(self, relative_path):
        # The companion only adds a CHAT_IMAGE leaf to the pinned official CLI.
        # Authentication, profile selection and the upload protocol stay in DWS.
        binary = self.config.get('imageUploadBinary')
        if not binary:
            raise BridgeError('Native image upload is not configured')
        uploader = DWS(self.root, {**self.config, 'binary': binary})
        data = uploader.call(['chat', 'bridge-image-upload', '--file', relative_path, '--yes'])
        media_id = data.get('mediaIdV2')
        if (not isinstance(media_id, str) or not media_id.startswith('$') or
                data.get('bizType') != 'CHAT_IMAGE' or data.get('compressed') is not False):
            raise BridgeError('Invalid native image upload receipt; message not sent')
        return media_id


class Bridge:
    """One routed conversation worker. No runtime dependency or automatic replies."""
    def __init__(self, root, config, dws=None, state_name=None):
        self.root, self.config = Path(root).resolve(), config
        self.local = self.root / 'local/runtime'
        if state_name is not None:
            if len(state_name)!=64 or any(c not in '0123456789abcdef' for c in state_name):
                raise ValueError('Invalid state name')
            self.local = self.local / 'routes' / state_name
        self.local.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.process_lock = (self.local / "process.lock").open("a")
        try:
            fcntl.flock(self.process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            self.process_lock.close()
            raise BridgeError("Another bridge owns this state directory") from e
        self.lock = threading.RLock()
        self.event_condition = threading.Condition(self.lock)
        self.event_waiters = threading.BoundedSemaphore(16)
        self.stopping = False
        self.sync_lock = threading.Lock()
        self.download_lock = threading.Lock()
        self.dws = dws or DWS(self.root, config)
        self.db = sqlite3.connect(self.local / 'bridge.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, message_id TEXT UNIQUE NOT NULL,
            body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS deliveries (
            key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
            state TEXT NOT NULL, task_id TEXT, message_id TEXT, error TEXT);
          CREATE TABLE IF NOT EXISTS rejection_audit (
            key TEXT PRIMARY KEY, before_json TEXT NOT NULL, evidence_json TEXT NOT NULL,
            evidence_sha256 TEXT NOT NULL, source TEXT NOT NULL, recorded_at REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS image_uploads (
            key TEXT PRIMARY KEY, state TEXT NOT NULL, media_id TEXT, error TEXT);
        ''')
        scope = json.dumps([config['profile'], config['group']])
        prior = self.db.execute('SELECT value FROM meta WHERE key="scope"').fetchone()
        if prior and prior[0] != scope:
            self.db.close()
            fcntl.flock(self.process_lock, fcntl.LOCK_UN)
            self.process_lock.close()
            raise BridgeError('Database belongs to a different profile/conversation')
        self.db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('scope', scope))
        # A crash after reservation cannot be assumed not sent.
        self.db.execute('UPDATE deliveries SET state="outcome_unknown" WHERE state="executing"')
        self.db.execute('UPDATE deliveries SET state="upload_unknown" WHERE state="uploading"')
        self.db.execute('UPDATE image_uploads SET state="outcome_unknown" WHERE state="uploading"')
        self.db.commit()
        (self.local / 'bridge.sqlite3').chmod(0o600)

    def target_args(self):
        if self.config.get('conversationType','group')=='direct':
            return ['--open-dingtalk-id',self.config['peerOpenDingTalkId']]
        return ['--group',self.config['group']]

    def validate_target(self):
        d = self.dws.call(['chat', '+conversation-info', *self.target_args()])
        info = d.get('result', {}).get('conversationInfo', {})
        if info.get('openConversationId') != self.config['group']:
            raise BridgeError('Target identity mismatch')
        return True

    def sync(self, deep=False):
        with self.sync_lock:
            now = datetime.now(timezone.utc)
            with self.lock:
                row = self.db.execute('SELECT value FROM meta WHERE key="watermark"').fetchone()
            start = datetime.fromisoformat(row[0]) - timedelta(minutes=5) if row else now - timedelta(days=1)
            with self.lock:
                last_deep = self.db.execute('SELECT value FROM meta WHERE key="last_deep_sync"').fetchone()
            deep = deep or not last_deep or now-datetime.fromisoformat(last_deep[0]) >= timedelta(minutes=30)
            if deep:
                start = min(start, now-timedelta(hours=24))
            data = self.dws.call(['chat', '+chat-messages', *self.target_args(),
                '--start', start.isoformat(), '--end', now.isoformat(), '--order', 'asc',
                '--page-all', '--page-limit', '20', '--max-items', '1000', '--limit', '50'])
            if not isinstance(data.get('messages'),list):
                raise BridgeError('Missing history messages; watermark unchanged')
            inserted = 0
            with self.lock, self.db:
                for msg in data.get('messages', []):
                    mid = msg.get('messageId')
                    if not mid or msg.get('conversationId') != self.config['group']:
                        raise BridgeError('Missing message identity or unexpected conversation')
                    own = self.config.get('selfSenderId')
                    event = {'event': 'new_message', 'source': 'dws_history', 'message_id': mid,
                             'conversation_id': self.config['group'], 'account_id':self.config.get('accountId','default'),
                             'conversation_type':self.config.get('conversationType','group'), 'chat': self.config['name'],
                             'sender': msg.get('sender'), 'sender_id': msg.get('senderId'),
                             'content': msg.get('text', ''), 'timestamp': msg.get('createTime'),
                             'from_self': msg.get('senderId') == own if own and msg.get('senderId') else None,
                             'attachments': msg.get('resourceRefs', []), 'raw': msg}
                    # Never collapse equal bodies: two equal messages can be intentional.
                    cur = self.db.execute('INSERT OR IGNORE INTO events(message_id,body) VALUES (?,?)',
                                          (mid, json.dumps(event, ensure_ascii=False)))
                    inserted += cur.rowcount
                complete = data.get('complete') is True and not data.get('partial') and not data.get('failedCount')
                if complete:
                    self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', ('watermark', now.isoformat()))
                    if deep:
                        self.db.execute('INSERT OR REPLACE INTO meta VALUES ("last_deep_sync",?)',(now.isoformat(),))
                self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                    ('last_sync', json.dumps({'at': now.isoformat(), 'complete': complete, 'inserted': inserted, 'deep':deep})))
                self.db.commit()
                if inserted:self.event_condition.notify_all()
            return {'inserted': inserted, 'complete': complete, 'count': data.get('count'),
                    'source': 'history_poll', 'deep':deep,
                    'other_member_events_observed':self.health()['other_member_events']}

    def events(self, after=0, limit=100, wait_seconds=0):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('Invalid cursor/limit')
        if type(wait_seconds) not in (int,float) or not 0<=wait_seconds<=30:
            raise ValueError('wait_seconds must be 0..30')
        acquired=False
        try:
            if wait_seconds:
                acquired=self.event_waiters.acquire(blocking=False)
                if not acquired:raise ValueError('Too many waiting consumers; retry with backoff')
            deadline=time.monotonic()+wait_seconds
            with self.event_condition:
                while True:
                    rows = self.db.execute('SELECT seq,body FROM events WHERE seq>? ORDER BY seq LIMIT ?',
                                           (after, limit)).fetchall()
                    remaining=deadline-time.monotonic()
                    if rows or remaining<=0 or self.stopping:break
                    self.event_condition.wait(remaining)
        finally:
            if acquired:self.event_waiters.release()
        return [{'seq': r['seq'], **json.loads(r['body'])} for r in rows]

    def delivery(self, key):
        with self.lock:
            row = self.db.execute('SELECT key,state,task_id,message_id,error FROM deliveries WHERE key=?', (key,)).fetchone()
            upload = self.db.execute('SELECT state FROM image_uploads WHERE key=?', (key,)).fetchone()
            rejection = self.db.execute('SELECT source,evidence_sha256 FROM rejection_audit WHERE key=?', (key,)).fetchone()
        return {**dict(row), **({'upload_state': upload[0], 'image_delivery': 'native'} if upload else {}),
                **({'rejection': dict(rejection)} if rejection else {})} if row else None

    def _record_rejection(self, key, raw, sha256, source):
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM deliveries WHERE key=?', (key,)).fetchone()
            if not row or row['task_id'] or row['message_id'] or row['state'] not in {'executing', 'outcome_unknown'}:
                raise ValueError('Only an unaccepted send can become rejected')
            self.db.execute('INSERT INTO rejection_audit VALUES (?,?,?,?,?,?)',
                (key, json.dumps(dict(row), ensure_ascii=False), raw.decode(), sha256, source, time.time()))
            self.db.execute('UPDATE deliveries SET state="rejected",error="PARAM_ERROR" WHERE key=?', (key,))
        return self.delivery(key)

    def _record_unknown(self, key, error):
        # Another HTTP request may have confirmed this task while our status
        # query was still in flight. A late error must not undo a terminal row.
        with self.lock, self.db:
            self.db.execute('UPDATE deliveries SET state="outcome_unknown",error=? WHERE key=? '
                            'AND state NOT IN ("confirmed","failed","rejected")', (str(error), key))
        return self.delivery(key)

    def send(self, key, text=None, file=None, image=None, reply_to=None):
        if not isinstance(key, str) or not key or len(key) > 128:
            raise ValueError('A stable idempotency key is required (1-128 chars)')
        if sum(x is not None for x in (text, file, image)) != 1:
            raise ValueError('Provide exactly one of text, file or image')
        if reply_to is not None and (text is None or not isinstance(reply_to, str) or
                                     not reply_to.strip() or reply_to != reply_to.strip() or len(reply_to) > 2048):
            raise ValueError('reply_to requires text and a nonempty message ID (up to 2048 chars)')
        payload = {}
        if text is not None:
            if not isinstance(text, str) or not text or len(text.encode()) > 65536 or '![' in text:
                raise ValueError('Use plain text up to 64 KiB; inline images need a separate verified route')
            payload = {'kind': 'text', 'text': text}
            if reply_to is not None:
                payload['reply_to'] = reply_to
        else:
            f = Path(image if image is not None else file)
            if f.is_absolute() or '..' in f.parts:
                raise ValueError('File must be a safe project relative path')
            source = (self.root / f).resolve()
            allowed = [(self.root / 'fixtures').resolve(), (self.root / 'local/outbox').resolve()]
            if not any(source.is_relative_to(p) for p in allowed) or not source.is_file():
                raise ValueError('Only files in fixtures/ or local/outbox/ can be sent')
            if source.stat().st_size > 20 * 1024 * 1024:
                raise ValueError('Experimental service file limit is 20 MiB')
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if image is not None and source.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
                raise ValueError('Image mode accepts PNG/JPEG only')
            stage_name = 'image' + source.suffix.lower() if image is not None else source.name
            stage = self.local / 'staged' / digest / stage_name
            stage.parent.mkdir(parents=True, exist_ok=True)
            if not stage.exists():
                stage.write_bytes(content)
                stage.chmod(0o600)
            if stage.is_symlink() or hashlib.sha256(stage.read_bytes()).hexdigest() != digest:
                raise ValueError('Staged file integrity mismatch; no upload or send attempted')
            payload = {'kind': 'image' if image is not None else 'file', 'sha256': digest, 'name': source.name,
                       'staged': str(stage.relative_to(self.root))}
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
        with self.lock:
            row = self.db.execute('SELECT fingerprint FROM deliveries WHERE key=?', (key,)).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise ValueError('Idempotency key already belongs to another payload')
                return {**self.delivery(key), 'replayed': True}
            # Replay lookup precedes validation so old payloads stay immutable.
            if text is not None and utf16_units(text) > PERSONAL_TEXT_UNITS:
                raise ValueError('Personal text exceeds 5120 UTF-16 units; split it or send a file')
            if reply_to is not None:
                source_row = self.db.execute('SELECT body FROM events WHERE message_id=?', (reply_to,)).fetchone()
                source_event = json.loads(source_row[0]) if source_row else {}
                if (source_event.get('message_id') != reply_to or
                        source_event.get('conversation_id') != self.config['group'] or
                        source_event.get('account_id') != self.config.get('accountId', 'default') or
                        not source_event.get('sender_id')):
                    raise ValueError('reply_to must identify an observed message with a known sender in this route')
            if image is not None:
                if not self.config.get('imageUploadBinary'):
                    raise ValueError('Native image upload requires imageUploadBinary; no Markdown fallback')
                if len(content) > 2 * 1024 * 1024:
                    raise ValueError('Native image limit is 2 MiB without compression; use file mode for larger originals')
                signature = b'\x89PNG\r\n\x1a\n' if source.suffix.lower() == '.png' else b'\xff\xd8\xff'
                if not content.startswith(signature):
                    raise ValueError('Image content does not match PNG/JPEG extension')
            self.db.execute('INSERT INTO deliveries(key,fingerprint,payload,state) VALUES (?,?,?,?)',
                            (key, fingerprint, serialized, 'uploading' if image is not None else 'executing'))
            if image is not None:
                self.db.execute('INSERT INTO image_uploads(key,state) VALUES (?,"uploading")', (key,))
            self.db.commit()
        args = ['chat', '+messages-send', '--as', 'user', *self.target_args(),
                '--idempotency-key', key, '--yes']
        if reply_to is not None:
            # Official DWS resolves the source again and checks the direct peer.
            # Explicit group binds the expected conversation even for a DM.
            args = ['chat', '+messages-reply', '--as', 'user', '--group', self.config['group'],
                    '--message-id', reply_to, '--content', text, '--idempotency-key', key, '--yes']
            if self.config.get('conversationType') == 'direct':
                args += ['--open-dingtalk-id', self.config['peerOpenDingTalkId']]
        elif text is not None:
            args += ['--text', text]
        elif image is not None:
            try:
                media_id = self.dws.upload_image(payload['staged'])
                with self.lock:
                    self.db.execute('UPDATE image_uploads SET state="uploaded",media_id=? WHERE key=?', (media_id, key))
                    # Commit the send reservation before invoking DWS. A crash here
                    # is conservatively unknown; startup must never resend it.
                    self.db.execute('UPDATE deliveries SET state="executing" WHERE key=?', (key,))
                    self.db.commit()
            except Exception:
                with self.lock:
                    self.db.execute('UPDATE image_uploads SET state="outcome_unknown",error="image_upload_failed_or_unknown" WHERE key=?', (key,))
                    self.db.execute('UPDATE deliveries SET state="upload_unknown",error="Image upload failed or unknown; message not attempted" WHERE key=?', (key,))
                    self.db.commit()
                return self.delivery(key)
            args += ['--msg-type', 'image', '--media-id', media_id]
        else:
            args += ['--msg-type', 'file', '--file', payload['staged']]
        try:
            data = self.dws.call(args)
            task = data.get('sendReceipt', {}).get('openTaskId')
            if not task and reply_to is not None:
                # v1.0.67 group quote returns raw MCP data; DM quote projects a
                # sendReceipt. Only inspect official response wrappers, never the
                # referenced source message. Ambiguous receipts remain unknown.
                tasks = set()
                def collect(value):
                    if isinstance(value, dict):
                        for name in ('openTaskId', 'taskId'):
                            candidate = value.get(name)
                            if isinstance(candidate, str) and candidate.strip():
                                tasks.add(candidate.strip())
                        for name in ('result', 'data', 'response', 'content', 'message'):
                            collect(value.get(name))
                    elif isinstance(value, list):
                        for item in value:
                            collect(item)
                collect(data)
                if len(tasks) == 1:
                    task = tasks.pop()
            if not isinstance(task, str) or not task.strip():
                raise BridgeError('No send task ID; do not resend')
            with self.lock:
                self.db.execute('UPDATE deliveries SET state="submitted",task_id=? WHERE key=?', (task, key))
                self.db.commit()
            return self.reconcile(key)
        except DWSRequestRejected as e:
            # Rejection of a status query cannot prove rejection of an already
            # submitted send. Preserve its task ID and uncertainty.
            if not self.delivery(key)['task_id']:
                raw = json.dumps(e.diagnostic, sort_keys=True).encode()
                return self._record_rejection(key, raw, hashlib.sha256(raw).hexdigest(), 'official_error_response')
            return self._record_unknown(key, e)
        except Exception as e:
            return self._record_unknown(key, e)

    def reconcile(self, key, rejection_evidence=None):
        if rejection_evidence is not None:
            with self.lock:
                row = self.db.execute('SELECT * FROM deliveries WHERE key=?', (key,)).fetchone()
                if not row:
                    raise KeyError(key)
                audit = self.db.execute('SELECT * FROM rejection_audit WHERE key=?', (key,)).fetchone()
                original = json.loads(audit['before_json']) if audit else dict(row)
                raw, sha256 = read_length_rejection(self.root, rejection_evidence, original, self.config)
                if audit:
                    if audit['evidence_sha256'] != sha256:
                        raise ValueError('A different rejection audit already exists')
                    return self.delivery(key)
                if row['state'] != 'outcome_unknown' or row['error'] != 'PARAM_ERROR' or row['task_id'] or row['message_id']:
                    raise ValueError('Not an unresolved parameter rejection without a task ID')
                text = json.loads(row['payload'])['text']
                if self.db.execute('SELECT 1 FROM events WHERE json_extract(body,"$.content")=? LIMIT 1', (text,)).fetchone():
                    raise ValueError('Matching message history requires manual investigation')
                return self._record_rejection(key, raw, sha256, 'official_cli_log')
        item = self.delivery(key)
        if not item:
            raise KeyError(key)
        if not item['task_id'] or item['state'] in {'confirmed', 'rejected', 'failed'}:
            return item
        data = self.dws.call(['chat', '+messages-query-send-status', '--open-task-id', item['task_id']])
        result = data.get('result', {})
        status = result.get('sendStatus')
        state = 'confirmed' if status == 'SUCCESS' else 'failed' if status == 'FAILED' else 'submitted'
        ref = data.get('messageRef', {})
        if state == 'confirmed' and (ref.get('openConversationId') != self.config['group'] or not ref.get('openMessageId')):
            raise BridgeError('Delivery result identity mismatch')
        with self.lock:
            # Status calls run outside the lock. Preserve the first committed
            # terminal result when an older pending/conflicting reply arrives.
            self.db.execute('UPDATE deliveries SET state=?,message_id=?,error=NULL WHERE key=? '
                            'AND state NOT IN ("confirmed","failed","rejected")',
                            (state, ref.get('openMessageId'), key))
            self.db.commit()
        return self.delivery(key)

    def download(self, message_id, repair=False):
        with self.download_lock:
            return self._download(message_id,repair)

    def _verify_download_ledger(self, ledger, folder, cached=False):
        label = 'Cached attachment' if cached else 'Downloaded attachment'
        try:
            if (not isinstance(ledger, dict) or type(ledger.get('ok')) is not bool or
                    type(ledger.get('partial', False)) is not bool or
                    type(ledger.get('failedCount', 0)) is not int or ledger.get('failedCount', 0) < 0 or
                    not isinstance(ledger.get('downloads'), list)):
                raise ValueError('invalid ledger')
            if cached and (not ledger['ok'] or ledger.get('partial') or ledger.get('failedCount')):
                raise ValueError('incomplete cache')
            actual = set(); verified = []
            for entry in ledger['downloads']:
                if (not isinstance(entry, dict) or entry.get('resourceType') not in {'fileId', 'mediaId'} or
                        not isinstance(entry.get('resourceId'), str) or not entry['resourceId'] or
                        not isinstance(entry.get('localPath'), str) or not entry['localPath']):
                    raise ValueError('invalid resource entry')
                identity = entry['resourceType'], entry['resourceId']
                if identity in actual:raise ValueError('duplicate resource')
                actual.add(identity)
                path = (self.root / entry['localPath']).resolve()
                if not path.is_relative_to(folder.resolve()) or not path.is_file():
                    raise ValueError('unsafe or missing file')
                content = path.read_bytes(); sha = hashlib.sha256(content).hexdigest()
                if type(entry.get('sizeBytes')) is not int or entry['sizeBytes'] != len(content):
                    raise ValueError('size mismatch')
                if cached and entry.get('sha256') != sha:raise ValueError('digest mismatch')
                verified.append((entry, sha))
            # Only attach locally verified digests after the entire ledger passes.
            for entry, sha in verified:entry['sha256'] = sha
            return actual
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            raise BridgeError(label + ' manifest or file integrity is invalid; '
                              + ('repair local cache explicitly' if cached else 'download was not cached')) from exc

    def _download(self, message_id, repair=False):
        with self.lock:
            row = self.db.execute('SELECT body FROM events WHERE message_id=?', (message_id,)).fetchone()
        if not row:
            raise ValueError('Only a message already read from the bound group may be downloaded')
        expected={(r.get('resourceIdType') or r.get('type'),r.get('resourceId')) for r in json.loads(row[0]).get('attachments',[])}
        folder = str(self.local.relative_to(self.root) / 'downloads' / hashlib.sha256(message_id.encode()).hexdigest())
        manifest = self.root / folder / 'manifest.json'
        if manifest.exists() and not repair:
            try:
                cached = json.loads(manifest.read_text())
            except (ValueError, OSError) as exc:
                raise BridgeError('Cached attachment manifest is invalid or incomplete; repair local cache explicitly') from exc
            actual = self._verify_download_ledger(cached, self.root / folder, cached=True)
            if expected-actual:
                raise BridgeError('Cached attachment manifest is incomplete; repair local cache explicitly')
            return cached
        attempt_folder = folder + '/attempt-' + uuid.uuid4().hex
        data = self.dws.call(['chat', '+messages-mget', '--msg-ids', message_id,
                             '--download-resources', '--output-dir', attempt_folder])
        messages=data.get('messages') if isinstance(data,dict) else None
        if (not isinstance(messages,list) or len(messages)!=1 or not isinstance(messages[0],dict) or
                messages[0].get('messageId')!=message_id or messages[0].get('conversationId')!=self.config['group']):
            raise BridgeError('Downloaded message identity mismatch')
        ledger = data.get('resourceDownloads', {})
        actual = self._verify_download_ledger(ledger, self.root / attempt_folder)
        if expected-actual:
            ledger={**ledger,'ok':False,'partial':True,'bridgeError':'missing_expected_resources'}
        elif ledger.get('partial') or ledger.get('failedCount'):
            ledger={**ledger,'ok':False}
        if ledger.get('ok') is True and not ledger.get('partial') and not ledger.get('failedCount'):
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(ledger, ensure_ascii=False))
            manifest.chmod(0o600)
        return ledger

    def health(self):
        with self.lock:
            r = self.db.execute('SELECT value FROM meta WHERE key="last_sync"').fetchone()
            count = self.db.execute('SELECT count(*) FROM events').fetchone()[0]
            peers = self.db.execute('SELECT count(*) FROM events WHERE json_extract(body,"$.from_self")=0').fetchone()[0]
        return {'mode': 'experimental', 'transport': 'dws_history_poll', 'events': count,
                'last_sync': json.loads(r[0]) if r else None,
                'native_audio_video': False, 'other_member_events':peers,
                'other_member_inbound': 'observed' if peers else 'not_observed'}

    def close(self):
        self.db.close()
        fcntl.flock(self.process_lock, fcntl.LOCK_UN)
        self.process_lock.close()

    def stop_waiters(self):
        with self.event_condition:
            self.stopping=True
            self.event_condition.notify_all()

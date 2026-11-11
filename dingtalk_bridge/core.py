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


class BridgeError(Exception):
    pass


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
        return {**dict(row), **({'upload_state': upload[0], 'image_delivery': 'native'} if upload else {})} if row else None

    def send(self, key, text=None, file=None, image=None):
        if not isinstance(key, str) or not key or len(key) > 128:
            raise ValueError('A stable idempotency key is required (1-128 chars)')
        if sum(x is not None for x in (text, file, image)) != 1:
            raise ValueError('Provide exactly one of text, file or image')
        payload = {}
        if text is not None:
            if not isinstance(text, str) or not text or len(text.encode()) > 65536 or '![' in text:
                raise ValueError('Use plain text up to 64 KiB; inline images need a separate verified route')
            payload = {'kind': 'text', 'text': text}
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
        if text is not None:
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
            if not task:
                raise BridgeError('No send task ID; do not resend')
            with self.lock:
                self.db.execute('UPDATE deliveries SET state="submitted",task_id=? WHERE key=?', (task, key))
                self.db.commit()
            return self.reconcile(key)
        except Exception as e:
            with self.lock:
                self.db.execute('UPDATE deliveries SET state="outcome_unknown",error=? WHERE key=?', (str(e), key))
                self.db.commit()
            return self.delivery(key)

    def reconcile(self, key):
        item = self.delivery(key)
        if not item:
            raise KeyError(key)
        if not item['task_id'] or item['state'] == 'confirmed':
            return item
        data = self.dws.call(['chat', '+messages-query-send-status', '--open-task-id', item['task_id']])
        result = data.get('result', {})
        status = result.get('sendStatus')
        state = 'confirmed' if status == 'SUCCESS' else 'failed' if status == 'FAILED' else 'submitted'
        ref = data.get('messageRef', {})
        if state == 'confirmed' and (ref.get('openConversationId') != self.config['group'] or not ref.get('openMessageId')):
            raise BridgeError('Delivery result identity mismatch')
        with self.lock:
            self.db.execute('UPDATE deliveries SET state=?,message_id=?,error=NULL WHERE key=?',
                            (state, ref.get('openMessageId'), key))
            self.db.commit()
        return self.delivery(key)

    def download(self, message_id, repair=False):
        with self.download_lock:
            return self._download(message_id,repair)

    def _download(self, message_id, repair=False):
        with self.lock:
            row = self.db.execute('SELECT body FROM events WHERE message_id=?', (message_id,)).fetchone()
        if not row:
            raise ValueError('Only a message already read from the bound group may be downloaded')
        folder = str(self.local.relative_to(self.root) / 'downloads' / hashlib.sha256(message_id.encode()).hexdigest())
        manifest = self.root / folder / 'manifest.json'
        if manifest.exists() and not repair:
            cached = json.loads(manifest.read_text())
            for entry in cached.get('downloads', []):
                p = (self.root / entry['localPath']).resolve()
                if not p.is_relative_to((self.root / folder).resolve()) or not p.is_file():
                    raise BridgeError('Cached attachment is missing; repair local cache explicitly')
                if hashlib.sha256(p.read_bytes()).hexdigest() != entry.get('sha256'):
                    raise BridgeError('Cached attachment integrity mismatch')
            return cached
        attempt_folder = folder + '/attempt-' + uuid.uuid4().hex
        data = self.dws.call(['chat', '+messages-mget', '--msg-ids', message_id,
                             '--download-resources', '--output-dir', attempt_folder])
        messages=data.get('messages',[])
        if len(messages)!=1 or messages[0].get('messageId')!=message_id or messages[0].get('conversationId')!=self.config['group']:
            raise BridgeError('Downloaded message identity mismatch')
        ledger = data.get('resourceDownloads', {})
        for entry in ledger.get('downloads', []):
            p = (self.root / entry['localPath']).resolve()
            if not p.is_relative_to((self.root / folder).resolve()):
                raise BridgeError('Unexpected download destination')
            entry['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
        expected={(r.get('resourceIdType') or r.get('type'),r.get('resourceId')) for r in json.loads(row[0]).get('attachments',[])}
        actual={(r.get('resourceType'),r.get('resourceId')) for r in ledger.get('downloads',[])}
        if expected-actual:
            ledger={**ledger,'ok':False,'partial':True,'bridgeError':'missing_expected_resources'}
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

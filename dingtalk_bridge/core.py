from __future__ import annotations
import hashlib
import fcntl
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from .text_limits import PERSONAL_TEXT_UNITS, utf16_units
from .rejection import read_length_rejection
from .dws_access import (BridgeError, DWSCredentialStoreUnavailable, DWSAccessSuspended,
                         DWSAccess, access_diagnostic, credential_failure, run_dws)


def credential_store_diagnostic():
    return access_diagnostic('credential_store_unavailable')


class DWSRequestRejected(BridgeError):
    """Explicit server invalid-request response, never a timeout inference."""
    def __init__(self, diagnostic):
        super().__init__('PARAM_ERROR')
        self.diagnostic = diagnostic


class ArtifactIntegrityError(ValueError):
    """The intended bytes changed before any new delivery was reserved."""
    def __init__(self):
        super().__init__('artifact_integrity_mismatch')


def provider_ids(value, fields):
    """Inspect only official response wrappers, never quoted messages or actions.

    DWS projects the first ID found in these wrappers. Preserve the underlying
    evidence too, so a projection cannot hide conflicting provider identities.
    """
    found = set()
    def collect(item):
        if isinstance(item, dict):
            if any(item.get(key) in (False, 'false') for key in ('success', 'ok') if key in item):
                raise BridgeError('Provider result reports failure')
            for field in fields:
                candidate = item.get(field)
                if candidate is None or candidate == '':
                    continue
                if not isinstance(candidate, str) or not candidate.strip():
                    raise BridgeError('Malformed provider identity')
                found.add(candidate.strip())
            for name in ('result', 'data', 'response', 'content', 'message'):
                collect(item.get(name))
        elif isinstance(item, list):
            for child in item:
                collect(child)
    collect(value)
    return found


def send_task_identity(data, allow_raw=False):
    receipt = data.get('sendReceipt')
    projected = set()
    if receipt is not None:
        if not isinstance(receipt, dict) or receipt.get('contractVersion', 'im.message-send-receipt.v1') != 'im.message-send-receipt.v1':
            raise BridgeError('Unexpected send receipt contract')
        projected = provider_ids(receipt, ('openTaskId', 'taskId'))
    tasks = projected | provider_ids(data, ('openTaskId', 'taskId'))
    if len(tasks) != 1 or not (projected or allow_raw):
        raise BridgeError('Missing or conflicting send task ID; do not resend')
    return tasks.pop()


class DWS:
    def __init__(self, root, config):
        self.root, self.config = Path(root), config
        self.binary = str((self.root / config['binary']).resolve())
        self.access = DWSAccess(self.root)
        self.stop = threading.Event()

    def call(self, args):
        with self.access.lease(self.stop) as lease:
            try:
                p = run_dws([self.binary, *args, '--profile', self.config['profile'],
                             '--format', 'json'], cwd=self.root, stop=self.stop)
            except DWSAccessSuspended as exc:
                lease.block(exc.reason);raise
            try:
                data = json.loads(p.stdout or p.stderr)
            except ValueError as e:
                lease.complete()
                raise BridgeError('DWS returned no valid JSON') from e
            if credential_failure(data):
                lease.block('credential_store_unavailable')
                raise DWSCredentialStoreUnavailable()
            lease.complete()
        if not isinstance(data, dict):
            raise BridgeError('DWS returned no JSON object')
        if p.returncode or data.get('success') in (False, 'false') or data.get('ok') is False:
            error = data.get('error', {})
            if not isinstance(error, dict):
                raise BridgeError('DWS business failure')
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
        uploader.stop = self.stop
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

    def _history_window(self, now, deep):
        # Freeze the window before the request, including failed/interrupted reads.
        # The official token is opaque and bound to this exact query; it is not a
        # timestamp from which the bridge may manufacture its own continuation.
        with self.lock, self.db:
            saved = self.db.execute('SELECT value FROM meta WHERE key="history_window"').fetchone()
            if saved:
                try:
                    window = json.loads(saved[0])
                    if not isinstance(window, dict) or set(window) != {'version', 'start', 'end', 'deep', 'target', 'token', 'seen'}:
                        raise ValueError('schema')
                    if type(window['version']) is not int or window['version'] != 1:
                        raise ValueError('version')
                    if type(window['deep']) is not bool or window['target'] != self.target_args():
                        raise ValueError('query binding')
                    start, end = (datetime.fromisoformat(window[k]) for k in ('start', 'end'))
                    if start.tzinfo is None or end.tzinfo is None or start > end:
                        raise ValueError('time window')
                    token, seen = window['token'], window['seen']
                    if (not isinstance(seen, list) or len(seen) > 4096 or
                            not all(isinstance(h, str) and len(h) == 64 and all(c in '0123456789abcdef' for c in h) for h in seen) or
                            len(set(seen)) != len(seen)):
                        raise ValueError('cursor history')
                    if not ((token is None and not seen) or (self._valid_history_token(token) and seen and
                            hashlib.sha256(token.encode()).hexdigest() == seen[-1])):
                        raise ValueError('cursor')
                except (ValueError, TypeError, KeyError) as exc:
                    raise BridgeError('Invalid persisted history window; no request made') from exc
                return window
            row = self.db.execute('SELECT value FROM meta WHERE key="watermark"').fetchone()
            start = datetime.fromisoformat(row[0]) - timedelta(minutes=5) if row else now - timedelta(days=1)
            last_deep = self.db.execute('SELECT value FROM meta WHERE key="last_deep_sync"').fetchone()
            deep = deep or not last_deep or now-datetime.fromisoformat(last_deep[0]) >= timedelta(minutes=30)
            if deep:
                start = min(start, now-timedelta(hours=24))
            window = {'version': 1, 'start': start.isoformat(), 'end': now.isoformat(),
                      'deep': bool(deep), 'target': self.target_args(), 'token': None, 'seen': []}
            self.db.execute('INSERT INTO meta VALUES (?,?)', ('history_window', json.dumps(window)))
            return window

    @staticmethod
    def _valid_history_token(token):
        return isinstance(token, str) and 0 < len(token) <= 8192 and all(33 <= ord(c) <= 126 for c in token)

    def sync(self, deep=False):
        with self.sync_lock:
            now = datetime.now(timezone.utc)
            window = self._history_window(now, deep)
            deep = window['deep']
            args = ['chat', '+chat-messages', *window['target'],
                '--start', window['start'], '--end', window['end'], '--order', 'asc',
                '--page-all', '--page-limit', '20', '--max-items', '1000', '--limit', '50']
            if window['token'] is not None:
                args += ['--page-token', window['token']]
            data = self.dws.call(args)
            if not isinstance(data.get('messages'),list):
                raise BridgeError('Missing history messages; watermark unchanged')
            failed = bool(data.get('partial') or data.get('failedCount') or data.get('failures'))
            complete = data.get('complete') is True and not failed and data.get('hasMore') is not True
            continuation = None
            continuation_error = None
            if not complete and not failed and (data.get('stopReason') in {'page_limit', 'result_limit'} or
                                                data.get('complete') is True):
                token = data.get('nextPageToken')
                if data.get('complete') is True or data.get('hasMore') is not True or not self._valid_history_token(token):
                    continuation_error = 'History limit has no safe continuation; window retained'
                else:
                    fingerprint = hashlib.sha256(token.encode()).hexdigest()
                    if fingerprint in window['seen'] or len(window['seen']) >= 4096:
                        continuation_error = 'History continuation repeated or exceeded window budget; window retained'
                    else:
                        continuation = {**window, 'token': token, 'seen': [*window['seen'], fingerprint]}
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
                if complete:
                    self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', ('watermark', window['end']))
                    if deep:
                        self.db.execute('INSERT OR REPLACE INTO meta VALUES ("last_deep_sync",?)',(window['end'],))
                    self.db.execute('DELETE FROM meta WHERE key="history_window"')
                elif continuation is not None:
                    self.db.execute('UPDATE meta SET value=? WHERE key="history_window"', (json.dumps(continuation),))
                self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                    ('last_sync', json.dumps({'at': now.isoformat(), 'complete': complete, 'inserted': inserted, 'deep':deep,
                                             'continuing': continuation is not None, 'error': continuation_error})))
                self.db.commit()
                if inserted:self.event_condition.notify_all()
            if continuation_error:
                raise BridgeError(continuation_error)
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

    def send(self, key, text=None, file=None, image=None, reply_to=None, expected_sha256=None):
        if not isinstance(key, str) or not key or len(key) > 128:
            raise ValueError('A stable idempotency key is required (1-128 chars)')
        if sum(x is not None for x in (text, file, image)) != 1:
            raise ValueError('Provide exactly one of text, file or image')
        if expected_sha256 is not None and (text is not None or not isinstance(expected_sha256, str)
                or re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is None):
            raise ValueError('expected_sha256 requires file/image and 64 lowercase hex characters')
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
            if not any(source.is_relative_to(p) for p in allowed):
                raise ValueError('Only files in fixtures/ or local/outbox/ can be sent')
            if image is not None and source.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
                raise ValueError('Image mode accepts PNG/JPEG only')
            stage_name = 'image' + source.suffix.lower() if image is not None else source.name
            def file_payload(digest):
                stage = self.local / 'staged' / digest / stage_name
                return {'kind': 'image' if image is not None else 'file', 'sha256': digest, 'name': source.name,
                        'staged': str(stage.relative_to(self.root))}
            def replay_expected_file():
                # A prior send owns these intended bytes. Reconcile its original
                # receipt even if the producer file has since changed/disappeared.
                intended = json.dumps(file_payload(expected_sha256), sort_keys=True, ensure_ascii=False)
                with self.lock:
                    row = self.db.execute('SELECT fingerprint FROM deliveries WHERE key=?', (key,)).fetchone()
                    if row:
                        if row[0] != hashlib.sha256(intended.encode()).hexdigest():
                            raise ValueError('Idempotency key already belongs to another payload')
                        return {**self.delivery(key), 'replayed': True}
                return None
            if expected_sha256 is not None:
                replay = replay_expected_file()
                if replay is not None: return replay
            if not source.is_file():
                raise ValueError('Only files in fixtures/ or local/outbox/ can be sent')
            if source.stat().st_size > 20 * 1024 * 1024:
                raise ValueError('Experimental service file limit is 20 MiB')
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            # Digest gate adapted from CEO Agent Service DingTalkFileHandler.dispatch
            # (bd3de36b); MIT, Copyright (c) 2026 CEO Agent Service contributors.
            # See licenses/ceo-agent-service.txt and docs/references/artifact-digest-adoption.md.
            if expected_sha256 is not None and digest != expected_sha256:
                # A concurrent request may have reserved/sent this same key
                # while we read. Its authoritative receipt still takes priority.
                replay = replay_expected_file()
                if replay is not None: return replay
                raise ArtifactIntegrityError()
            if len(content) > 20 * 1024 * 1024:
                raise ValueError('Experimental service file limit is 20 MiB')
            stage = self.local / 'staged' / digest / stage_name
            stage.parent.mkdir(parents=True, exist_ok=True)
            if not stage.exists():
                stage.write_bytes(content)
                stage.chmod(0o600)
            if stage.is_symlink() or hashlib.sha256(stage.read_bytes()).hexdigest() != digest:
                raise ValueError('Staged file integrity mismatch; no upload or send attempted')
            payload = file_payload(digest)
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
            # v1.0.67 group quote may return raw MCP data without sendReceipt.
            task = send_task_identity(data, allow_raw=reply_to is not None)
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
        if data.get('contractVersion', 'im.message-send-status.v1') != 'im.message-send-status.v1':
            raise BridgeError('Unexpected send status contract')
        tasks = provider_ids(data, ('openTaskId', 'taskId'))
        if tasks and tasks != {item['task_id']}:
            raise BridgeError('Delivery result task mismatch')
        result = data.get('result', {})
        status = result.get('sendStatus')
        state = 'confirmed' if status == 'SUCCESS' else 'failed' if status == 'FAILED' else 'submitted'
        ref = data.get('messageRef', {})
        if state == 'confirmed':
            mid = ref.get('openMessageId')
            if (ref.get('openConversationId') != self.config['group'] or
                    not isinstance(mid, str) or not mid.strip()):
                raise BridgeError('Delivery result identity mismatch')
            messages = provider_ids(data, ('openMessageId', 'messageId', 'msgId'))
            conversations = provider_ids(data, ('openConversationId', 'conversationId', 'openCid'))
            if ((messages and messages != {mid}) or
                    (conversations and conversations != {self.config['group']})):
                raise BridgeError('Conflicting delivery result identities')
            with self.lock:
                payload = json.loads(self.db.execute('SELECT payload FROM deliveries WHERE key=?', (key,)).fetchone()[0])
            if mid == payload.get('reply_to'):
                raise BridgeError('Referenced source is not outgoing delivery evidence')
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

    def _commit_download_manifest(self, manifest, ledger):
        temporary = None
        try:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix='.manifest-', suffix='.json', dir=manifest.parent)
            temporary = Path(name)  # mkstemp is private (0600) before any bytes exist.
            with os.fdopen(descriptor, 'wb') as output:
                output.write(json.dumps(ledger, ensure_ascii=False).encode())
                output.flush()
                os.fsync(output.fileno())
            # Same-directory replacement publishes a complete file without first
            # truncating the last good cache. A killed writer may leave only a
            # private temporary file, which cache readers never select.
            os.replace(temporary, manifest)
        except (OSError, ValueError, TypeError) as exc:
            raise BridgeError('Attachment cache commit failed; check local storage before retrying') from exc
        finally:
            if temporary is not None:
                try:temporary.unlink(missing_ok=True)
                except OSError:pass  # Do not mask the commit error; orphan remains private.

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
            self._commit_download_manifest(manifest, ledger)
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
        if isinstance(self.dws,DWS):self.dws.stop.set()
        with self.event_condition:
            self.stopping=True
            self.event_condition.notify_all()

"""Route-bound stdio endpoint for a native OpenClaw channel, using bridge HTTP and Inbox."""
import argparse
import base64
import binascii
from contextlib import ExitStack, closing
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request

from .consumer import Inbox, acquire_consumer_lock, execution_scope
from .local_http import urlopen
from .message_model import file_request, materialize, normalize, select_file_sources
from .routing import route_configs

MAX_FILE = 20 * 1024 * 1024
MAX_FRAME = ((MAX_FILE + 2) // 3) * 4 + 65536


class ChannelError(ValueError):
    """Only these fixed codes are returned to the host."""


def route_api(root, route, port):
    if not 1 <= port <= 65535:
        raise ChannelError('invalid_bridge_port')
    scope = {'account_id': route['accountId'], 'conversation_id': route['group']}

    def call(path, payload=None):
        token = (root / 'local/runtime/http-token').read_text().strip()
        data = None
        if payload is None:
            path += ('&' if '?' in path else '?') + urlencode(scope)
        else:
            data = json.dumps({**payload, **scope}).encode()
        request = Request(f'http://127.0.0.1:{port}{path}', data=data, headers={
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urlopen(request, timeout=120) as response:
            return json.load(response)
    return call


def stage_original(root, filename, data, digest):
    directory = root / 'local/outbox/host-channel' / digest
    if directory.resolve() != directory:
        raise ChannelError('invalid_staging_directory')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = directory / filename
    # Publish complete bytes without replacing a file being read by another route.
    if not destination.exists():
        with tempfile.NamedTemporaryFile(dir=directory) as tmp:
            tmp.write(data)
            tmp.flush()
            try:
                os.link(tmp.name, destination)
            except FileExistsError:
                pass
    if (destination.is_symlink() or not destination.is_file()
            or destination.stat().st_size != len(data)
            or hashlib.sha256(destination.read_bytes()).hexdigest() != digest):
        raise ChannelError('staged_media_integrity')
    return str(destination.relative_to(root))


class HostChannel:
    def __init__(self, root, route, state_name, initial_cursor, api, *, consumer_instance=None):
        if route.get('executionOwner') != 'openclaw' or not route.get('selfSenderId'):
            raise ChannelError('route_not_configured_for_host')
        if type(initial_cursor) is not int or initial_cursor < 0:
            raise ChannelError('invalid_initial_cursor')
        if consumer_instance is not None and (
                not isinstance(consumer_instance, str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,31}', consumer_instance)):
            raise ChannelError('invalid_consumer_instance')
        self.root = Path(root).resolve()
        self.route = route
        self.api = api
        self.control_turn = None
        self.control_cursor = 0
        self.file_selection = None
        # Ephemeral evidence only: a restarted owner cannot certify cancellation.
        self.send_attempts = 0
        self.claim_send_epochs = {}
        self.cancel_matches = {}
        _, key = execution_scope(route)
        # This path is also held for the full lifetime of a pre-plugin gateway.
        # Sharing only its lock preserves its existing inbox, tasks and session.
        with ExitStack() as stack:
            stack.enter_context(acquire_consumer_lock(self.root, 'agent-' + key))
            name = 'openclaw-' + key
            if consumer_instance is not None:
                name += '-' + consumer_instance
            self.inbox = Inbox(self.root, route, name, state_name)
            stack.callback(self.inbox.close)
            self.db = self.inbox.db
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS host_dispatch (
                    message_id TEXT PRIMARY KEY, status TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS host_cancellations (
                    message_id TEXT PRIMARY KEY, cancel_message_id TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS host_sends (
                    key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS host_plans (
                    intent TEXT PRIMARY KEY, part_count INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS host_plan_keys (
                    intent TEXT NOT NULL, part_index INTEGER NOT NULL, position INTEGER NOT NULL,
                    key TEXT PRIMARY KEY, kind TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    UNIQUE(intent, part_index, position));
            ''')
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO meta VALUES ("cursor", ?)',
                                (str(initial_cursor),))
                self.db.execute("UPDATE host_dispatch SET status='unknown' WHERE status='claimed'")
            self.resources = stack.pop_all()

    def close(self):
        self.resources.close()

    def claim_ready(self):
        rows = self.db.execute('''
            SELECT seq, model FROM inbox WHERE state='normalized'
              AND json_extract(model,'$.fromSelf')=0
              AND json_array_length(model,'$.issues')=0
              AND NOT EXISTS (SELECT 1 FROM host_dispatch d WHERE d.message_id=inbox.message_id)
              ORDER BY seq''')
        try:
            ready = next(self.inbox.iter_ready(rows), None)
        finally:
            rows.close()
        if ready is None:
            return None
        return self.claim(ready['message'])

    def claim(self, message):
        # Stdio delivery and arbitrary host/tool execution cannot share a transaction.
        # A process death after this commit therefore needs review, never a second turn.
        with self.db:
            self.db.execute("INSERT INTO host_dispatch VALUES (?, 'claimed')", (message['id'],))
        self.claim_send_epochs[message['id']] = self.send_attempts
        return message

    def receive(self):
        query = urlencode({'after': self.inbox.cursor, 'limit': 200})
        batch = self.api('/v1/events?' + query)
        if (batch.get('account_id'), batch.get('conversation_id')) != (
                self.route['accountId'], self.route['group']):
            raise ChannelError('transport_route_mismatch')
        if len(batch['events']) > 200:
            raise ChannelError('oversized_transport_batch')
        if any(event.get('conversation_type') != self.route.get('conversationType', 'group')
               for event in batch['events']):
            raise ChannelError('transport_conversation_type_mismatch')
        return self.inbox.ingest(batch)

    def poll(self):
        message = self.claim_ready()
        if message is None:
            self.receive()
            self.inbox.hydrate(lambda mid: self.api('/v1/attachments', {'message_id': mid}))
            message = self.claim_ready()
        return {'message': message}

    def poll_cancel(self, active_id):
        """During a turn, keep other work durable and search only for a later text stop."""
        active = self.db.execute("""
            SELECT i.seq, json_extract(i.model,'$.senderId') AS sender
            FROM inbox i JOIN host_dispatch d USING(message_id)
            WHERE i.message_id=? AND d.status='claimed'""", (active_id,)).fetchone()
        if active is None:
            # Its terminal acknowledgment might have reached stdio before this poll.
            return {'message': None}
        if self.control_turn != active_id:
            self.control_turn, self.control_cursor = active_id, active['seq']
        if self.control_cursor >= self.inbox.cursor:
            self.receive()
        page = self.db.execute("""
            SELECT i.seq, i.model, d.status FROM inbox i
            LEFT JOIN host_dispatch d USING(message_id)
            WHERE i.seq>? ORDER BY i.seq LIMIT 200""", (self.control_cursor,)).fetchall()
        for row in page:
            self.control_cursor = row['seq']
            if row['status'] is not None:
                continue
            msg = json.loads(row['model'])
            if (not msg or msg['senderId'] != active['sender'] or msg['fromSelf'] is not False
                    or msg['issues'] or msg.get('quote') or len(msg['parts']) != 1
                    or msg['parts'][0]['type'] != 'text'):
                continue
            raw = msg['parts'][0]['text']
            direct = msg['conversationType'] == 'direct'
            if not direct and not raw.startswith('/agent'):
                continue
            text = raw.strip()
            if (direct and text == '/stop') or re.fullmatch(r'/agent\s+(?:cancel|/stop)', text):
                control = self.claim(msg)
                self.cancel_matches[control['id']] = active_id
                return {'message': control}
        # Immediately examine the next page when there is local or upstream backlog.
        # Each call fetches at most one transport page and reads at most 200 inbox rows.
        return {'message': None, 'hasMore': len(page) == 200}

    def previous_file_candidates(self, row):
        # seq can contain large gaps from overlap polls. Count actual route events,
        # including malformed ones, across the host's first-activation cursor.
        path = self.inbox.cache_root.with_name('bridge.sqlite3')
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as history:
            history.execute('BEGIN')
            scope = history.execute("SELECT value FROM meta WHERE key='scope'").fetchone()
            if scope is None or json.loads(scope[0]) != [self.route['profile'], self.route['group']]:
                raise ChannelError('file_history_scope_mismatch')
            anchor = history.execute('SELECT body FROM events WHERE seq=? AND message_id=?',
                                     (row['seq'], row['message_id'])).fetchone()
            if anchor is None or {'seq': row['seq'], **json.loads(anchor[0])} != json.loads(row['raw']):
                raise ChannelError('file_history_anchor_mismatch')
            rows = history.execute('SELECT message_id, body FROM events WHERE seq<? ORDER BY seq DESC LIMIT 50',
                                   (row['seq'],)).fetchall()
        previous = []
        for mid, body in rows:
            event = json.loads(body)
            if (event.get('message_id') != mid or event.get('account_id') != self.route['accountId']
                    or event.get('conversation_id') != self.route['group'] or event.get('conversation_type') != 'group'):
                raise ChannelError('file_history_scope_mismatch')
            try:
                previous.append(normalize(event, self.route))
            except (ValueError, KeyError, TypeError):
                continue  # The built-in selector also excludes quarantined projections.
        return previous

    def select_files(self, mid):
        if self.file_selection is not None:
            old_mid, task, originals = self.file_selection
            if old_mid != mid:
                raise ChannelError('file_selection_busy')
            return {'task': task, 'count': len(originals)}
        row = self.db.execute("""
            SELECT i.seq,i.message_id,i.raw,i.model FROM inbox i JOIN host_dispatch d USING(message_id)
            WHERE i.message_id=? AND d.status='claimed' AND i.state='normalized'""", (mid,)).fetchone()
        if row is None:
            raise ChannelError('file_selection_requires_claim')
        model = json.loads(row['model'])
        text = ''.join(part['text'] for part in model['parts'] if part['type'] == 'text')
        addressed = re.fullmatch(r'/agent\s+(.*)', text, flags=re.DOTALL)
        command = addressed[1] if addressed else None
        if model['fromSelf'] is not False or not file_request(model, command):
            return {'error': 'file_selection_invalid'}
        previous = self.previous_file_candidates(row)
        try:
            task, sources = select_file_sources(model, command, previous)
        except ValueError as exc:
            return {'error': str(exc)}
        by_id = {candidate['id']: candidate for candidate in previous}
        originals = [(by_id[src['messageId']], src) for src in sources]
        # This owner serializes turns. A lost claim is quarantined on restart.
        # Retain the selected identities while originals are downloaded one at a time.
        self.file_selection = (mid, task, originals)
        return {'task': task, 'count': len(originals)}

    def selected_file(self, mid, index):
        if self.file_selection is None or self.file_selection[0] != mid:
            raise ChannelError('file_selection_requires_claim')
        originals = self.file_selection[2]
        if type(index) is not int or not 0 <= index < len(originals):
            raise ChannelError('invalid_file_selection_index')
        original, selected = originals[index]
        ledger = self.api('/v1/attachments', {'message_id': original['id']})
        materialize(original, ledger, self.root, self.inbox.cache_root)
        part, = [p for p in original['parts'] if p['type'] == 'file'
                 and p.get('name') == selected['name'] and p['resource'] == selected['resource']]
        return {'part': part}

    def ack(self, mid, status, cancel_id=None):
        if (not isinstance(mid, str) or status not in ('done', 'ignored', 'unknown', 'canceled')
                or (status == 'canceled' and (not isinstance(cancel_id, str) or not cancel_id))):
            raise ChannelError('invalid_ack')
        with self.db:
            row = self.db.execute('SELECT status FROM host_dispatch WHERE message_id=?', (mid,)).fetchone()
            if row is None or row[0] not in ('claimed', status):
                raise ChannelError('dispatch_state_conflict')
            if status == 'canceled' and row[0] == 'claimed':
                control = self.db.execute('SELECT status FROM host_dispatch WHERE message_id=?',
                                          (cancel_id,)).fetchone()
                if (self.cancel_matches.get(cancel_id) != mid or control is None or control[0] != 'done'
                        or self.claim_send_epochs.get(mid) != self.send_attempts):
                    raise ChannelError('cancellation_not_proven')
                self.db.execute('INSERT INTO host_cancellations VALUES (?,?)', (mid, cancel_id))
            elif status == 'canceled':
                prior = self.db.execute('SELECT cancel_message_id FROM host_cancellations WHERE message_id=?',
                                        (mid,)).fetchone()
                if prior is None or prior[0] != cancel_id:
                    raise ChannelError('dispatch_state_conflict')
            self.db.execute('UPDATE host_dispatch SET status=? WHERE message_id=?', (status, mid))
        self.claim_send_epochs.pop(mid, None)
        self.cancel_matches = {control: active for control, active in self.cancel_matches.items() if active != mid}
        if self.file_selection and self.file_selection[0] == mid:
            self.file_selection = None
        return {'status': status}

    def submission(self, request):
        if ('media' in request) == ('text' in request):
            raise ChannelError('choose_text_or_media')
        if 'text' in request:
            text = request['text']
            if not isinstance(text, str) or not text:
                raise ChannelError('invalid_text')
            body = {'text': text}
            if 'replyTo' in request:
                body['reply_to'] = request['replyTo']
            return body, None
        media = request['media']
        if not isinstance(media, dict) or media.get('kind') not in ('file', 'image'):
            raise ChannelError('invalid_media')
        filename = media.get('filename')
        if (not isinstance(filename, str) or not filename.strip() or filename in ('.', '..')
                or '/' in filename or '\\' in filename or any(ord(c) < 32 for c in filename)
                or len(filename.encode()) > 255):
            raise ChannelError('invalid_filename')
        encoded = media.get('base64')
        if not isinstance(encoded, str) or len(encoded) > ((MAX_FILE + 2) // 3) * 4:
            raise ChannelError('invalid_media_size')
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise ChannelError('invalid_base64') from None
        if len(content) > MAX_FILE:
            raise ChannelError('invalid_media_size')
        digest = hashlib.sha256(content).hexdigest()
        if 'sha256' in media and media['sha256'] != digest:
            raise ChannelError('media_digest_mismatch')
        return {'kind': media['kind'], 'filename': filename, 'expected_sha256': digest}, content

    def stage(self, body, content):
        if content is None:
            return body
        kind, filename, digest = body['kind'], body['filename'], body['expected_sha256']
        if (kind == 'image' and (not self.route.get('imageUploadBinary') or len(content) > 2 * 1024 * 1024
                                or Path(filename).suffix.lower() not in ('.png', '.jpg', '.jpeg'))):
            kind = 'file'
        return {kind: stage_original(self.root, filename, content, digest), 'expected_sha256': digest}

    def receipt(self, key, result):
        if (not isinstance(result, dict) or result.get('key') != key or not result.get('state')
                or result['state'] == 'confirmed' and not result.get('message_id')):
            raise ChannelError('invalid_transport_receipt')
        return {name: result.get(name) for name in ('key', 'state', 'task_id', 'message_id')}

    def plan(self, intent, part, count, keys):
        if (type(part) is not int or type(count) is not int or not 0 <= part < count <= 2**53 - 1
                or not isinstance(keys, list) or not keys):
            raise ChannelError('invalid_delivery_plan')
        entries = []
        for entry in keys:
            if not isinstance(entry, dict):
                raise ChannelError('invalid_delivery_plan')
            key, kind, fingerprint = (entry.get(field) for field in ('key', 'kind', 'fingerprint'))
            if (not isinstance(key, str) or not 1 <= len(key) <= 128 or kind not in ('text', 'media')
                    or not isinstance(fingerprint, str) or not re.fullmatch('[0-9a-f]{64}', fingerprint)):
                raise ChannelError('invalid_delivery_plan')
            entries.append((key, kind, fingerprint))
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO host_plans VALUES (?, ?)', (intent, count))
            stored_count = self.db.execute('SELECT part_count FROM host_plans WHERE intent=?', (intent,)).fetchone()[0]
            if count != stored_count:
                raise ChannelError('delivery_plan_conflict')
            registered = self.db.execute("""
                SELECT key,kind,fingerprint FROM host_plan_keys
                WHERE intent=? AND part_index=? ORDER BY position""", (intent, part)).fetchall()
            if registered:
                if entries != [tuple(row) for row in registered]:
                    raise ChannelError('delivery_plan_conflict')
            else:
                # A legacy send has no evidence linking it to this host queue/part.
                # A physical key can belong to only one intent, position, and payload.
                try:
                    for position, (key, kind, fingerprint) in enumerate(entries):
                        if self.db.execute('SELECT 1 FROM host_sends WHERE key=?', (key,)).fetchone():
                            raise ChannelError('delivery_plan_conflict')
                        self.db.execute('INSERT INTO host_plan_keys VALUES (?,?,?,?,?,?)',
                                        (intent, part, position, key, kind, fingerprint))
                except sqlite3.IntegrityError:
                    raise ChannelError('delivery_plan_conflict') from None
        return {'registered': True}

    def lookup_plan(self, intent):
        count = self.db.execute('SELECT part_count FROM host_plans WHERE intent=?', (intent,)).fetchone()
        parts = {}
        for row in self.db.execute("""
            SELECT part_index,key,kind,fingerprint FROM host_plan_keys
            WHERE intent=? ORDER BY part_index,position""", (intent,)):
            parts.setdefault(row['part_index'], []).append(
                {field: row[field] for field in ('key', 'kind', 'fingerprint')})
        return {'partCount': count[0] if count else None, 'parts': [
            {'partIndex': index, 'keys': keys} for index, keys in parts.items()]}

    def verify_planned_send(self, key, intent, content):
        row = self.db.execute('SELECT kind, fingerprint FROM host_plan_keys WHERE key=?', (key,)).fetchone()
        if row is None:
            return
        if content is None:
            kind, fields = 'text', ['text', intent['text']]
            if 'reply_to' in intent:
                raise ChannelError('delivery_plan_conflict')
        else:
            kind, fields = 'media', [intent['kind'], intent['filename'], intent['expected_sha256']]
        # The host hashes UTF-8 JSON.stringify of this ordered string tuple.
        compact = json.dumps(fields, ensure_ascii=False, separators=(',', ':')).encode()
        if (kind, hashlib.sha256(compact).hexdigest()) != tuple(row):
            raise ChannelError('delivery_plan_conflict')

    def status(self, key, reconcile=False):
        if not self.db.execute('SELECT 1 FROM host_sends WHERE key=?', (key,)).fetchone():
            if self.db.execute('SELECT 1 FROM host_plan_keys WHERE key=?', (key,)).fetchone():
                # The host knows this required component; it has no physical receipt yet.
                return {'key': key, 'state': 'outcome_unknown', 'message_id': None, 'task_id': None}
            raise ChannelError('unknown_host_key')
        try:
            result = self.api('/v1/deliveries/' + quote(key, safe=''))
        except HTTPError as exc:
            with exc:
                if exc.code != 404:
                    raise
            # A local reservation can precede the transport ledger after interruption.
            return {'key': key, 'state': 'outcome_unknown', 'message_id': None, 'task_id': None}
        receipt = self.receipt(key, result)
        if (reconcile and receipt['task_id']
                and receipt['state'] not in ('confirmed', 'rejected', 'failed')):
            return self.receipt(key, self.api('/v1/reconcile', {'idempotency_key': key}))
        return receipt

    def send(self, key, request):
        # Conservatively include retries/invalid requests. No canceled claim may
        # conceal a send whose stdio/HTTP outcome could have been lost.
        self.send_attempts += 1
        intent, content = self.submission(request)
        self.verify_planned_send(key, intent, content)
        fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
        old = self.db.execute('SELECT fingerprint FROM host_sends WHERE key=?', (key,)).fetchone()
        if old is not None:
            if old[0] != fingerprint:
                raise ChannelError('idempotency_conflict')
            return self.status(key, reconcile=True)
        payload = self.stage(intent, content)
        # The process owns the route lock, so only this reservation can send this key.
        with self.db:
            self.db.execute('INSERT INTO host_sends VALUES (?,?)', (key, fingerprint))
        result = self.api('/v1/send', {'idempotency_key': key, **payload})
        return self.receipt(key, result)

    def handle(self, request):
        for field, target in (('accountId', 'accountId'), ('account_id', 'accountId'),
                              ('conversationId', 'group'), ('conversation_id', 'group')):
            if field in request and request[field] != self.route[target]:
                raise ChannelError('request_route_mismatch')
        op = request.get('op')
        if op in ('plan', 'lookupPlan'):
            intent = request.get('intent')
            if not isinstance(intent, str) or not 1 <= len(intent) <= 128:
                raise ChannelError('invalid_delivery_intent')
            if op == 'lookupPlan':
                return self.lookup_plan(intent)
            return self.plan(intent, request.get('partIndex'), request.get('partCount'), request.get('keys'))
        if op == 'poll':
            return self.poll()
        if op == 'pollCancel':
            active_id = request.get('activeMessageId')
            if not isinstance(active_id, str) or not active_id:
                raise ChannelError('invalid_active_message')
            return self.poll_cancel(active_id)
        if op in ('selectFiles', 'selectedFile'):
            mid = request.get('messageId')
            if not isinstance(mid, str) or not mid:
                raise ChannelError('invalid_file_selection_message')
            if op == 'selectFiles':
                return self.select_files(mid)
            return self.selected_file(mid, request.get('index'))
        if op == 'ack':
            return self.ack(request.get('messageId'), request.get('status'), request.get('cancelMessageId'))
        if op == 'summary':
            return {'cursor': self.inbox.cursor, 'dispatch': dict(self.db.execute(
                'SELECT status,count(*) FROM host_dispatch GROUP BY status'))}
        if op in ('send', 'status', 'reconcile'):
            key = request.get('key')
            if not isinstance(key, str) or not 1 <= len(key) <= 128:
                raise ChannelError('invalid_key')
            return self.send(key, request) if op == 'send' else self.status(key, reconcile=op == 'reconcile')
        raise ChannelError('unknown_operation')


def serve(channel, stdin, stdout):
    while raw := stdin.readline(MAX_FRAME + 1):
        call_id = None
        try:
            if len(raw) > MAX_FRAME:
                # Oversized frame may contain more data; do not parse its remainder as new calls.
                raise SystemExit('oversized_host_frame')
            request = json.loads(raw)
            if not isinstance(request, dict) or not isinstance(request.get('id'), (str, int)):
                raise ChannelError('invalid_request')
            call_id = request['id']
            result = {'ok': True, 'result': channel.handle(request)}
        except ChannelError as exc:
            result = {'ok': False, 'error': str(exc)}
        except sqlite3.Error:
            result = {'ok': False, 'error': 'sidecar_database_unavailable'}
        except HTTPError as exc:
            with exc:
                result = {'ok': False, 'error': f'transport_http_{exc.code}'}
        except (ValueError, KeyError, TypeError, OSError) as exc:
            result = {'ok': False, 'error': type(exc).__name__}
        print(json.dumps({'id': call_id, **result}, ensure_ascii=False), file=stdout, flush=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account-id', required=True)
    parser.add_argument('--conversation-id', required=True)
    parser.add_argument('--initial-cursor', required=True, type=int)
    parser.add_argument('--consumer-instance')
    parser.add_argument('--config', default='local/service-config.json')
    parser.add_argument('--port', default=18768, type=int)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    routes = route_configs(json.loads((root / args.config).read_text()))
    for route, state_name in routes:
        if (route['accountId'], route['group']) == (args.account_id, args.conversation_id):
            channel = HostChannel(root, route, state_name, args.initial_cursor,
                                  route_api(root, route, args.port), consumer_instance=args.consumer_instance)
            try:
                serve(channel, sys.stdin.buffer, sys.stdout)
            finally:
                channel.close()
            return
    parser.error('account/conversation route is not configured')


if __name__ == '__main__':
    main()

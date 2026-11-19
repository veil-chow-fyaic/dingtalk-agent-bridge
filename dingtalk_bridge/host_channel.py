"""Route-bound stdio endpoint for a native OpenClaw channel, using bridge HTTP and Inbox."""
import argparse
import base64
import binascii
from concurrent.futures import Future
from contextlib import ExitStack, closing
import hashlib
import json
import os
import re
import signal
import sqlite3
from pathlib import Path
import sys
import tempfile
from threading import Thread
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request

from .consumer import Inbox, acquire_consumer_lock, execution_scope
from .group_participation import GroupMentions, recent_group_context
from .local_http import urlopen
from .message_model import file_request, materialize, media_parts, normalize, select_file_sources
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
    def __init__(self, root, route, state_name, initial_cursor, api, *, consumer_instance=None, mention_senders=()):
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
        self.media_worker = None
        self.mention_senders = frozenset(mention_senders)
        if self.mention_senders and route.get('conversationType') != 'group':
            raise ChannelError('mentions_require_group')
        self.mention_index = GroupMentions(self.root, route) if self.mention_senders else None
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
                CREATE TABLE IF NOT EXISTS host_media_failures (
                    message_id TEXT PRIMARY KEY, reason TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS host_participation_wait (
                    message_id TEXT PRIMARY KEY, reason TEXT NOT NULL, attempts INTEGER NOT NULL, retry_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS host_silent_replies (
                    message_id TEXT PRIMARY KEY, reason TEXT NOT NULL);
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
                # No task execution or outbound delivery can begin until media preparation promotes
                # this claim. Observing a stop also promotes it first, so a stop cannot replay.
                self.db.execute("DELETE FROM host_dispatch WHERE status='preparing'")
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
              AND NOT EXISTS (
                SELECT 1 FROM host_participation_wait w JOIN inbox earlier USING(message_id)
                WHERE w.retry_at>? AND earlier.seq<=inbox.seq
                  AND json_extract(earlier.model,'$.senderId')=json_extract(inbox.model,'$.senderId'))
              ORDER BY seq''', (time.time(),))
        try:
            ready = next(self.inbox.iter_ready(rows), None)
        finally:
            rows.close()
        if ready is None:
            return None
        return self.claim(ready['message'])

    def claim(self, message, status='claimed'):
        mid = message['id']
        waiting = self.db.execute('SELECT retry_at FROM host_participation_wait WHERE message_id=?', (mid,)).fetchone()
        if waiting and waiting[0] > time.time():
            return None
        if self.mention_index is not None and message['senderId'] in self.mention_senders:
            raw = ''.join(p['text'] for p in message['parts'] if p['type'] == 'text')
            # A stop is an always-available same-sender control; it cannot cause a visible reply.
            if not re.fullmatch(r'/agent\s+(?:cancel|/stop)', raw.strip()):
                seq = self.db.execute('SELECT seq FROM inbox WHERE message_id=?', (mid,)).fetchone()[0]
                mentioned = self.mention_index.check(message, seq, self.inbox.cursor)
                if mentioned is None:
                    with self.db:
                        self.wait_for_participation(mid, 'mention_lookup_unavailable')
                    return None
                message = {**message, 'mentionedSelf': mentioned}
        # Stdio delivery and arbitrary host/tool execution cannot share a transaction.
        # A process death after this commit therefore needs review, never a second turn.
        with self.db:
            self.db.execute('INSERT INTO host_dispatch VALUES (?, ?)', (message['id'], status))
        self.claim_send_epochs[message['id']] = self.send_attempts
        return message

    def wait_for_participation(self, mid, reason):
        previous = self.db.execute('SELECT attempts FROM host_participation_wait WHERE message_id=?', (mid,)).fetchone()
        attempts = previous[0] + 1 if previous else 1
        delay = min(300, 15 * 2 ** min(attempts - 1, 5))
        self.db.execute('INSERT OR REPLACE INTO host_participation_wait VALUES (?,?,?,?)',
                        (mid, reason, attempts, time.time() + delay))

    def defer_participation(self, mid, reason):
        # A preparing reservation has not admitted business execution. Independent
        # outbound queue activity on this route cannot belong to the tool-free classifier.
        if reason != 'classifier_unavailable' or mid not in self.claim_send_epochs:
            raise ChannelError('participation_deferral_not_proven')
        with self.db:
            changed = self.db.execute("DELETE FROM host_dispatch WHERE message_id=? AND status='preparing'", (mid,))
            if changed.rowcount != 1:
                raise ChannelError('dispatch_state_conflict')
            self.wait_for_participation(mid, reason)
        self.claim_send_epochs.pop(mid)
        return {'pending': True}

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

    def poll_ordered(self, *, defer_group_execution=False):
        # Choose the next normalized projection in transport order before requiring
        # attachment bytes. The host can apply sender/group policy without downloads.
        if self.db.execute("SELECT 1 FROM host_dispatch WHERE status IN ('claimed','preparing') LIMIT 1").fetchone():
            return {'message': None}
        query = """
            SELECT model FROM inbox i WHERE i.state IN ('normalized','pending_media','media_failed')
            AND json_extract(i.model,'$.fromSelf')=0 AND json_array_length(i.model,'$.issues')=0
            AND NOT EXISTS (SELECT 1 FROM host_dispatch d WHERE d.message_id=i.message_id)
            AND NOT EXISTS (
                SELECT 1 FROM host_participation_wait w JOIN inbox earlier USING(message_id)
                WHERE w.retry_at>? AND earlier.seq<=i.seq
                  AND json_extract(earlier.model,'$.senderId')=json_extract(i.model,'$.senderId'))
            ORDER BY seq LIMIT 1"""
        row = self.db.execute(query, (time.time(),)).fetchone()
        if row is None:
            self.receive()
            row = self.db.execute(query, (time.time(),)).fetchone()
        if row is None:
            return {'message': None}
        model = json.loads(row['model'])
        if any(media_parts(model)):
            model['mediaPreparing'] = True
            return {'message': self.claim(model, 'preparing')}
        if defer_group_execution and self.route.get('conversationType') == 'group':
            # The host decides admission and may ask its tool-free model. No business
            # turn, send or file selection can run until beginGroupDispatch succeeds.
            model['participationPreparing'] = True
            return {'message': self.claim(model, 'preparing')}
        return {'message': self.claim(model)}

    def begin_group_dispatch(self, mid):
        if mid in self.cancel_matches.values():
            return {'state': 'stopping'}
        with self.db:
            changed = self.db.execute("UPDATE host_dispatch SET status='claimed' WHERE message_id=? AND status='preparing'",
                                      (mid,))
            if self.route.get('conversationType') != 'group' or changed.rowcount != 1:
                raise ChannelError('dispatch_state_conflict')
        return {'state': 'claimed'}

    def prepare_media(self, mid):
        row = self.db.execute("""
            SELECT i.seq,i.state,i.model,i.attempts FROM inbox i JOIN host_dispatch d USING(message_id)
            WHERE i.message_id=? AND d.status='preparing'""", (mid,)).fetchone()
        if row is None:
            # A pollCancel reply may be crossing stdio while the host's timer requests
            # preparation one last time. The matched stop will abort that timer.
            if mid in self.cancel_matches.values():
                return {'state': 'waiting'}
            raise ChannelError('media_preparation_requires_claim')

        def finish(model=None):
            with self.db:
                self.db.execute("UPDATE host_dispatch SET status='claimed' WHERE message_id=?", (mid,))
                if model is None:
                    self.db.execute('INSERT INTO host_media_failures VALUES (?,?)', (mid, 'original_unavailable'))
            return {'state': 'unavailable'} if model is None else {'state': 'ready', 'message': model}

        if row['state'] == 'normalized':
            ready = next(self.inbox.iter_ready([row]), None)
            if ready is not None:
                return finish(ready['message'])

        def download_original():
            model = json.loads(row['model'])
            ledger = self.api('/v1/attachments', {'message_id': mid})
            return materialize(model, ledger, self.root, self.inbox.cache_root)

        future = self.media_result(('inbound', mid), download_original)
        if future is None:
            return {'state': 'waiting'}
        try:
            model = future.result()
        except Exception as exc:
            with self.db:
                self.db.execute(
                    "UPDATE inbox SET state='media_failed',error=?,attempts=attempts+1 WHERE message_id=?",
                    (type(exc).__name__, mid))
            if row['attempts'] + 1 >= 3:
                return finish()
            return {'state': 'retrying'}
        with self.db:
            self.db.execute(
                "UPDATE inbox SET model=?,state='normalized',error=NULL,attempts=attempts+1 WHERE message_id=?",
                (json.dumps(model, ensure_ascii=False), mid))
        return finish(model)

    def media_result(self, key, read):
        # At most one attachment read per route. SQLite/dispatch state stays on the
        # stdio thread, which remains free to ingest new input and match stop commands.
        if self.media_worker is not None:
            owner, future = self.media_worker
            if not future.done():
                return None
            self.media_worker = None
            if owner == key:
                return future

        future = Future()
        def work():
            try:
                future.set_result(read())
            except Exception as exc:
                future.set_exception(exc)
        Thread(target=work, name='dingtalk-inbound-media', daemon=True).start()
        self.media_worker = (key, future)
        return None

    def poll_cancel(self, active_id):
        """During a turn, keep other work durable and search only for a later text stop."""
        active = self.db.execute("""
            SELECT i.seq, json_extract(i.model,'$.senderId') AS sender
            FROM inbox i JOIN host_dispatch d USING(message_id)
            WHERE i.message_id=? AND d.status IN ('claimed','preparing')""", (active_id,)).fetchone()
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
                # If interrupted after the stop is claimed, the original needs review;
                # the safe-to-retry pre-model state no longer applies.
                with self.db:
                    self.db.execute("UPDATE host_dispatch SET status='claimed' WHERE message_id=? AND status='preparing'",
                                    (active_id,))
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
                    or event.get('conversation_id') != self.route['group'] or event.get('conversation_type') != self.route.get('conversationType','group')):
                raise ChannelError('file_history_scope_mismatch')
            try:
                previous.append(normalize(event, self.route))
            except (ValueError, KeyError, TypeError):
                previous.append(None)  # Image positions before this row cannot be resolved safely.
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
        direct = model['conversationType'] == 'direct'
        command = addressed[1] if addressed else text if direct else None
        mixed = command is not None and (command == '--attachments' or command.startswith('--attachments '))
        if model['fromSelf'] is not False or not (mixed or file_request(model, command)):
            return {'error': 'file_selection_invalid'}
        previous = self.previous_file_candidates(row)
        try:
            task, sources = select_file_sources(model, command, previous, allow_images=mixed)
        except ValueError as exc:
            return {'error': str(exc)}
        by_id = {candidate['id']: candidate for candidate in previous if candidate is not None}
        originals = [(by_id[src['messageId']], src) for src in sources]
        # This owner serializes turns. A lost claim is quarantined on restart.
        # Retain the selected identities while originals are downloaded one at a time.
        self.file_selection = (mid, task, originals)
        return {'task': task, 'count': len(originals)}

    def selected_file(self, mid, index, background=False):
        if self.file_selection is None or self.file_selection[0] != mid:
            raise ChannelError('file_selection_requires_claim')
        originals = self.file_selection[2]
        if type(index) is not int or not 0 <= index < len(originals):
            raise ChannelError('invalid_file_selection_index')
        original, selected = originals[index]
        def read_original():
            ledger = self.api('/v1/attachments', {'message_id': original['id']})
            materialize(original, ledger, self.root, self.inbox.cache_root)
            if 'imagePartIndex' in selected:
                part = original['parts'][selected['imagePartIndex']]
                if part['type'] != 'image' or part['resource'] != selected['resource']:
                    raise ChannelError('selection_original_changed')
                return part
            part, = [p for p in original['parts'] if p['type'] == 'file'
                     and p.get('name') == selected['name'] and p['resource'] == selected['resource']]
            return part

        if not background:
            return {'part': read_original()}
        future = self.media_result(('selected', mid, index), read_original)
        return {'state': 'waiting'} if future is None else {'part': future.result()}

    def ack(self, mid, status, cancel_id=None, silent_reason=None):
        if silent_reason is not None and (status != 'done' or silent_reason not in
                                          ('agent_decision', 'agent_no_reply', 'host_policy')):
            raise ChannelError('invalid_silent_ack')
        if (not isinstance(mid, str) or status not in ('done', 'ignored', 'unknown', 'canceled')
                or (status == 'canceled' and (not isinstance(cancel_id, str) or not cancel_id))):
            raise ChannelError('invalid_ack')
        with self.db:
            row = self.db.execute('SELECT status FROM host_dispatch WHERE message_id=?', (mid,)).fetchone()
            allowed = {status}
            if silent_reason != 'agent_decision':
                allowed.add('claimed')
            if status in ('ignored', 'unknown') or silent_reason == 'agent_decision':
                allowed.add('preparing')
            if row is None or row[0] not in allowed:
                raise ChannelError('dispatch_state_conflict')
            if silent_reason and row[0] in ('claimed', 'preparing'):
                if mid not in self.claim_send_epochs:
                    raise ChannelError('silent_completion_not_proven')
                if row[0] == 'claimed' and self.claim_send_epochs[mid] != self.send_attempts:
                    # The business agent or an independent outbound queue could have sent.
                    # Keep this turn for reconciliation and leave the route able to poll.
                    status = 'unknown'
                else:
                    self.db.execute('INSERT INTO host_silent_replies VALUES (?,?)', (mid, silent_reason))
            elif row[0] == status:
                silent = self.db.execute('SELECT reason FROM host_silent_replies WHERE message_id=?', (mid,)).fetchone()
                if (silent[0] if silent else None) != silent_reason:
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
            self.db.execute('DELETE FROM host_participation_wait WHERE message_id=?', (mid,))
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
            return (self.poll_ordered(defer_group_execution=request.get('deferGroupExecution') is True)
                    if request.get('orderedMedia') is True else self.poll())
        if op == 'beginGroupDispatch':
            return self.begin_group_dispatch(request.get('messageId'))
        if op == 'prepareMedia':
            return self.prepare_media(request.get('messageId'))
        if op == 'recordMediaStageFailure':
            mid = request.get('messageId')
            with self.db:
                row = self.db.execute('SELECT d.status,i.model FROM host_dispatch d JOIN inbox i USING(message_id) '
                                      'WHERE d.message_id=?', (mid,)).fetchone()
                if row is None or row['status'] != 'claimed' or not any(media_parts(json.loads(row['model']))):
                    raise ChannelError('media_stage_failure_requires_claim')
                self.db.execute('INSERT OR IGNORE INTO host_media_failures VALUES (?,?)', (mid, 'host_stage_failed'))
            return {'recorded': True}
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
            return self.selected_file(mid, request.get('index'), request.get('background') is True)
        if op == 'groupContext':
            return {'recent': recent_group_context(self.db, request.get('messageId'), request.get('allowSenders'))}
        if op == 'deferParticipation':
            return self.defer_participation(request.get('messageId'), request.get('reason'))
        if op == 'ack':
            return self.ack(request.get('messageId'), request.get('status'), request.get('cancelMessageId'),
                            request.get('silentReason'))
        if op == 'summary':
            summary = {'cursor': self.inbox.cursor, 'dispatch': dict(self.db.execute(
                'SELECT status,count(*) FROM host_dispatch GROUP BY status'))}
            if request.get('includeInbox') is True:
                summary['participationPending'] = dict(self.db.execute(
                    'SELECT reason,count(*) FROM host_participation_wait GROUP BY reason'))
                summary['silentReplies'] = dict(self.db.execute(
                    'SELECT reason,count(*) FROM host_silent_replies GROUP BY reason'))
                summary['inboxStates'] = dict(self.db.execute('SELECT state,count(*) FROM inbox GROUP BY state'))
                summary['projectionIssues'] = self.db.execute(
                    "SELECT count(*) FROM inbox WHERE json_array_length(model,'$.issues')>0").fetchone()[0]
                summary['mediaFailures'] = dict(self.db.execute(
                    'SELECT reason,count(*) FROM host_media_failures GROUP BY reason'))
            return summary
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
    parser.add_argument('--mention-sender', action='append', default=[])
    parser.add_argument('--consumer-instance')
    parser.add_argument('--config', default='local/service-config.json')
    parser.add_argument('--port', default=18768, type=int)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    routes = route_configs(json.loads((root / args.config).read_text()))
    for route, state_name in routes:
        if (route['accountId'], route['group']) == (args.account_id, args.conversation_id):
            channel = HostChannel(root, route, state_name, args.initial_cursor,
                                  route_api(root, route, args.port), consumer_instance=args.consumer_instance,
                                  mention_senders=args.mention_sender)
            if channel.mention_index is not None:
                signal.signal(signal.SIGTERM, channel.mention_index.stop_when_drained)
            try:
                serve(channel, sys.stdin.buffer, sys.stdout)
            finally:
                channel.close()
            return
    parser.error('account/conversation route is not configured')


if __name__ == '__main__':
    main()

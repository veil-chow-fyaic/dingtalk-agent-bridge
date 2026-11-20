import base64
import hashlib
import io
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from contextlib import closing
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlsplit
from unittest.mock import patch

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.consumer import Inbox, execution_scope
from dingtalk_bridge.host_channel import ChannelError, HostChannel, route_api, serve
from test_agent_gateway import SETTINGS
from test_routing_consumer import CFG, event, ref


class Transport:
    def __init__(self, root, route):
        self.root, self.route = root, route
        self.events, self.receipts, self.sends = [], {}, []
        self.download = None
        self.header_route = route['group']
        self.lost = False

    def __call__(self, path, data=None):
        if path.startswith('/v1/events?'):
            after = int(parse_qs(urlsplit(path).query)['after'][0])
            limit = int(parse_qs(urlsplit(path).query)['limit'][0])
            page = [{'conversation_type': self.route.get('conversationType', 'group'), **item}
                    for item in self.events if item['seq'] > after][:limit]
            return {'account_id': self.route['accountId'], 'conversation_id': self.header_route,
                    'events': page, 'next_cursor': page[-1]['seq'] if page else after}
        if path == '/v1/attachments':
            return self.download
        if path == '/v1/send':
            self.sends.append(data)
            key = data['idempotency_key']
            if self.lost:
                raise OSError('synthetic interruption')
            receipt = {'key': key, 'state': 'submitted', 'task_id': 'task-' + key}
            self.receipts[key] = receipt
            return receipt
        if path.startswith('/v1/deliveries/'):
            key = unquote(path.split('/')[-1])
            if key not in self.receipts:
                raise HTTPError(path, 404, '', {}, None)
            return self.receipts[key]
        if path == '/v1/reconcile':
            item = self.receipts[data['idempotency_key']]
            item.update(state='confirmed', message_id='message-' + item['key'])
            return item
        raise AssertionError(path)


class HostChannelTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.route = {**CFG, 'executionOwner': 'openclaw'}
        self.api = Transport(self.root, self.route)
        self.channel = None
        self.open()

    def open(self, cursor=0):
        if self.channel is not None:
            self.channel.close()
        self.channel = HostChannel(self.root, self.route, None, cursor, self.api)
        self.addCleanup(self.channel.close)

    def test_poll_marks_connection_failure_distinct_from_auth_refusal(self):
        token = self.root/'local/runtime/http-token'
        token.parent.mkdir(exist_ok=True, parents=True)
        token.write_text('synthetic')
        call = route_api(self.root,self.route,42001)
        with patch('dingtalk_bridge.host_channel.urlopen', side_effect=ConnectionRefusedError()):
            with self.assertRaisesRegex(ChannelError,'transport_unavailable'):
                call('/v1/events?after=0')
        with patch('dingtalk_bridge.host_channel.urlopen', side_effect=HTTPError('url',403,'forbidden',{},None)):
            with self.assertRaises(HTTPError) as auth:
                call('/v1/events?after=0')
            with auth.exception:
                self.assertEqual(auth.exception.code,403)

    def test_only_confirmed_same_route_host_text_can_supply_quote_context(self):
        db_path = self.channel.inbox.cache_root.with_name('bridge.sqlite3')
        db_path.parent.mkdir(exist_ok=True, parents=True)
        with closing(sqlite3.connect(db_path)) as transport, transport:
            transport.executescript("""
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE deliveries (key TEXT, state TEXT, message_id TEXT, payload TEXT);
            """)
            transport.execute("INSERT INTO meta VALUES ('scope',?)",
                              (json.dumps([self.route['profile'], self.route['group']]),))
            for key, state, kind in [('own','confirmed','text'), ('other','confirmed','text'),
                                     ('pending','submitted','text'), ('photo','confirmed','image')]:
                transport.execute('INSERT INTO deliveries VALUES (?,?,?,?)',
                                  (key,state,'out-'+key,json.dumps({'kind':kind,'text':'建议'})))
                if key != 'other':
                    with self.channel.db:
                        self.channel.db.execute('INSERT INTO host_sends VALUES (?,?)',(key,hashlib.sha256(json.dumps({'text':'建议'}).encode()).hexdigest()))
        seq = 0
        def poll_quote(key='own', text='建议', sender='self'):
            nonlocal seq
            seq += 1
            source={'conversationId':'g','messageId':'out-'+key,'text':text,'senderId':sender}
            self.api.events.append(event(seq,text='展开',quote=source))
            msg=self.channel.poll_ordered()['message']
            self.channel.ack(msg['id'],'done')
            return msg

        for kind in ['group','direct']:
            self.route['conversationType']=kind
            for source in ['self', None]:
                verified=poll_quote(sender=source)
                self.assertTrue(verified.get('confirmedHostTextQuote'))
                self.assertEqual(verified['quote']['senderId'],'self')
            for invalid in [dict(key='other'),dict(key='pending'),dict(key='photo'),
                            dict(key='missing'),dict(text='不同正文'),dict(sender='third-person')]:
                self.assertFalse(poll_quote(**invalid).get('confirmedHostTextQuote'))
        with closing(sqlite3.connect(db_path)) as transport, transport:
            transport.execute("UPDATE meta SET value='[]'")
        self.assertFalse(poll_quote().get('confirmedHostTextQuote'))

    def test_dispatch_restart_and_self_echo(self):
        self.api.events = [event(1, sender='self'), event(2, sender=''), event(3, text='[Agent] user text'),
                           event(4, text='second'), event(5, text='third')]
        self.assertEqual(self.channel.poll()['message']['parts'], [{'type': 'text', 'text': '[Agent] user text'}])
        self.assertEqual(self.channel.poll()['message']['id'], 'm4')
        self.channel.ack('m4', 'done')
        self.open(cursor=100)
        self.assertEqual(self.channel.poll()['message']['id'], 'm5')
        self.channel.ack('m5', 'ignored')
        self.assertIsNone(self.channel.poll()['message'])
        self.assertEqual(self.channel.handle({'op': 'summary'}),
                         {'cursor': 5, 'dispatch': {'unknown': 1, 'done': 1, 'ignored': 1}})
        self.assertEqual(self.channel.ack('m4', 'done'), {'status': 'done'})
        with self.assertRaisesRegex(ChannelError, 'dispatch_state_conflict'):
            self.channel.ack('m3', 'done')

    def test_cancel_scan_bypasses_ordinary_backlog_without_claiming_waiting_work(self):
        self.api.events = [event(1, text='/agent slow')]
        original = self.channel.poll()['message']
        # The first 400 events include ordinary peer jobs, a different sender's
        # stop, a self echo, a quoted stop and a DM-only command in a group.
        for seq in range(2, 404):
            self.api.events.append(event(seq, text=f'/agent queued {seq}'))
        self.api.events[10] = event(11, text='/agent cancel', sender='stranger')
        self.api.events[11] = event(12, text='/agent cancel', sender='self')
        self.api.events[12] = event(13, text='/stop')
        self.api.events[13] = event(14, text='/agent cancel', quote={'conversationId':'g','text':'example'})
        self.api.events.append(event(404, text='/agent cancel'))
        cancel = {'op': 'pollCancel', 'activeMessageId': original['id']}
        self.assertEqual(self.channel.handle(cancel), {'message': None, 'hasMore': True})
        self.assertEqual(self.channel.inbox.cursor, 201)
        self.assertEqual(self.channel.handle(cancel), {'message': None, 'hasMore': True})
        self.assertEqual(self.channel.inbox.cursor, 401)
        control = self.channel.handle(cancel)['message']
        self.assertEqual(control['id'], 'm404')
        self.channel.ack(control['id'], 'done')
        self.assertEqual(self.channel.handle({'op': 'summary'})['dispatch'], {'claimed': 1, 'done': 1})
        # Simulate abrupt host death: only the active turn may have side effects.
        self.open()
        self.assertEqual(self.channel.handle({'op': 'summary'})['dispatch'], {'unknown': 1, 'done': 1})
        for seq in range(2, 11):
            waiting = self.channel.poll()['message']
            self.assertEqual(waiting['id'], f'm{seq}')
            self.channel.ack(waiting['id'], 'done')

    def test_control_must_follow_active_turn_and_match_real_sender(self):
        self.api.events = [event(1, text='/agent cancel'), event(2, text='/agent new')]
        first = self.channel.poll()['message']
        self.channel.ack(first['id'], 'ignored')
        active = self.channel.poll()['message']
        self.assertIsNone(self.channel.poll_cancel(active['id'])['message'])
        self.channel.ack(active['id'], 'done')
        self.api.events.append(event(3, text='/agent cancel'))
        self.assertIsNone(self.channel.poll_cancel(active['id'])['message'])
        self.assertIsNone(self.channel.poll_cancel('unknown-id')['message'])

    def canceled_turn(self):
        self.api.events = [event(1, text='/agent work'), event(2, text='/agent cancel'),
                           event(3, text='/agent next')]
        self.assertEqual(self.channel.poll()['message']['id'], 'm1')
        self.assertEqual(self.channel.poll_cancel('m1')['message']['id'], 'm2')
        self.channel.ack('m2', 'done')

    def test_confirmed_unsent_cancellation_is_terminal_across_restart(self):
        self.canceled_turn()
        request = {'op': 'ack', 'messageId': 'm1', 'status': 'canceled', 'cancelMessageId': 'm2'}
        self.assertEqual(self.channel.handle(request), {'status': 'canceled'})
        mapping = [tuple(row) for row in self.channel.db.execute('SELECT * FROM host_cancellations')]
        self.assertEqual(mapping, [('m1', 'm2')])
        self.open()
        self.assertEqual(self.channel.handle(request), {'status': 'canceled'})
        with self.assertRaisesRegex(ChannelError, 'dispatch_state_conflict'):
            self.channel.handle({**request, 'cancelMessageId': 'm3'})
        self.assertEqual([tuple(row) for row in self.channel.db.execute('SELECT * FROM host_cancellations')], mapping)
        self.assertEqual(self.channel.handle({'op': 'summary'})['dispatch'], {'canceled': 1, 'done': 1})
        self.assertEqual(self.channel.poll()['message']['id'], 'm3')

    def test_cancellation_mapping_and_terminal_status_commit_atomically(self):
        self.canceled_turn()
        self.channel.db.execute("""CREATE TRIGGER reject_cancel BEFORE UPDATE OF status ON host_dispatch
            WHEN NEW.status='canceled' BEGIN SELECT RAISE(ABORT, 'synthetic commit failure'); END""")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'synthetic commit failure'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.assertEqual(self.channel.db.execute('SELECT count(*) FROM host_cancellations').fetchone()[0], 0)
        self.assertEqual(self.channel.db.execute("SELECT status FROM host_dispatch WHERE message_id='m1'").fetchone()[0], 'claimed')
        self.channel.db.execute('DROP TRIGGER reject_cancel')
        self.assertEqual(self.channel.ack('m1', 'canceled', 'm2'), {'status': 'canceled'})

    def test_cancellation_requires_matching_stop_and_acknowledged_control(self):
        self.api.events = [event(1, text='/agent work'), event(2, text='/agent cancel', sender='stranger'),
                           event(3, text='/agent cancel')]
        self.channel.poll()
        with self.assertRaisesRegex(ChannelError, 'invalid_ack'):
            self.channel.ack('m1', 'canceled')
        with self.assertRaisesRegex(ChannelError, 'cancellation_not_proven'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.assertEqual(self.channel.poll_cancel('m1')['message']['id'], 'm3')
        with self.assertRaisesRegex(ChannelError, 'cancellation_not_proven'):
            self.channel.ack('m1', 'canceled', 'm3')
        self.channel.ack('m3', 'done')
        with self.assertRaisesRegex(ChannelError, 'cancellation_not_proven'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.assertEqual(self.channel.ack('m1', 'canceled', 'm3'), {'status': 'canceled'})

    def test_send_before_stop_keeps_unknown_and_cannot_be_reclassified(self):
        self.canceled_turn()
        self.channel.handle({'op': 'send', 'key': 'submitted', 'text': 'already sent'})
        with self.assertRaisesRegex(ChannelError, 'cancellation_not_proven'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.channel.ack('m1', 'unknown')
        with self.assertRaisesRegex(ChannelError, 'dispatch_state_conflict'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.open()
        self.assertEqual(self.channel.poll()['message']['id'], 'm3')
        self.assertEqual(len(self.api.sends), 1)
        self.assertEqual(self.channel.db.execute('SELECT count(*) FROM host_cancellations').fetchone()[0], 0)

    def test_lost_send_response_and_restarted_stop_proof_stay_unknown(self):
        self.canceled_turn()
        self.api.lost = True
        with self.assertRaises(OSError):
            self.channel.handle({'op': 'send', 'key': 'lost', 'text': 'uncertain'})
        with self.assertRaisesRegex(ChannelError, 'cancellation_not_proven'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.open()
        with self.assertRaisesRegex(ChannelError, 'dispatch_state_conflict'):
            self.channel.ack('m1', 'canceled', 'm2')
        self.assertEqual(self.channel.handle({'op': 'summary'})['dispatch'], {'unknown': 1, 'done': 1})
        self.assertEqual(self.channel.db.execute('SELECT count(*) FROM host_cancellations').fetchone()[0], 0)
        self.assertEqual(self.channel.poll()['message']['id'], 'm3')

    def test_earlier_turn_send_does_not_block_new_unsent_cancellation(self):
        self.channel.handle({'op': 'send', 'key': 'earlier', 'text': 'earlier turn'})
        self.canceled_turn()
        self.assertEqual(self.channel.ack('m1', 'canceled', 'm2'), {'status': 'canceled'})

    def test_quoted_group_attachment_sha_and_bad_bytes(self):
        self.api.events = [event(1, text='/agent inspect this', refs=[ref('fileId', 'source')], quote={
            'messageId': 'original', 'senderId': 'other', 'conversationId': 'g',
            'text': '[文件] input.csv fileId: source', 'resourceRefs': [ref('fileId', 'source')]})]
        target = self.root / 'local/runtime/downloads/original/input.csv'
        target.parent.mkdir(parents=True)
        content = b'item,qty\nx,2'
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        record = {**ref('fileId', 'source'), 'localPath': str(target.relative_to(self.root)),
                  'sha256': '0' * 64, 'sizeBytes': len(content)}
        self.api.download = {'ok': True, 'downloads': [record]}
        self.assertIsNone(self.channel.poll()['message'])
        record['sha256'] = digest
        model = self.channel.poll()['message']
        self.assertEqual(model['quote']['id'], 'original')
        self.assertEqual(model['quote']['parts'][0]['sha256'], digest)
        self.assertEqual(Path(model['quote']['parts'][0]['path']).read_bytes(), content)

    def test_initial_cursor_and_direct_route(self):
        self.route = {**self.route, 'conversationType': 'direct'}
        self.api.route = self.route
        self.api.events = [event(1), event(2)]
        self.open(cursor=1)
        self.assertEqual(self.channel.poll()['message']['conversationType'], 'direct')
        self.assertEqual(self.channel.ack('m2', 'done'), {'status': 'done'})
        self.api.events.append({**event(3), 'conversation_type': 'group'})
        with self.assertRaisesRegex(ChannelError, 'transport_conversation_type_mismatch'):
            self.channel.poll()
        self.api.header_route = 'different'
        with self.assertRaisesRegex(ChannelError, 'transport_route_mismatch'):
            self.channel.poll()

    def test_owner_opt_in_and_old_gateway_lock_each_direction(self):
        with self.assertRaisesRegex(ValueError, 'another execution owner'):
            Gateway(self.root, self.route, None, SETTINGS)
        with self.assertRaisesRegex(ValueError, 'consumer_already_owned'):
            Gateway(self.root, CFG, None, SETTINGS, self.api)
        self.channel.close()
        with self.assertRaisesRegex(ChannelError, 'route_not_configured_for_host'):
            HostChannel(self.root, CFG, None, 0, self.api)
        _, key = execution_scope(CFG)
        # Mimic even the old gateway binary, which knows only this existing Inbox lock.
        legacy = Inbox(self.root, CFG, 'agent-' + key)
        try:
            with self.assertRaisesRegex(ValueError, 'consumer_already_owned'):
                HostChannel(self.root, self.route, None, 0, self.api)
        finally:
            legacy.close()

    def test_named_instance_starts_at_reviewed_cut_and_preserves_other_inboxes(self):
        self.api.events = [event(1), event(2), event(3)]
        self.assertEqual(self.channel.poll()['message']['id'], 'm1')
        self.channel.ack('m1', 'unknown')
        with self.assertRaisesRegex(ValueError, 'consumer_already_owned'):
            HostChannel(self.root, self.route, None, 3, self.api, consumer_instance='pilot')
        self.channel.close()
        _, key = execution_scope(self.route)
        retired = self.root / 'local/consumers' / ('openclaw-' + key)
        frozen = {p.name: p.read_bytes() for p in retired.iterdir() if p.name != 'process.lock'}
        self.api.events.extend([event(4), event(5)])
        pilot = HostChannel(self.root, self.route, None, 3, self.api, consumer_instance='pilot')
        try:
            self.assertEqual(pilot.poll()['message']['id'], 'm4')
            pilot.ack('m4', 'done')
            for candidate in (None, 'second'):
                with self.assertRaisesRegex(ValueError, 'consumer_already_owned'):
                    HostChannel(self.root, self.route, None, 0, self.api, consumer_instance=candidate)
            with self.assertRaisesRegex(ValueError, 'consumer_already_owned'):
                Gateway(self.root, CFG, None, SETTINGS, self.api)
        finally:
            pilot.close()
        resumed = HostChannel(self.root, self.route, None, 0, self.api, consumer_instance='pilot')
        try:
            self.assertEqual(resumed.poll()['message']['id'], 'm5')
            resumed.ack('m5','done')
            self.assertIsNone(resumed.poll()['message'])
        finally:
            resumed.close()
        self.assertEqual(frozen,{p.name:p.read_bytes() for p in retired.iterdir() if p.name!='process.lock'})

    def test_invalid_named_instance_rejected_before_locks_or_directory_creation(self):
        for invalid in ('', '../pilot', 'p/x', '-p', 'p_' , 'p\n', 'P', 'a' * 33, 42):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ChannelError, 'invalid_consumer_instance'):
                HostChannel(self.root, self.route, None, 0, self.api, consumer_instance=invalid)

    def test_output_is_literal_and_retries_query_original_key(self):
        key = 'answer/1'
        text = '  [Agent] explicitly chosen\nline\n'
        request = {'op': 'send', 'text': text, 'key': key, 'replyTo': 'source-message'}
        self.assertEqual(self.channel.handle(request)['state'], 'submitted')
        result = self.channel.handle(request)
        self.assertEqual(result['message_id'], 'message-' + key)
        self.assertEqual(self.api.sends, [{'idempotency_key': key, 'text': text, 'reply_to': 'source-message'}])
        self.open()
        self.assertEqual(self.channel.handle({'op': 'status', 'key': key})['state'], 'confirmed')
        with self.assertRaisesRegex(ChannelError, 'idempotency_conflict'):
            self.channel.handle({**request, 'text': 'different'})

    def test_lost_submission_is_ambiguous_no_repeat_even_if_service_has_no_receipt(self):
        request = {'op': 'send', 'key': 'ambiguous', 'text': 'first'}
        self.api.lost = True
        with self.assertRaises(OSError):
            self.channel.handle(request)
        self.open()
        self.assertEqual(self.channel.handle(request)['state'], 'outcome_unknown')
        self.assertEqual(self.channel.handle({'op': 'reconcile', 'key': 'ambiguous'})['state'], 'outcome_unknown')
        self.assertEqual(len(self.api.sends), 1)
        with self.assertRaisesRegex(ChannelError, 'unknown_host_key'):
            self.channel.handle({'op': 'status', 'key': 'foreign'})

    def test_host_authorized_bytes_staged_under_correct_filename_and_digest(self):
        body = b'synthetic original'
        digest = hashlib.sha256(body).hexdigest()
        media = {'filename': '结果.pdf', 'kind': 'file', 'base64': base64.b64encode(body).decode(),
                 'sha256': digest}
        self.channel.handle({'op': 'send', 'key': 'media', 'media': media})
        sent = self.api.sends[0]
        self.assertEqual(sent['expected_sha256'], digest)
        stage = Path(sent['file'])
        self.assertEqual(stage.name, '结果.pdf')
        self.assertTrue(stage.is_relative_to('local/outbox'))
        self.assertEqual((self.root / stage).read_bytes(), body)
        for change in [{'filename': '../secret'}, {'sha256': '0'*64}, {'base64': '$%^'}]:
            with self.subTest(change=change), self.assertRaises(ChannelError):
                self.channel.handle({'op': 'send', 'key': 'other', 'media': {**media, **change}})
        self.assertEqual(len(self.api.sends), 1)

    def test_image_fallback_decided_only_on_first_submission(self):
        media = {'filename': 'original.png', 'kind': 'image', 'base64': base64.b64encode(b'fixture').decode()}
        request = {'op': 'send', 'media': media, 'key': 'same-image'}
        self.channel.handle(request)
        self.assertIn('file', self.api.sends[0])
        self.route['imageUploadBinary'] = 'newly-enabled'
        self.open()
        self.assertEqual(self.channel.handle(request)['state'], 'confirmed')
        self.assertEqual(len(self.api.sends), 1)

    def test_frames_and_loopback_request_never_forward_unspecified_scope(self):
        # Route and bearer come exclusively from the configured sidecar and bridge root.
        token = self.root / 'local/runtime/http-token'
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text('synthetic-test')
        def check(request, timeout):
            self.assertEqual(request.full_url, 'http://127.0.0.1:43210/v1/send')
            self.assertEqual(json.loads(request.data)['conversation_id'], 'g')
            self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-test')
            return io.BytesIO(b'{}')
        with patch('dingtalk_bridge.host_channel.urlopen', side_effect=check):
            route_api(self.root, self.route, 43210)('/v1/send', {'conversation_id': 'other'})
        with self.assertRaisesRegex(ChannelError, 'request_route_mismatch'):
            self.channel.handle({'op': 'send', 'conversationId': 'other', 'text': 'wrong route', 'key': 'k'})
        stdout = io.StringIO()
        serve(self.channel, io.BytesIO(b'{bad}\n{"id":1,"op":"summary"}\n'), stdout)
        frames = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(frames[0], {'id': None, 'ok': False, 'error': 'JSONDecodeError'})
        self.assertTrue(frames[1]['ok'])

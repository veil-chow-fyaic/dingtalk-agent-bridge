import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from types import SimpleNamespace
from dingtalk_bridge.core import Bridge, BridgeError, DWS

CFG = {'profile': 'corp:user', 'group': 'g', 'name': 'test', 'selfSenderId': 'self', 'binary': 'dws',
       'imageUploadBinary': 'dws-image-upload'}

class Fake:
    def __init__(self):
        self.sent = 0
        self.fail = False
        self.complete = True
        self.uploaded = 0
        self.send_args = []
        self.messages = [{'messageId': 'm1', 'conversationId': 'g', 'senderId': 'self', 'text': 'same'},
                         {'messageId': 'm2', 'conversationId': 'g', 'senderId': 'other', 'text': 'same'}]
    def call(self, args):
        if '+messages-send' in args or '+messages-reply' in args:
            self.sent += 1
            self.send_args.append(args)
            if self.fail: raise BridgeError('timeout')
            return {'sendReceipt': {'openTaskId': 'task'}}
        if '+messages-query-send-status' in args:
            return {'result': {'sendStatus': 'SUCCESS'}, 'messageRef': {'openConversationId': 'g', 'openMessageId': 'sent'}}
        if '+chat-messages' in args:
            return {'messages': self.messages, 'count': len(self.messages), 'complete': self.complete}
        raise AssertionError(args)

    def upload_image(self, path):
        self.uploaded += 1
        return '$uploaded'

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fake = Fake()
        self.b = Bridge(self.root, CFG, self.fake)
    def tearDown(self):
        self.b.close()
        self.tmp.cleanup()
    def test_plain_text_and_quoted_reply_keep_literal_image_syntax(self):
        text = '  [Agent] 原文\n![例](./missing-image.png)\n  '
        self.b.sync()
        for key, source in [('literal', None), ('quote-literal', 'm2')]:
            self.assertEqual(self.b.send(key, text=text, reply_to=source)['state'], 'confirmed')
            args = self.fake.send_args[-1]
            flag = '--content' if source else '--text'
            self.assertEqual(args[args.index(flag)+1], text)
            self.assertNotIn('--markdown', args)
            self.assertTrue(self.b.send(key, text=text, reply_to=source)['replayed'])
        self.assertEqual((self.fake.sent, self.fake.uploaded), (2, 0))

    def test_idempotency_survives_restart(self):
        self.assertEqual(self.b.send('k', text='hello')['state'], 'confirmed')
        self.b.close()
        self.b = Bridge(self.root, CFG, self.fake)
        self.assertTrue(self.b.send('k', text='hello')['replayed'])
        self.assertEqual(self.fake.sent, 1)
        with self.assertRaises(ValueError): self.b.send('k', text='changed')
        self.assertEqual(self.fake.sent, 1)
    def test_unknown_is_never_resent(self):
        self.fake.fail = True
        self.assertEqual(self.b.send('k', text='hello')['state'], 'outcome_unknown')
        self.b.send('k', text='hello')
        self.assertEqual(self.fake.sent, 1)
    def test_quote_identity_survives_restart_and_binds_source(self):
        self.b.sync()
        self.assertEqual(self.b.send('quote', text='reply', reply_to='m2')['state'], 'confirmed')
        self.assertIn('+messages-reply', self.fake.send_args[0])
        self.assertIn('--content', self.fake.send_args[0])
        self.b.close(); self.b = Bridge(self.root, CFG, self.fake)
        self.assertTrue(self.b.send('quote', text='reply', reply_to='m2')['replayed'])
        for ref in ('m1', None):
            with self.assertRaises(ValueError): self.b.send('quote', text='reply', reply_to=ref)
        self.assertEqual(self.fake.sent, 1)

    def test_quote_rejects_missing_foreign_or_unknown_sender_before_reservation(self):
        self.b.sync()
        original = json.loads(self.b.db.execute('SELECT body FROM events WHERE message_id="m2"').fetchone()[0])
        for field, value in [('account_id', 'foreign'), ('conversation_id', 'foreign'), ('sender_id', None), ('message_id', 'foreign')]:
            with self.subTest(field=field):
                event = {**original, field: value}
                self.b.db.execute('UPDATE events SET body=? WHERE message_id="m2"', (json.dumps(event),))
                self.b.db.commit()
                with self.assertRaises(ValueError): self.b.send('bad', text='reply', reply_to='m2')
                self.assertIsNone(self.b.delivery('bad'))
        for ref in ('missing', '', ' m2', 7, {}):
            with self.assertRaises(ValueError): self.b.send('bad', text='reply', reply_to=ref)
        for mode in ('file', 'image'):
            with self.assertRaises(ValueError): self.b.send('bad', **{mode: 'fixtures/a.png'}, reply_to='m2')
        self.assertEqual(self.fake.sent, 0); self.assertEqual(self.fake.uploaded, 0)

    def test_quote_unknown_restart_never_reissues_even_if_source_removed(self):
        self.b.sync(); self.fake.fail = True
        self.assertEqual(self.b.send('quote', text='reply', reply_to='m2')['state'], 'outcome_unknown')
        self.b.db.execute('DELETE FROM events'); self.b.db.commit()
        self.b.close(); self.b = Bridge(self.root, CFG, self.fake)
        self.assertTrue(self.b.send('quote', text='reply', reply_to='m2')['replayed'])
        self.assertEqual(self.b.reconcile('quote')['state'], 'outcome_unknown')
        self.assertEqual(self.fake.sent, 1)

    def test_quote_direct_binds_both_peer_and_conversation(self):
        self.b.close()
        self.b = Bridge(self.root, {**CFG, 'conversationType': 'direct', 'peerOpenDingTalkId': 'peer'}, self.fake)
        self.b.sync(); self.b.send('quote', text='reply', reply_to='m2')
        args = self.fake.send_args[0]
        self.assertEqual(args[args.index('--group') + 1], 'g')
        self.assertEqual(args[args.index('--open-dingtalk-id') + 1], 'peer')

    def test_quote_raw_group_receipt_and_ambiguous_result(self):
        self.b.sync(); original = self.fake.call
        for index, receipt in enumerate(({'result': {'openTaskId': 'task'}},
                                        {'result': [{'openTaskId': 'task'}, {'openTaskId': 'other-task'}]},
                                        {'referencedMessage': {'openTaskId': 'source-task'}})):
            with patch.object(self.fake, 'call', side_effect=lambda args: receipt if '+messages-reply' in args else original(args)):
                value = self.b.send('raw' + str(index), text='reply', reply_to='m2')
            self.assertEqual(value['state'], 'confirmed' if index == 0 else 'outcome_unknown')
    def test_personal_text_limit_counts_utf16_before_any_send_or_reservation(self):
        self.assertEqual(self.b.send('edge',text='🙂'*2560)['state'],'confirmed')
        for text in ('a'*5121, '🙂'*2560+'a', '中'*5121):
            with self.assertRaisesRegex(ValueError,'5120 UTF-16'):
                self.b.send('oversize',text=text)
        self.assertEqual(self.fake.sent,1)
        self.assertIsNone(self.b.delivery('oversize'))

    def test_historical_oversized_unknown_is_not_rechunked_or_resent(self):
        payload=json.dumps({'kind':'text','text':'🙂'*3000},sort_keys=True,ensure_ascii=False)
        self.b.db.execute('INSERT INTO deliveries(key,fingerprint,payload,state,error) VALUES (?,?,?,?,?)',
            ('old',hashlib.sha256(payload.encode()).hexdigest(),payload,'outcome_unknown','PARAM_ERROR'))
        self.b.db.commit()
        receipt=self.b.send('old',text='🙂'*3000)
        self.assertTrue(receipt['replayed']);self.assertEqual(receipt['state'],'outcome_unknown')
        self.assertEqual(self.fake.sent,0)
    def test_crashed_reservation_is_unknown(self):
        self.b.db.execute('INSERT INTO deliveries(key,fingerprint,payload,state) VALUES (?,?,?,?)', ('k','fp','{}','executing'))
        self.b.db.commit()
        self.b.close()
        self.b = Bridge(self.root, CFG, self.fake)
        self.assertEqual(self.b.delivery('k')['state'], 'outcome_unknown')
        self.assertEqual(self.fake.sent, 0)
    def test_history_dedup_uses_identity_not_text(self):
        self.assertEqual(self.b.sync()['inserted'], 2)
        self.assertEqual(self.b.sync()['inserted'], 0)
        events = self.b.events()
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]['from_self'])
        self.assertFalse(events[1]['from_self'])
        self.assertEqual(len(self.b.events(after=events[0]['seq'])), 1)
    def test_partial_history_does_not_advance_watermark(self):
        self.fake.complete = False
        self.assertFalse(self.b.sync()['complete'])
        self.assertIsNone(self.b.db.execute('SELECT value FROM meta WHERE key="watermark"').fetchone())
    def test_missing_sender_remains_unknown(self):
        self.fake.messages[0].pop('senderId')
        self.b.sync()
        self.assertIsNone(self.b.events()[0]['from_self'])
    def test_health_counts_only_observed_peer_events(self):
        self.assertEqual(self.b.health()['other_member_inbound'],'not_observed')
        self.fake.messages.append({'messageId':'unknown','conversationId':'g','text':'unknown sender'})
        self.assertEqual(self.b.sync()['other_member_events_observed'],1)
        self.assertEqual(self.b.health()['other_member_events'],1)
        self.assertEqual(self.b.health()['other_member_inbound'],'observed')
    def test_partial_history_recovers_after_restart(self):
        self.fake.complete = False
        self.b.sync()
        self.b.close()
        self.b = Bridge(self.root, CFG, self.fake)
        self.fake.complete = True
        self.fake.messages.append({'messageId':'m3','conversationId':'g','senderId':'other','text':'after outage'})
        self.assertEqual(self.b.sync()['inserted'],1)
        self.assertEqual(len(self.b.events()),3)
        self.assertIsNotNone(self.b.db.execute('SELECT value FROM meta WHERE key="watermark"').fetchone())
    def test_cross_scope_rolls_back_entire_batch(self):
        self.fake.messages[1]['conversationId'] = 'wrong'
        with self.assertRaises(BridgeError): self.b.sync()
        self.assertEqual(self.b.events(), [])
    def test_file_boundary_and_content_binding(self):
        with self.assertRaises(ValueError): self.b.send('k', file='../private')
        (self.root/'fixtures').mkdir()
        f=self.root/'fixtures/a.txt';f.write_text('original')
        self.b.send('k', file='fixtures/a.txt')
        f.write_text('changed')
        with self.assertRaises(ValueError): self.b.send('k', file='fixtures/a.txt')
        self.assertEqual(self.fake.sent, 1)
    def test_image_has_separate_payload_identity(self):
        (self.root/"fixtures").mkdir()
        (self.root/"fixtures/image.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        self.assertEqual(self.b.send("img", image="fixtures/image.png")["state"], "confirmed")
        with self.assertRaises(ValueError): self.b.send("img", file="fixtures/image.png")
        self.assertEqual(self.fake.sent, 1)
        self.assertEqual(self.fake.uploaded, 1)
        self.assertIn('--media-id', self.fake.send_args[0])
        self.assertNotIn('--markdown', self.fake.send_args[0])

    def image_fixture(self):
        path = self.root / 'fixtures/image.png'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        return 'fixtures/image.png'

    def test_native_image_restart_does_not_upload_or_send_twice(self):
        f = self.image_fixture()
        self.b.send('img', image=f)
        self.b.close(); self.b = Bridge(self.root, CFG, self.fake)
        receipt = self.b.send('img', image=f)
        self.assertTrue(receipt['replayed'])
        self.assertEqual(receipt['upload_state'], 'uploaded')
        self.assertEqual((self.fake.uploaded, self.fake.sent), (1, 1))

    def test_image_upload_timeout_never_attempts_message(self):
        f = self.image_fixture()
        with patch.object(self.fake, 'upload_image', side_effect=BridgeError('timeout')) as upload:
            self.assertEqual(self.b.send('img', image=f)['state'], 'upload_unknown')
            self.b.close(); self.b = Bridge(self.root, CFG, self.fake)
            self.b.send('img', image=f)
            self.b.reconcile('img')
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(self.fake.sent, 0)

    def test_crash_during_image_upload_preserves_unknown_and_no_resend(self):
        f = self.image_fixture()
        with patch.object(self.fake, 'upload_image', side_effect=SystemExit):
            with self.assertRaises(SystemExit): self.b.send('img', image=f)
        self.b.close(); self.b = Bridge(self.root, CFG, self.fake)
        self.assertEqual(self.b.send('img', image=f)['state'], 'upload_unknown')
        self.assertEqual(self.fake.sent, 0)

    def test_crash_after_image_upload_preserves_media_and_never_resends(self):
        f = self.image_fixture()
        with patch.object(self.fake, 'call', side_effect=SystemExit):
            with self.assertRaises(SystemExit): self.b.send('img', image=f)
        self.b.close(); self.b = Bridge(self.root, CFG, self.fake)
        receipt = self.b.send('img', image=f)
        self.assertEqual(receipt['state'], 'outcome_unknown')
        self.assertEqual(receipt['upload_state'], 'uploaded')
        self.assertEqual(self.b.db.execute('SELECT media_id FROM image_uploads').fetchone()[0], '$uploaded')
        self.assertEqual((self.fake.uploaded, self.fake.sent), (1, 0))

    def test_legacy_inline_key_keeps_receipt_without_native_upload(self):
        f = self.image_fixture()
        digest = hashlib.sha256((self.root/f).read_bytes()).hexdigest()
        payload = json.dumps({'kind':'image', 'sha256':digest, 'name':'image.png',
                              'staged':f'local/runtime/staged/{digest}/image.png'}, sort_keys=True, ensure_ascii=False)
        self.b.db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?,?,?)',
                          ('old', hashlib.sha256(payload.encode()).hexdigest(), payload, 'confirmed', 'oldtask', 'oldmsg', None))
        self.b.db.commit()
        self.b.config = {k:v for k,v in CFG.items() if k != 'imageUploadBinary'}
        self.assertTrue(self.b.send('old', image=f)['replayed'])
        self.assertEqual((self.fake.uploaded, self.fake.sent), (0, 0))
        with self.assertRaisesRegex(ValueError, 'imageUploadBinary'): self.b.send('new', image=f)
        self.assertIsNone(self.b.delivery('new'))

    def test_image_validation_and_corrupt_stage_fail_before_remote_calls(self):
        f = self.image_fixture()
        for data in (b'not PNG', b'\x89PNG\r\n\x1a\n' + b'x' * (2*1024*1024)):
            (self.root/f).write_bytes(data)
            with self.assertRaises(ValueError): self.b.send('invalid', image=f)
        self.image_fixture()
        digest = hashlib.sha256((self.root/f).read_bytes()).hexdigest()
        stage = self.b.local / 'staged' / digest / 'image.png'
        stage.parent.mkdir(parents=True, exist_ok=True); stage.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'integrity'): self.b.send('corrupt', image=f)
        self.assertEqual((self.fake.uploaded, self.fake.sent), (0, 0))

    def test_interrupted_file_staging_can_retry_without_reserving_or_sending(self):
        source = self.root / 'fixtures' / 'table.csv'
        source.parent.mkdir(exist_ok=True)
        data = b'item,units\nA,12\n'
        source.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        target = self.b.local / 'staged' / digest / source.name
        with patch('os.fsync', side_effect=OSError('no space')), self.assertRaises(OSError):
            self.b.send('table', file='fixtures/table.csv')
        self.assertFalse(target.exists())
        self.assertIsNone(self.b.delivery('table'))
        self.assertEqual(self.fake.sent, 0)
        self.assertEqual(self.b.send('table', file='fixtures/table.csv')['state'], 'confirmed')
        self.assertEqual(target.read_bytes(), data)

    def test_concurrent_sends_recover_unreserved_legacy_partial_file(self):
        source = self.root / 'fixtures' / 'table.csv'
        source.parent.mkdir(exist_ok=True)
        data = b'item,units\nA,12\n'
        source.write_bytes(data)
        target = self.b.local / 'staged' / hashlib.sha256(data).hexdigest() / source.name
        target.parent.mkdir(parents=True)
        target.write_bytes(data[:4])
        with ThreadPoolExecutor(max_workers=2) as pool:
            receipts = list(pool.map(lambda key: self.b.send(key, file='fixtures/table.csv'), ('one', 'two')))
        self.assertTrue(all(r['state'] == 'confirmed' for r in receipts))
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(self.fake.sent, 2)
        target.write_bytes(data[:4])
        with self.assertRaisesRegex(ValueError, 'integrity'):
            self.b.send('new', file='fixtures/table.csv')
        self.assertEqual(target.read_bytes(), data[:4])

    def test_dws_upload_requires_v2_chat_image_without_compression(self):
        cli = DWS(self.root, CFG)
        good = {'mediaIdV2':'$v2','bizType':'CHAT_IMAGE','compressed':False}
        with patch.object(DWS, 'call', return_value=good) as call:
            self.assertEqual(cli.upload_image('fixtures/image.png'), '$v2')
            self.assertEqual(call.call_args.args[0], ['chat','bridge-image-upload','--file','fixtures/image.png','--yes'])
        for change in ({'mediaIdV2':''}, {'mediaIdV2':'@v1'}, {'compressed':True}, {'bizType':'approval_image'}):
            with patch.object(DWS, 'call', return_value={**good, **change}):
                with self.assertRaises(BridgeError): cli.upload_image('fixtures/image.png')
    def test_unobserved_attachment_rejected(self):
        with self.assertRaises(ValueError): self.b.download('unknown')
    def test_single_owner(self):
        with self.assertRaises(BridgeError): Bridge(self.root, CFG, self.fake)
    def test_cli_envelope_and_stderr_error(self):
        cli=DWS(self.root,CFG)
        with patch('dingtalk_bridge.core.run_dws', return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'ok':True,'outcome':'pending','data':{'success':True,'result':{'openTaskId':'t'}}}),stderr='')):
            self.assertEqual(cli.call([])['result']['openTaskId'],'t')
        with patch('dingtalk_bridge.core.run_dws', return_value=SimpleNamespace(returncode=1,stdout='',stderr=json.dumps({'error':{'server_error_code':'CONFLICT_ERROR'}}))):
            with self.assertRaisesRegex(BridgeError,'CONFLICT_ERROR'): cli.call([])
    def test_string_false_business_failure(self):
        cli=DWS(self.root,CFG)
        for response in ({'success':'false'}, {'ok':True,'outcome':'completed','data':{'success':'false'}}):
            with patch('dingtalk_bridge.core.run_dws',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(response),stderr='')):
                with self.assertRaises(BridgeError):cli.call([])

if __name__=='__main__': unittest.main()

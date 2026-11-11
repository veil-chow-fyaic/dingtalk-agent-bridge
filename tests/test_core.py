import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from dingtalk_bridge.core import Bridge, BridgeError, DWS

CFG = {'profile': 'corp:user', 'group': 'g', 'name': 'test', 'selfSenderId': 'self', 'binary': 'dws'}

class Fake:
    def __init__(self):
        self.sent = 0
        self.fail = False
        self.complete = True
        self.messages = [{'messageId': 'm1', 'conversationId': 'g', 'senderId': 'self', 'text': 'same'},
                         {'messageId': 'm2', 'conversationId': 'g', 'senderId': 'other', 'text': 'same'}]
    def call(self, args):
        if '+messages-send' in args:
            self.sent += 1
            if self.fail: raise BridgeError('timeout')
            return {'sendReceipt': {'openTaskId': 'task'}}
        if '+messages-query-send-status' in args:
            return {'result': {'sendStatus': 'SUCCESS'}, 'messageRef': {'openConversationId': 'g', 'openMessageId': 'sent'}}
        if '+chat-messages' in args:
            return {'messages': self.messages, 'count': len(self.messages), 'complete': self.complete}
        raise AssertionError(args)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fake = Fake()
        self.b = Bridge(self.root, CFG, self.fake)
    def tearDown(self):
        self.b.close()
        self.tmp.cleanup()
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
        (self.root/"fixtures/image.png").write_bytes(b"fixture")
        self.assertEqual(self.b.send("img", image="fixtures/image.png")["state"], "confirmed")
        with self.assertRaises(ValueError): self.b.send("img", file="fixtures/image.png")
        self.assertEqual(self.fake.sent, 1)
    def test_unobserved_attachment_rejected(self):
        with self.assertRaises(ValueError): self.b.download('unknown')
    def test_single_owner(self):
        with self.assertRaises(BridgeError): Bridge(self.root, CFG, self.fake)
    def test_cli_envelope_and_stderr_error(self):
        cli=DWS(self.root,CFG)
        with patch('subprocess.run', return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'ok':True,'outcome':'pending','data':{'success':True,'result':{'openTaskId':'t'}}}),stderr='')):
            self.assertEqual(cli.call([])['result']['openTaskId'],'t')
        with patch('subprocess.run', return_value=SimpleNamespace(returncode=1,stdout='',stderr=json.dumps({'error':{'server_error_code':'CONFLICT_ERROR'}}))):
            with self.assertRaisesRegex(BridgeError,'CONFLICT_ERROR'): cli.call([])
    def test_string_false_business_failure(self):
        cli=DWS(self.root,CFG)
        for response in ({'success':'false'}, {'ok':True,'outcome':'completed','data':{'success':'false'}}):
            with patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(response),stderr='')):
                with self.assertRaises(BridgeError):cli.call([])

if __name__=='__main__': unittest.main()

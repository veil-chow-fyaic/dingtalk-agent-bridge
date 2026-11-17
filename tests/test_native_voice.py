"""Pinned DWS voice projection and original-byte delivery, without live accounts.

The marker is documented in v1.0.67 connect_chatrecord.go and its fixture.
The bytes below are opaque synthetic test data, not a playable voice recording.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.consumer import Inbox
from dingtalk_bridge.core import Bridge
from dingtalk_bridge.message_model import media_parts, normalize
from test_agent_gateway import FakeAPI, FakeRuntime, SETTINGS
from test_routing_consumer import CFG, event, ref


VOICE_BYTES = b'synthetic opaque native voice original'
VOICE_TEXT = 'a spoken sentence\n[语音消息](mediaId=voice-1)'


def voice_event(seq=1, text=VOICE_TEXT, sender='other'):
    return event(seq, text=text, sender=sender, refs=[ref('mediaId', 'voice-1')])


class VoiceDWS:
    """Only the existing history and mget/download contracts may be invoked."""
    def __init__(self, root, fault=None):
        self.root, self.fault = root, fault
        self.calls = []

    def call(self, args):
        self.calls.append(list(args))
        if args[:2] == ['chat', '+chat-messages']:
            return {'complete': True, 'messages': [voice_event()['raw'], event(2)['raw']]}
        if args[:2] != ['chat', '+messages-mget']:
            raise AssertionError(args)
        if args[2:5] != ['--msg-ids', 'm1', '--download-resources']:
            raise AssertionError(args)
        path = self.root / args[args.index('--output-dir') + 1] / 'original.amr'
        path.parent.mkdir(parents=True)
        path.write_bytes(VOICE_BYTES)
        message = {'messageId': 'm1', 'conversationId': 'g'}
        entry = {'resourceType': 'mediaId', 'resourceId': 'voice-1', 'messageId': 'm1',
                 'localPath': str(path.relative_to(self.root)), 'sizeBytes': len(VOICE_BYTES)}
        if self.fault == 'foreign_conversation':message['conversationId'] = 'elsewhere'
        if self.fault == 'foreign_message':message['messageId'] = 'elsewhere'
        if self.fault == 'missing_original':entry['resourceId'] = 'different-resource'
        if self.fault == 'wrong_size':entry['sizeBytes'] += 1
        return {'messages': [message], 'resourceDownloads': {'ok': True, 'downloads': [entry]}}


class NativeVoiceTests(unittest.TestCase):
    def test_transcription_and_mixed_media_keep_order_and_exact_resource(self):
        text = VOICE_TEXT + '\na picture [图片消息](mediaId=picture-1) then [语音消息](mediaId=voice-2)'
        item = event(text=text, refs=[ref('mediaId', rid) for rid in ('voice-2', 'picture-1', 'voice-1')])
        before = copy.deepcopy(item)
        model = normalize(item, CFG)
        self.assertEqual(model['issues'], [])
        self.assertEqual([p['type'] for p in model['parts']], ['text', 'audio', 'text', 'image', 'text', 'audio'])
        self.assertEqual([p['resource']['resourceId'] for p in media_parts(model)], ['voice-1', 'picture-1', 'voice-2'])
        self.assertEqual(model['parts'][0]['text'], 'a spoken sentence\n')
        self.assertEqual(item, before)
        self.assertNotIn('path', model['parts'][1])

    def test_missing_and_malformed_voice_markers_cannot_become_ready_text(self):
        cases = [
            ('[语音消息](mediaId=unowned)', [], 'text_resource_missing_from_refs'),
            (VOICE_TEXT + ' [语音消息](mediaId=', [ref('mediaId', 'voice-1')], 'unparsed_media_marker'),
            ('[语音消息](mediaId=two words)', [], 'unparsed_media_marker'),
            ('[语音消息](mediaId=)', [], 'unparsed_media_marker'),
        ]
        for text, refs, issue in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temp:
                inbox = Inbox(Path(temp), CFG)
                bad = event(text=text, refs=refs)
                try:
                    inbox.ingest({'events': [bad, event(2)], 'next_cursor': 2})
                    row = inbox.db.execute('SELECT model,raw FROM inbox WHERE seq=1').fetchone()
                    self.assertIn(issue, json.loads(row['model'])['issues'])
                    self.assertEqual(json.loads(row['raw']), bad)
                    self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                    self.assertEqual(inbox.cursor, 2)
                finally:inbox.close()
        text = '普通语音说明 [括号] (mediaId=not-a-voice-message)'
        model = normalize(event(text=text), CFG)
        self.assertEqual(model['issues'], [])
        self.assertEqual(model['parts'], [{'type': 'text', 'text': text}])

    def test_quoted_voice_stays_on_source_and_does_not_change_sender_scope(self):
        quote = {**voice_event()['raw'], 'messageId': 'quoted', 'senderId': 'self'}
        model = normalize(event(text='reply', refs=quote['resourceRefs'], quote=quote), CFG)
        self.assertEqual(model['issues'], [])
        self.assertEqual(model['parts'], [{'type': 'text', 'text': 'reply'}])
        self.assertEqual(len(list(media_parts(model))), 1)
        self.assertEqual(model['quote']['parts'][1]['type'], 'audio')
        self.assertEqual((model['senderId'], model['fromSelf']), ('other', False))
        self.assertEqual((model['quote']['id'], model['quote']['senderId']), ('quoted', 'self'))
        quote['conversationId'] = 'other-conversation'
        with self.assertRaisesRegex(ValueError, 'cross_conversation_message'):
            normalize(event(quote=quote), CFG)
        item = voice_event();item['account_id'] = 'other-account'
        with self.assertRaisesRegex(ValueError, 'unexpected_account'):normalize(item, CFG)

    def test_history_to_original_consumer_bytes_survives_restart_and_uses_cache(self):
        for kind in ('group', 'direct'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                config = {**CFG, 'conversationType': kind, 'peerOpenDingTalkId': 'synthetic-peer'}
                dws = VoiceDWS(root);bridge = Bridge(root, config, dws)
                inbox = Inbox(root, config)
                try:
                    self.assertEqual(bridge.sync()['inserted'], 2)
                    inbox.ingest({'events': bridge.events(), 'next_cursor': 2})
                    self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                    self.assertEqual(inbox.hydrate(bridge.download), {'completed': 1, 'failed': 0})
                    ready = inbox.ready()
                    self.assertEqual([r['seq'] for r in ready], [1, 2])
                    audio = ready[0]['message']['parts'][1]
                    self.assertEqual(audio['type'], 'audio')
                    self.assertEqual(Path(audio['path']).read_bytes(), VOICE_BYTES)
                    self.assertEqual(audio['sha256'], hashlib.sha256(VOICE_BYTES).hexdigest())
                    self.assertEqual(audio['sizeBytes'], len(VOICE_BYTES))
                    self.assertEqual(audio['resource'], ref('mediaId', 'voice-1'))
                    self.assertEqual(ready[0]['message']['conversationType'], kind)
                    inbox.close();bridge.close()
                    bridge = Bridge(root, config, dws);inbox = Inbox(root, config)
                    self.assertEqual(inbox.cursor, 2)
                    self.assertEqual([r['seq'] for r in inbox.ready()], [1, 2])
                    self.assertEqual(inbox.hydrate(bridge.download), {'completed': 0, 'failed': 0})
                    self.assertTrue(bridge.download('m1')['ok'])
                    self.assertEqual(sum(c[:2] == ['chat', '+messages-mget'] for c in dws.calls), 1)
                finally:
                    inbox.close();bridge.close()

    def test_foreign_or_incomplete_original_isolated_until_explicit_retry(self):
        for fault in ('foreign_conversation', 'foreign_message', 'missing_original', 'wrong_size'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve();dws = VoiceDWS(root, fault)
                bridge = Bridge(root, CFG, dws);inbox = Inbox(root, CFG)
                try:
                    bridge.sync();inbox.ingest({'events': bridge.events(), 'next_cursor': 2})
                    self.assertEqual(inbox.hydrate(bridge.download), {'completed': 0, 'failed': 1})
                    self.assertEqual(inbox.db.execute('SELECT state FROM inbox WHERE seq=1').fetchone()[0], 'media_failed')
                    self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                    self.assertEqual(inbox.cursor, 2)
                    inbox.close();inbox = Inbox(root, CFG)
                    self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                    self.assertEqual(sum(c[:2] == ['chat', '+messages-mget'] for c in dws.calls), 1)
                    dws.fault = None
                    self.assertEqual(inbox.hydrate(bridge.download), {'completed': 1, 'failed': 0})
                    self.assertEqual([r['seq'] for r in inbox.ready()], [1, 2])
                finally:
                    inbox.close();bridge.close()

    def test_native_voice_does_not_authorize_group_task_or_echo(self):
        with tempfile.TemporaryDirectory() as temp:
            api, runtime = FakeAPI(), FakeRuntime()
            api.events = [voice_event(1), voice_event(2, '/agent [语音消息](mediaId=voice-1)', 'stranger'),
                          voice_event(3, '[Agent] [语音消息](mediaId=voice-1)', 'self')]
            gateway = Gateway(Path(temp), CFG, None, SETTINGS, api, runtime)
            try:
                gateway.intake()
                self.assertEqual(gateway.inbox.cursor, 3)
                self.assertEqual(gateway.summary()['jobs'], {})
                self.assertEqual(runtime.calls, 0)
                self.assertEqual(api.sends, {})
                self.assertIsNone(gateway.media_slot)
            finally:gateway.close()


if __name__ == '__main__':unittest.main()

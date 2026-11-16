"""Incomplete projections and unreadable cached originals cannot block later input."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.consumer import Inbox
from dingtalk_bridge.message_model import normalize
from test_agent_gateway import FakeAPI, FakeRuntime, SETTINGS
from test_routing_consumer import CFG, event, ref


def image_ledger(root, folder='initial'):
    path = root / 'local/runtime/downloads' / folder / 'image.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b'synthetic original image';path.write_bytes(data)
    return path, {'ok': True, 'downloads': [{
        'resourceType': 'mediaId', 'resourceId': 'ok',
        'localPath': str(path.relative_to(root)),
        'sha256': hashlib.sha256(data).hexdigest(), 'sizeBytes': len(data)}]}


def mixed_message(seq=1, text=None, quoted=False):
    text = text or 'compare [图片消息](mediaId=ok) and [图片消息](mediaId='
    refs = [ref('mediaId', 'ok')]
    if quoted:
        return event(seq, text='/agent compare quoted images', refs=refs,
                     quote={'conversationId': 'g', 'messageId': 'quoted',
                            'text': text, 'resourceRefs': refs})
    return event(seq, text=text, refs=refs)


class MessageReadinessTests(unittest.TestCase):
    def test_each_unparsed_image_marker_blocks_mixed_projection_and_preserves_raw(self):
        malformed = [
            '[图片消息](mediaId=ok) [图片消息](mediaId=',
            '[图片消息](mediaId=) [图片消息](mediaId=ok)',
            '[图片消息](mediaId=ok) [图片消息](mediaId=two words)',
        ]
        for text in malformed:
            for quoted in (False, True):
                with self.subTest(text=text, quoted=quoted), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp).resolve();inbox = Inbox(root, CFG)
                    bad = mixed_message(text=text, quoted=quoted)
                    inbox.ingest({'events': [bad, event(2)], 'next_cursor': 2})
                    _, ledger = image_ledger(root)
                    inbox.hydrate(lambda _: ledger)
                    try:
                        model = json.loads(inbox.db.execute('SELECT model FROM inbox WHERE seq=1').fetchone()[0])
                        node = model['quote'] if quoted else model
                        self.assertIn('unparsed_media_marker', node['issues'])
                        self.assertEqual(sum(p['type'] == 'image' for p in node['parts']), 1)
                        self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                        self.assertEqual(json.loads(inbox.db.execute('SELECT raw FROM inbox WHERE seq=1').fetchone()[0]), bad)
                        inbox.close();inbox = Inbox(root, CFG)
                        self.assertEqual(inbox.cursor, 2)
                        self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                    finally:
                        inbox.close()

    def test_complete_order_and_ordinary_brackets_remain_supported(self):
        model = normalize(event(text='[one] [图片消息](mediaId=a)中间[图片消息](mediaId=b)[two]',
                                refs=[ref('mediaId', 'a'), ref('mediaId', 'b')]), CFG)
        self.assertEqual(model['issues'], [])
        self.assertEqual([p['type'] for p in model['parts']], ['text', 'image', 'text', 'image', 'text'])
        self.assertEqual([p['resource']['resourceId'] for p in model['parts'] if p['type'] == 'image'], ['a', 'b'])
        literal = normalize(event(text='[普通文字] (mediaId=x) ![image](example.png)'), CFG)
        self.assertEqual(literal['issues'], [])
        self.assertEqual(literal['parts'], [{'type': 'text', 'text': '[普通文字] (mediaId=x) ![image](example.png)'}])

    def test_gateway_blocks_incomplete_projection_once_and_continues_valid_task(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);api, runtime = FakeAPI(), FakeRuntime()
            api.events = [mixed_message(text='/agent compare [图片消息](mediaId=ok) [图片消息](mediaId='),
                          event(2, text='/agent valid task')]
            gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
            try:
                gateway.intake()
                self.assertEqual(gateway.summary()['jobs'], {'blocked': 1, 'queued': 1})
                self.assertIsNone(gateway.media_slot)
                self.assertTrue(gateway.execute_one());gateway.flush()
                self.assertEqual(runtime.calls, 1)
                self.assertFalse(gateway.execute_one())
                sends = copy.deepcopy(api.sends)
                gateway.close();gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
                gateway.intake();gateway.flush()
                self.assertEqual(gateway.inbox.cursor, 2)
                self.assertFalse(gateway.execute_one());self.assertEqual(runtime.calls, 1)
                self.assertEqual(api.sends, sends)
            finally:
                gateway.close()

    def test_unreadable_cached_original_isolated_persisted_and_explicitly_rehydrated(self):
        for fault in (PermissionError, FileNotFoundError, OSError):
            with self.subTest(fault=fault.__name__), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve();inbox = Inbox(root, CFG)
                inbox.ingest({'events': [event(1, text='[图片消息](mediaId=ok)', refs=[ref('mediaId', 'ok')]),
                                         event(2)], 'next_cursor': 2})
                path, ledger = image_ledger(root);calls = []
                def download(mid):
                    calls.append(mid);return ledger
                inbox.hydrate(download)
                original = Path.read_bytes
                def unavailable(selected):
                    if selected == path:raise fault('synthetic cache I/O failure')
                    return original(selected)
                try:
                    with patch.object(Path, 'read_bytes', unavailable):
                        self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                        self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                        self.assertEqual(inbox.summary()['readyForRuntime'], 1)
                    row = inbox.db.execute('SELECT state,error,attempts,raw FROM inbox WHERE seq=1').fetchone()
                    self.assertEqual((row['state'], row['error'], row['attempts']), ('media_failed', 'cache_unavailable', 1))
                    self.assertEqual(json.loads(row['raw'])['message_id'], 'm1')
                    inbox.close();inbox = Inbox(root, CFG)
                    self.assertEqual(inbox.cursor, 2)
                    self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                    self.assertEqual(calls, ['m1'])
                    # A caller explicitly supplies the repaired official-download result.
                    _, ledger = image_ledger(root, 'repaired')
                    self.assertEqual(inbox.hydrate(download), {'completed': 1, 'failed': 0})
                    self.assertEqual([r['seq'] for r in inbox.ready()], [1, 2])
                    self.assertEqual(calls, ['m1', 'm1'])
                finally:
                    inbox.close()

    def test_real_symlink_loop_is_isolated_without_swallowing_other_runtime_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve();inbox = Inbox(root, CFG)
            inbox.ingest({'events': [event(1, text='[图片消息](mediaId=ok)', refs=[ref('mediaId', 'ok')]),
                                     event(2)], 'next_cursor': 2})
            path, ledger = image_ledger(root);calls = []
            def download(mid):
                calls.append(mid);return ledger
            inbox.hydrate(download)
            original_resolve = Path.resolve
            def programming_error(selected, *args, **kwargs):
                if selected == path:raise RuntimeError('synthetic programming error')
                return original_resolve(selected, *args, **kwargs)
            try:
                with patch.object(Path, 'resolve', programming_error):
                    with self.assertRaisesRegex(RuntimeError, 'programming error'):inbox.ready()
                # Real filesystem loop: Python 3.11 raises RuntimeError from
                # OSError(ELOOP), while newer pathlib surfaces OSError itself.
                path.unlink();path.symlink_to(path.name)
                self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                row = inbox.db.execute('SELECT state,error,attempts FROM inbox WHERE seq=1').fetchone()
                self.assertEqual(tuple(row), ('media_failed', 'cache_unavailable', 1))
                self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                self.assertEqual(inbox.cursor, 2);self.assertEqual(calls, ['m1'])
                inbox.close();inbox = Inbox(root, CFG)
                self.assertEqual([r['seq'] for r in inbox.ready()], [2])
                self.assertEqual(inbox.cursor, 2);self.assertEqual(calls, ['m1'])
                _, ledger = image_ledger(root, 'repaired')
                self.assertEqual(inbox.hydrate(download), {'completed': 1, 'failed': 0})
                self.assertEqual([r['seq'] for r in inbox.ready()], [1, 2])
                self.assertEqual(calls, ['m1', 'm1'])
            finally:
                inbox.close()

    def test_database_failure_is_not_swallowed_as_cache_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            inbox = Inbox(Path(temp), CFG)
            try:
                inbox.db.close()
                with self.assertRaises(sqlite3.ProgrammingError):inbox.ready()
            finally:
                inbox.close()

    def test_gateway_preserves_existing_file_failure_and_no_replay_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve();api, runtime = FakeAPI(), FakeRuntime()
            bad = mixed_message(quoted=True, text='[图片消息](mediaId=ok)')
            api.events = [bad, event(2, text='/agent valid task')]
            gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
            path, ledger = image_ledger(root)
            gateway.inbox.ingest({'events': api.events, 'next_cursor': 2})
            gateway.inbox.hydrate(lambda _: ledger)
            original = Path.read_bytes
            def unavailable(selected):
                if selected == path:raise PermissionError('synthetic cache I/O failure')
                return original(selected)
            try:
                gateway.intake()
                with patch.object(Path, 'read_bytes', unavailable):
                    self.assertTrue(gateway.execute_one())
                self.assertEqual(runtime.calls, 0)
                self.assertEqual(gateway.db.execute('SELECT state FROM jobs WHERE seq=1').fetchone()[0], 'failed')
                self.assertTrue(gateway.execute_one());gateway.flush()
                self.assertEqual(runtime.calls, 1)
                gateway.close();gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
                gateway.intake();gateway.flush()
                self.assertFalse(gateway.execute_one());self.assertEqual(runtime.calls, 1)
            finally:
                gateway.close()


if __name__ == '__main__':unittest.main()

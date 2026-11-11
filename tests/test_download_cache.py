"""The generic attachment API must not bless an incomplete cached manifest."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from dingtalk_bridge.core import Bridge, BridgeError
from test_routing_consumer import CFG, event, ref


class DownloadCacheTests(unittest.TestCase):
    def test_corrupt_manifest_is_refused_until_explicit_repair_without_overwriting_old_files(self):
        changes = [
            ('missing_resource', lambda x: x.update(downloads=[])),
            ('wrong_resource', lambda x: x['downloads'][0].update(resourceId='wrong')),
            ('wrong_size', lambda x: x['downloads'][0].update(sizeBytes=999)),
            ('incomplete', lambda x: x.update(ok=False)),
            ('partial', lambda x: x.update(partial=True)),
            ('failed_resource', lambda x: x.update(failedCount=1)),
        ]
        for label, corrupt in changes:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                calls = []

                class DWS:
                    def call(self, args):
                        if '+chat-messages' in args:
                            return {'complete': True, 'messages': [event(text='[文件] fixture.txt fileId: f', refs=[ref('fileId', 'f')])['raw']]}
                        assert '+messages-mget' in args
                        folder = args[args.index('--output-dir') + 1]
                        calls.append(folder)
                        path = root / folder / 'fixture.txt'
                        path.parent.mkdir(parents=True)
                        path.write_bytes(b'original')
                        return {'messages': [{'messageId': 'm1', 'conversationId': 'g'}],
                                'resourceDownloads': {'ok': True, 'downloads': [{'resourceType': 'fileId', 'resourceId': 'f',
                                    'localPath': str(path.relative_to(root)), 'sizeBytes': 8}]}}

                bridge = Bridge(root, CFG, DWS())
                try:
                    bridge.sync()
                    original = bridge.download('m1')
                    path = root / original['downloads'][0]['localPath']
                    manifest = path.parent.parent / 'manifest.json'
                    broken = copy.deepcopy(original)
                    corrupt(broken)
                    manifest.write_text(json.dumps(broken))
                    bridge.close()
                    bridge = Bridge(root, CFG, DWS())
                    with self.assertRaisesRegex(BridgeError, 'Cached attachment'):
                        bridge.download('m1')
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(json.loads(manifest.read_text()), broken)
                    self.assertEqual(path.read_bytes(), b'original')
                    repaired = bridge.download('m1', repair=True)
                    self.assertTrue(repaired['ok'])
                    self.assertEqual(len(calls), 2)
                    self.assertNotEqual(calls[0], calls[1])
                    self.assertEqual(path.read_bytes(), b'original')
                    self.assertEqual(bridge.download('m1'), repaired)
                    self.assertEqual(len(calls), 2)
                finally:
                    bridge.close()


if __name__ == '__main__':
    unittest.main()

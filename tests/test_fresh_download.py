"""Fresh and cached attachment responses share a fail-closed integrity contract."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from dingtalk_bridge.core import Bridge, BridgeError
from test_routing_consumer import CFG, event, ref


class DownloadFixture:
    def __init__(self, root, mutate):
        self.root = root;self.mutate = mutate;self.paths = [];self.responses = []

    def call(self, args):
        if '+chat-messages' in args:
            return {'complete': True, 'messages': [event(text='[文件] fixture.txt fileId: f', refs=[ref('fileId', 'f')])['raw']]}
        assert '+messages-mget' in args
        path = self.root / args[args.index('--output-dir') + 1] / 'fixture.txt'
        path.parent.mkdir(parents=True);path.write_bytes(b'original');self.paths.append(path)
        data = {'messages': [{'messageId': 'm1', 'conversationId': 'g'}],
                'resourceDownloads': {'ok': True, 'downloads': [{'resourceType': 'fileId', 'resourceId': 'f',
                    'localPath': str(path.relative_to(self.root)), 'sizeBytes': 8}]}}
        if len(self.paths) == 1:
            replacement = self.mutate(data)
            if replacement is not None:data = replacement
        self.responses.append(copy.deepcopy(data))
        return data


class FreshDownloadTests(unittest.TestCase):
    def test_invalid_first_response_cannot_create_success_cache_and_retry_preserves_old_attempt(self):
        def entry(data):return data['resourceDownloads']['downloads'][0]
        mutations = [
            ('wrong_size', lambda d: entry(d).update(sizeBytes=9)),
            ('missing_size', lambda d: entry(d).pop('sizeBytes') and None),
            ('boolean_size', lambda d: entry(d).update(sizeBytes=True)),
            ('string_size', lambda d: entry(d).update(sizeBytes='8')),
            ('duplicate_resource', lambda d: d['resourceDownloads']['downloads'].append(copy.deepcopy(entry(d)))),
            ('missing_resource_id', lambda d: entry(d).pop('resourceId') and None),
            ('unknown_resource_type', lambda d: entry(d).update(resourceType='unknown')),
            ('missing_path', lambda d: entry(d).pop('localPath') and None),
            ('integer_path', lambda d: entry(d).update(localPath=7)),
            ('nul_path', lambda d: entry(d).update(localPath='bad\0path')),
            ('outside_path', lambda d: entry(d).update(localPath='../outside.txt')),
            ('bad_downloads_shape', lambda d: d['resourceDownloads'].update(downloads={})),
            ('bad_entry_shape', lambda d: d['resourceDownloads'].update(downloads=[None])),
            ('bad_ledger_shape', lambda d: d.update(resourceDownloads=[])),
            ('missing_ledger', lambda d: d.pop('resourceDownloads') and None),
            ('bad_messages_shape', lambda d: d.update(messages=None)),
            ('bad_message_shape', lambda d: d.update(messages=[None])),
            ('bad_top_shape', lambda d: []),
            ('bad_ok_type', lambda d: d['resourceDownloads'].update(ok='true')),
            ('bad_partial_type', lambda d: d['resourceDownloads'].update(partial='false')),
            ('negative_failed_count', lambda d: d['resourceDownloads'].update(failedCount=-1)),
            ('boolean_failed_count', lambda d: d['resourceDownloads'].update(failedCount=False)),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp);dws = DownloadFixture(root, mutate);bridge = Bridge(root, CFG, dws)
                try:
                    bridge.sync()
                    with self.assertRaises(BridgeError):bridge.download('m1')
                    self.assertEqual(len(dws.paths), 1)
                    manifest = dws.paths[0].parent.parent / 'manifest.json'
                    self.assertFalse(manifest.exists())
                    bridge.close();bridge = Bridge(root, CFG, dws)
                    result = bridge.download('m1')
                    self.assertTrue(result['ok']);self.assertEqual(len(dws.paths), 2)
                    self.assertNotEqual(dws.paths[0], dws.paths[1])
                    self.assertTrue(all(p.read_bytes() == b'original' for p in dws.paths))
                    self.assertEqual(result['downloads'][0]['sha256'], hashlib.sha256(b'original').hexdigest())
                    self.assertEqual(bridge.download('m1'), result);self.assertEqual(len(dws.paths), 2)
                finally:bridge.close()

    def test_partial_or_missing_resources_are_not_success_and_recover_without_repair(self):
        mutations = [
            lambda d: d['resourceDownloads'].update(partial=True),
            lambda d: d['resourceDownloads'].update(failedCount=1),
            lambda d: d['resourceDownloads'].update(downloads=[]),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as temp:
                root = Path(temp);dws = DownloadFixture(root, mutate);bridge = Bridge(root, CFG, dws)
                try:
                    bridge.sync();result = bridge.download('m1')
                    self.assertIs(result['ok'], False)
                    self.assertFalse((dws.paths[0].parent.parent / 'manifest.json').exists())
                    self.assertTrue(bridge.download('m1')['ok'])
                    self.assertEqual(len(dws.paths), 2)
                finally:bridge.close()

    def test_malformed_cached_entry_is_a_bridge_error_without_download_or_rewrite(self):
        mutations = [
            lambda d: d['downloads'][0].pop('localPath'),
            lambda d: d['downloads'][0].update(localPath=7),
            lambda d: d['downloads'].append(copy.deepcopy(d['downloads'][0])),
            lambda d: d['downloads'][0].update(resourceType='unknown'),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as temp:
                root = Path(temp);dws = DownloadFixture(root, lambda _: None);bridge = Bridge(root, CFG, dws)
                try:
                    bridge.sync();result = bridge.download('m1');mutate(result)
                    manifest = dws.paths[0].parent.parent / 'manifest.json'
                    manifest.write_text(json.dumps(result));old = manifest.read_bytes()
                    with self.assertRaisesRegex(BridgeError, 'Cached attachment'):bridge.download('m1')
                    self.assertEqual(manifest.read_bytes(), old);self.assertEqual(len(dws.paths), 1)
                finally:bridge.close()

    def test_failed_explicit_repair_retains_previous_good_cache_and_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);dws = DownloadFixture(root, lambda _: None);bridge = Bridge(root, CFG, dws)
            try:
                bridge.sync();original = bridge.download('m1')
                manifest = dws.paths[0].parent.parent / 'manifest.json';saved = manifest.read_bytes()
                call = dws.call
                def broken(args):
                    result = call(args)
                    if '+messages-mget' in args:result['resourceDownloads']['downloads'][0]['sizeBytes'] = 999
                    return result
                dws.call = broken
                with self.assertRaises(BridgeError):bridge.download('m1', repair=True)
                self.assertEqual(len(dws.paths), 2);self.assertEqual(manifest.read_bytes(), saved)
                self.assertEqual(bridge.download('m1'), original);self.assertEqual(len(dws.paths), 2)
                dws.call = call;repaired = bridge.download('m1', repair=True)
                self.assertEqual(len(dws.paths), 3)
                self.assertNotEqual(repaired['downloads'][0]['localPath'], original['downloads'][0]['localPath'])
                self.assertTrue(all(p.read_bytes() == b'original' for p in dws.paths))
            finally:bridge.close()


if __name__ == '__main__':unittest.main()

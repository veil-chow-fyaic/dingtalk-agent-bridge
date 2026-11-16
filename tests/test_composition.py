"""Ordered originals and one durable delivery, independent of any Agent runtime."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from dingtalk_bridge.core import Bridge, ArtifactIntegrityError, DWSRequestRejected
from dingtalk_bridge.composition import IMAGE_LIMIT, prepare
from test_core import CFG, Fake


def png(color):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + bytes(color))) + chunk(b'IEND', b''))


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root / 'fixtures').mkdir()
        self.originals = [png((255, 0, 0)), png((0, 0, 255))]
        self.paths = [self.root / 'fixtures' / name for name in ['a ](extra).png', 'b.png']]
        for path, content in zip(self.paths, self.originals): path.write_bytes(content)
        self.value = {'text': 'literal **title** ![extra](file:///private) <tag> \\ end', 'images': [
            {'path': str(path.relative_to(self.root)), 'sha256': hashlib.sha256(content).hexdigest()}
            for path, content in zip(self.paths, self.originals)]}
        self.provider = Fake(); self.bridge = Bridge(self.root, CFG, self.provider)
        self.addCleanup(lambda: self.bridge.close())

    def saved(self):
        return json.loads(self.bridge.db.execute('SELECT payload FROM deliveries WHERE key="one"').fetchone()[0])

    def restart(self):
        self.bridge.close(); self.bridge = Bridge(self.root, CFG, self.provider)

    def test_one_send_preserves_order_bytes_and_literal_text(self):
        self.assertEqual(self.bridge.send('one', composition=self.value)['state'], 'confirmed')
        payload = self.saved(); args = self.provider.send_args[0]
        self.assertEqual(args[args.index('--group') + 1], 'g')
        self.assertNotIn('--file', args); self.assertNotIn('--text', args)
        body = args[args.index('--markdown') + 1]
        self.assertIn(r'\!\[extra\]\(file\:\/\/\/private\)', body)
        self.assertIn(r'\<tag\>', body)
        self.assertLess(body.index(payload['images'][0]['staged']), body.index(payload['images'][1]['staged']))
        for item, expected in zip(payload['images'], self.originals):
            self.assertEqual((self.root / item['staged']).read_bytes(), expected)
        self.assertEqual(self.provider.sent, 1); self.assertEqual(self.provider.uploaded, 0)

    def test_direct_target_uses_configured_peer_without_runtime(self):
        self.bridge.close()
        self.bridge = Bridge(self.root, {**CFG, 'conversationType': 'direct', 'peerOpenDingTalkId': 'fixture-peer'}, self.provider)
        self.bridge.send('one', composition=self.value)
        args = self.provider.send_args[0]
        self.assertEqual(args[args.index('--open-dingtalk-id') + 1], 'fixture-peer')
        self.assertNotIn('--group', args)

    def test_any_changed_original_prevents_reservation_and_send(self):
        self.paths[1].write_bytes(png((1, 2, 3)))
        with self.assertRaises(ArtifactIntegrityError): self.bridge.send('one', composition=self.value)
        self.assertIsNone(self.bridge.delivery('one')); self.assertEqual(self.provider.sent, 0)
        self.assertFalse((self.bridge.local / 'staged').exists())

    def test_replay_after_restart_and_deleted_sources_never_reuploads(self):
        self.provider.fail = True
        first = self.bridge.send('one', composition=self.value)
        self.assertEqual(first['state'], 'outcome_unknown')
        self.restart()
        for path in self.paths: path.unlink()
        replay = self.bridge.send('one', composition=self.value)
        self.assertTrue(replay.pop('replayed')); self.assertEqual(replay, first)
        self.assertEqual(self.bridge.reconcile('one')['state'], 'outcome_unknown')
        self.assertEqual(self.provider.sent, 1)

    def test_changed_order_caption_or_digest_conflicts_with_original_key(self):
        self.bridge.send('one', composition=self.value)
        for change in ('order', 'text', 'digest'):
            value = copy.deepcopy(self.value)
            if change == 'order': value['images'].reverse()
            if change == 'text': value['text'] += 'changed'
            if change == 'digest': value['images'][1]['sha256'] = '0' * 64
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'another payload'):
                self.bridge.send('one', composition=value)
        self.assertEqual(self.provider.sent, 1)

    def test_parallel_same_key_makes_one_delivery(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.bridge.send('one', composition=self.value), range(8)))
        self.assertEqual(sum(bool(r.get('replayed')) for r in results), 7)
        self.assertEqual(self.provider.sent, 1)

    def test_crash_during_official_call_restarts_as_unknown_without_send(self):
        with patch.object(self.provider, 'call', side_effect=SystemExit('synthetic crash')):
            with self.assertRaises(SystemExit): self.bridge.send('one', composition=self.value)
        self.assertEqual(self.bridge.delivery('one')['state'], 'executing')
        self.restart()
        self.assertEqual(self.bridge.send('one', composition=self.value)['state'], 'outcome_unknown')
        self.assertEqual(self.provider.sent, 0)

    def test_status_failure_preserves_task_for_reconciliation(self):
        original = self.provider.call
        def call(args):
            if '+messages-query-send-status' in args: raise OSError('synthetic lost status')
            return original(args)
        with patch.object(self.provider, 'call', side_effect=call):
            result = self.bridge.send('one', composition=self.value)
        self.assertEqual(result['state'], 'outcome_unknown'); self.assertEqual(result['task_id'], 'task')
        self.assertEqual(self.bridge.reconcile('one')['state'], 'confirmed')
        self.assertEqual(self.provider.sent, 1)

    def test_explicit_rejection_is_persisted_and_never_retried(self):
        with patch.object(self.provider, 'call', side_effect=DWSRequestRejected({'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR'})) as call:
            self.assertEqual(self.bridge.send('one', composition=self.value)['state'], 'rejected')
            self.assertTrue(self.bridge.send('one', composition=self.value)['replayed'])
        self.assertEqual(call.call_count, 1)

    def test_duplicate_references_count_toward_nine_and_preserve_positions(self):
        value = {'images': [self.value['images'][0]] * 9}
        self.bridge.send('one', composition=value)
        self.assertEqual(len(self.saved()['images']), 9)
        self.assertEqual(self.provider.send_args[0][-1].count('![image '), 9)
        with self.assertRaises(ValueError): self.bridge.send('ten', composition={'images': value['images'] + value['images'][:1]})
        self.assertIsNone(self.bridge.delivery('ten')); self.assertEqual(self.provider.sent, 1)

    def test_invalid_schema_and_mutually_exclusive_modes_have_no_side_effect(self):
        for value in ([], {}, {'images': []}, {'images': 'x'}, {'images': [self.value['images'][0]], 'markdown': '![](x)'},
                      {'images': [{'path': 'fixtures/b.png'}]}, {'images': [{'path': 7, 'sha256': '0'*64}]},
                      {'images': [{'path': 'fixtures/b.png', 'sha256': 'A'*64}]}, {**self.value, 'text': 'x\0'}):
            with self.subTest(value=value), self.assertRaises(ValueError): self.bridge.send('one', composition=value)
        for other in ({'text': 'x'}, {'file': 'x'}, {'image': 'x'}, {'reply_to': 'm'}, {'expected_sha256': '0'*64}):
            with self.subTest(other=other), self.assertRaises(ValueError): self.bridge.send('one', composition=self.value, **other)
        self.assertIsNone(self.bridge.delivery('one')); self.assertEqual(self.provider.sent, 0)

    def test_path_and_media_boundaries_prevent_upload(self):
        outside = self.root / 'outside.png'; outside.write_bytes(self.originals[0])
        (self.root / 'fixtures/link.png').symlink_to(outside)
        for name in ('../outside.png', str(outside), 'outside.png', 'fixtures/link.png', 'fixtures/a.pdf', 'https://example.test/a.png'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.bridge.send('one', composition={'images': [{'path': name, 'sha256': '0'*64}]})
        for content in (b'not a png', b'\x89PNG\r\n\x1a\n' + b'0' * IMAGE_LIMIT):
            self.paths[0].write_bytes(content)
            with self.assertRaises(ValueError):
                self.bridge.send('one', composition={'images': [{'path': self.value['images'][0]['path'], 'sha256': hashlib.sha256(content).hexdigest()}]})
        self.assertEqual(self.provider.sent, 0); self.assertIsNone(self.bridge.delivery('one'))

    def test_generated_body_limit_includes_images_and_utf16_escaping(self):
        for text in ('🙂' * 2560, '*' * 2560, 'x' * 5120):
            with self.subTest(text=text[:8]), self.assertRaisesRegex(ValueError, '5120 UTF-16'):
                self.bridge.send('one', composition={**self.value, 'text': text})
        self.assertIsNone(self.bridge.delivery('one')); self.assertEqual(self.provider.sent, 0)

    def test_tampered_staging_and_symlink_are_not_overwritten(self):
        payload, _ = prepare(self.bridge.root, self.bridge.local, self.value)
        target = self.root / payload['images'][0]['staged']; target.parent.mkdir(parents=True)
        target.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'): self.bridge.send('one', composition=self.value)
        self.assertEqual(target.read_bytes(), b'tampered'); target.unlink()
        target.symlink_to(self.paths[0])
        with self.assertRaisesRegex(ValueError, 'symlink'): self.bridge.send('one', composition=self.value)
        self.assertEqual(self.provider.sent, 0); self.assertIsNone(self.bridge.delivery('one'))


if __name__ == '__main__': unittest.main()

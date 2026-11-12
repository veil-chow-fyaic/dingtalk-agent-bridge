"""Synthetic task -> persistent outbox -> bridge/provider integrity contract."""
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.core import Bridge, ArtifactIntegrityError
from test_agent_gateway import SETTINGS, FakeAPI, FakeRuntime
from test_core import Fake
from test_routing_consumer import CFG, event


class ArtifactDeliveryDigestTests(unittest.TestCase):
    def test_concurrent_receipt_wins_over_late_local_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'fixtures').mkdir()
            source = root / 'fixtures/result.txt'; source.write_bytes(b'changed')
            provider = Fake(); bridge = Bridge(root, CFG, provider)
            entered, release = threading.Event(), threading.Event(); read = Path.read_bytes
            digest = hashlib.sha256(b'original').hexdigest()
            def slow_read(path):
                data = read(path)
                if path == source.resolve() and threading.current_thread().name.startswith('slow-digest'):
                    entered.set()
                    if not release.wait(5): raise AssertionError('Slow read not released')
                return data
            try:
                with patch.object(Path,'read_bytes',slow_read), ThreadPoolExecutor(max_workers=1,thread_name_prefix='slow-digest') as pool:
                    slow = pool.submit(bridge.send, 'same', file='fixtures/result.txt', expected_sha256=digest)
                    try:
                        self.assertTrue(entered.wait(3)); source.write_bytes(b'original')
                        first = bridge.send('same', file='fixtures/result.txt', expected_sha256=digest)
                    finally: release.set()
                    late = slow.result(timeout=5)
                self.assertTrue(late.pop('replayed')); self.assertEqual(late, first)
                self.assertEqual(first['state'], 'confirmed'); self.assertEqual(provider.sent, 1)
            finally: bridge.close()

    def test_bridge_checks_exact_file_and_image_before_reservation_or_upload(self):
        for kind, name, original in [('file', 'a.txt', b'original'), ('image', 'a.png', b'\x89PNG\r\n\x1a\noriginal')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); (root / 'fixtures').mkdir()
                source = root / 'fixtures' / name; source.write_bytes(b'changed')
                provider = Fake(); bridge = Bridge(root, {**CFG, 'imageUploadBinary': 'image-fixture'}, provider)
                digest = hashlib.sha256(original).hexdigest()
                try:
                    with self.assertRaisesRegex(ArtifactIntegrityError, '^artifact_integrity_mismatch$'):
                        bridge.send('fixed', **{kind: 'fixtures/' + name}, expected_sha256=digest)
                    self.assertEqual(provider.sent, 0); self.assertEqual(provider.uploaded, 0)
                    self.assertIsNone(bridge.delivery('fixed'))
                    source.write_bytes(original)
                    receipt = bridge.send('fixed', **{kind: 'fixtures/' + name}, expected_sha256=digest)
                    self.assertEqual(receipt['state'], 'confirmed')
                    saved = json.loads(bridge.db.execute('SELECT payload FROM deliveries WHERE key="fixed"').fetchone()[0])
                    self.assertEqual(saved['sha256'], digest)
                    staged = root / saved['staged']
                    self.assertEqual(staged.read_bytes(), original)
                finally: bridge.close()

    def test_bound_replay_after_source_deletion_uses_original_unknown_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'fixtures').mkdir()
            source = root / 'fixtures/result.txt'; source.write_bytes(b'approved')
            digest = hashlib.sha256(b'approved').hexdigest()
            provider = Fake(); call = provider.call
            def lost_query(args):
                if '+messages-query-send-status' in args: raise OSError('response lost')
                return call(args)
            provider.call = lost_query
            bridge = Bridge(root, CFG, provider)
            try:
                # A receipt created before this additive field existed must match.
                first = bridge.send('same-key', file='fixtures/result.txt')
                self.assertEqual(first['state'], 'outcome_unknown')
                self.assertEqual(first['task_id'], 'task')
                source.unlink(); bridge.close(); bridge = Bridge(root, CFG, provider)
                replay = bridge.send('same-key', file='fixtures/result.txt', expected_sha256=digest)
                self.assertTrue(replay.pop('replayed')); self.assertEqual(replay, first)
                with self.assertRaisesRegex(ValueError, 'another payload'):
                    bridge.send('same-key', file='fixtures/result.txt', expected_sha256='0' * 64)
                provider.call = call
                self.assertEqual(bridge.reconcile('same-key')['state'], 'confirmed')
                self.assertEqual(provider.sent, 1)
            finally: bridge.close()

    def test_expected_digest_rejects_invalid_types_and_text_without_dws(self):
        with tempfile.TemporaryDirectory() as temp:
            provider = Fake(); bridge = Bridge(Path(temp), CFG, provider)
            try:
                for digest in ('', '0' * 63, 'G' * 64, 'A' * 64, 123, [], {}):
                    with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, 'expected_sha256'):
                        bridge.send('invalid', file='fixtures/file.txt', expected_sha256=digest)
                with self.assertRaisesRegex(ValueError, 'expected_sha256'):
                    bridge.send('text', text='hello', expected_sha256='0' * 64)
                self.assertEqual(provider.sent, 0); self.assertIsNone(bridge.delivery('invalid'))
            finally: bridge.close()

    def test_source_change_after_read_does_not_change_bytes_handed_to_dws(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'fixtures').mkdir()
            source = root / 'fixtures/result.txt'; source.write_bytes(b'approved')
            provider = Fake(); bridge = Bridge(root, CFG, provider)
            read = Path.read_bytes
            def mutate_after_read(path):
                data = read(path)
                if path == source.resolve(): source.write_bytes(b'later mutation')
                return data
            try:
                with patch.object(Path, 'read_bytes', mutate_after_read):
                    receipt = bridge.send('original', file='fixtures/result.txt',
                                          expected_sha256=hashlib.sha256(b'approved').hexdigest())
                self.assertEqual(receipt['state'], 'confirmed')
                args = provider.send_args[0]; staged = root / args[args.index('--file') + 1]
                self.assertEqual(staged.read_bytes(), b'approved')
                self.assertEqual(source.read_bytes(), b'later mutation')
            finally: bridge.close()

    def test_queued_file_mutation_is_not_delivered_and_task_is_not_reexecuted(self):
        self.queued_mutation()

    def test_legacy_queued_file_uses_saved_job_digest_not_current_bytes(self):
        self.queued_mutation(legacy=True)

    def queued_mutation(self, legacy=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbound, runtime, provider = FakeAPI(), FakeRuntime(), Fake()
            bridge = Bridge(root, CFG, provider)

            def api(path, data=None):
                if path == '/v1/send':
                    return bridge.send(data['idempotency_key'], **{
                        k: v for k, v in data.items() if k != 'idempotency_key'})
                if path == '/v1/reconcile':
                    return bridge.reconcile(data['idempotency_key'])
                return inbound(path, data)

            gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
            try:
                inbound.events = [event(text='/agent generate file')]
                gateway.intake(); self.assertTrue(gateway.execute_one())
                row = gateway.db.execute('SELECT * FROM outbox WHERE key LIKE "%-file-0"').fetchone()
                payload = json.loads(row['payload'])
                if legacy:
                    payload.pop('expected_sha256')
                    with gateway.db:
                        gateway.db.execute('UPDATE outbox SET payload=? WHERE key=?', (json.dumps(payload), row['key']))
                (root / payload['file']).write_bytes(b'changed after task completed')
                gateway.close()
                gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
                gateway.flush(); gateway.flush()
                delivery = gateway.db.execute('SELECT * FROM outbox WHERE key=?', (row['key'],)).fetchone()
                self.assertEqual(delivery['state'], 'failed')
                self.assertFalse(any('--file' in args for args in provider.send_args))
                self.assertEqual(runtime.calls, 1)
                self.assertFalse(gateway.execute_one())
                job = gateway.db.execute('SELECT * FROM jobs').fetchone()
                self.assertEqual(job['state'], 'completed')
                artifact = json.loads(job['result'])['artifacts'][0]
                self.assertEqual(artifact['sha256'], hashlib.sha256(b'task result').hexdigest())
                self.assertEqual(json.loads(delivery['payload'])['expected_sha256'], artifact['sha256'])
                self.assertIsNone(bridge.delivery(row['key']))
                self.assertEqual(gateway.db.execute(
                    'SELECT count(*) FROM outbox WHERE key LIKE "%-delivery-issue"').fetchone()[0], 1)
            finally:
                gateway.close(); bridge.close()

    def test_gateway_lost_success_reply_and_deleted_file_reconciles_same_key(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbound, runtime, provider = FakeAPI(), FakeRuntime(), Fake()
            bridge = Bridge(root, CFG, provider); lost = []
            def api(path, data=None):
                if path == '/v1/send':
                    result = bridge.send(data['idempotency_key'], **{
                        k: v for k, v in data.items() if k != 'idempotency_key'})
                    if 'file' in data and not lost:
                        lost.append(data['idempotency_key']); (root / data['file']).unlink()
                        raise OSError('lost HTTP success after provider confirmation')
                    return result
                if path == '/v1/reconcile': return bridge.reconcile(data['idempotency_key'])
                return inbound(path, data)
            gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
            try:
                inbound.events = [event(text='/agent generate file')]
                gateway.intake(); gateway.execute_one(); gateway.flush()
                self.assertEqual(gateway.db.execute('SELECT state FROM outbox WHERE key=?', (lost[0],)).fetchone()[0], 'pending')
                gateway.close(); gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
                gateway.flush()
                self.assertEqual(gateway.db.execute('SELECT state FROM outbox WHERE key=?', (lost[0],)).fetchone()[0], 'confirmed')
                self.assertEqual(sum('--file' in a for a in provider.send_args), 1)
                self.assertEqual(runtime.calls, 1)
                self.assertEqual(gateway.db.execute('SELECT count(*) FROM outbox WHERE key LIKE "%-delivery-issue"').fetchone()[0], 0)
            finally: gateway.close(); bridge.close()

    def test_gateway_native_image_carries_original_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); api = FakeAPI(); runtime = FakeRuntime()
            image_bytes = b'\x89PNG\r\n\x1a\nsynthetic image bytes'
            def run(prompt, workspace, *args):
                (workspace / 'exports/result.png').write_bytes(image_bytes)
                return {'text': 'image result', 'files': ['exports/result.png']}
            runtime.run = run
            gateway = Gateway(root, {**CFG, 'imageUploadBinary': 'image-fixture'}, None, SETTINGS, api, runtime)
            try:
                api.events = [event(text='/agent generate image')]
                gateway.intake(); gateway.execute_one(); gateway.flush()
                sent = next(p for p in api.sends.values() if 'image' in p)
                self.assertEqual(sent['expected_sha256'], hashlib.sha256(image_bytes).hexdigest())
            finally: gateway.close()

    def test_legacy_without_original_proof_remains_unresolved_without_send(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); api = FakeAPI(); gateway = Gateway(root, CFG, None, SETTINGS, api, FakeRuntime())
            try:
                with gateway.db:
                    gateway.emit('historical', 'file-0', {'file': 'local/outbox/old.txt'})
                gateway.flush()
                row = gateway.db.execute('SELECT * FROM outbox').fetchone()
                self.assertEqual(row['state'], 'pending'); self.assertEqual(row['error'], 'ValueError')
                self.assertEqual(api.sends, {})
                self.assertNotIn('expected_sha256', json.loads(row['payload']))
            finally: gateway.close()


if __name__ == '__main__':
    unittest.main()

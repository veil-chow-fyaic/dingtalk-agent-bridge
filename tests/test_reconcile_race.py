"""Deterministic overlapping status queries; no platform calls or credentials."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest

from dingtalk_bridge.core import Bridge, BridgeError, DWSRequestRejected
from test_core import CFG


def receipt(status):
    result = {'result': {'sendStatus': status}}
    if status == 'SUCCESS':
        result['messageRef'] = {'openConversationId': 'g', 'openMessageId': 'confirmed-message'}
    return result


class ControlledStatus:
    def __init__(self, late, terminal):
        self.late, self.terminal = late, terminal
        self.entered, self.release = threading.Event(), threading.Event()
        self.lock = threading.Lock()
        self.sent = self.queries = 0
        self.racing = False

    def call(self, args):
        with self.lock:
            if '+messages-send' in args:
                self.sent += 1
                return {'sendReceipt': {'openTaskId': 'original-task'}}
            if '+messages-query-send-status' not in args:
                raise AssertionError(args)
            if not self.racing:
                return receipt('PENDING')
            self.queries += 1
            first = self.queries == 1
        if first:
            self.entered.set()
            if not self.release.wait(5):
                raise AssertionError('Controlled query was not released')
            if isinstance(self.late, Exception):
                raise self.late
            return receipt(self.late)
        return receipt(self.terminal)


class ReconcileRaceTests(unittest.TestCase):
    def race(self, late, terminal='SUCCESS', during_send=False):
        with tempfile.TemporaryDirectory() as temp:
            provider = ControlledStatus(late, terminal)
            bridge = Bridge(Path(temp), CFG, provider)
            try:
                if not during_send:
                    self.assertEqual(bridge.send('stable-key', text='synthetic')['state'], 'submitted')
                provider.racing = True
                with ThreadPoolExecutor(max_workers=1) as pool:
                    slow = pool.submit(bridge.send, 'stable-key', text='synthetic') if during_send else pool.submit(bridge.reconcile, 'stable-key')
                    try:
                        self.assertTrue(provider.entered.wait(3))
                        final = bridge.reconcile('stable-key')
                        expected = 'confirmed' if terminal == 'SUCCESS' else 'failed'
                        self.assertEqual(final['state'], expected)
                    finally:
                        provider.release.set()
                    slow_result = slow.result(timeout=5)
                self.assertEqual(slow_result, final)
                self.assertEqual(bridge.delivery('stable-key'), final)
                self.assertEqual(final['task_id'], 'original-task')
                self.assertEqual(final['message_id'], 'confirmed-message' if terminal == 'SUCCESS' else None)
                self.assertIsNone(final['error'])
                self.assertEqual(provider.sent, 1)
                self.assertEqual(provider.queries, 2)
                self.assertEqual(bridge.db.execute('SELECT count(*) FROM rejection_audit').fetchone()[0], 0)
                bridge.close()
                bridge = Bridge(Path(temp), CFG, provider)
                self.assertEqual(bridge.delivery('stable-key'), final)
                self.assertEqual(bridge.reconcile('stable-key'), final)
                replay = bridge.send('stable-key', text='synthetic')
                self.assertTrue(replay.pop('replayed'))
                self.assertEqual(replay, final)
                self.assertEqual(provider.sent, 1)
                self.assertEqual(provider.queries, 2)
            finally:
                bridge.close()

    def test_late_pending_query_cannot_regress_confirmation(self):
        self.race('PENDING')

    def test_late_conflicting_query_cannot_replace_first_committed_terminal(self):
        for late, terminal in [('FAILED', 'SUCCESS'), ('SUCCESS', 'FAILED'), ('PENDING', 'FAILED')]:
            with self.subTest(late=late, terminal=terminal):
                self.race(late, terminal)

    def test_send_initial_query_error_cannot_erase_concurrent_confirmation(self):
        for error in [BridgeError('authorization unavailable'), BridgeError('timeout'),
                      DWSRequestRejected({'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR'})]:
            with self.subTest(error=type(error).__name__ + ':' + str(error)):
                self.race(error, during_send=True)

    def test_send_initial_pending_cannot_erase_concurrent_confirmation(self):
        self.race('PENDING', during_send=True)


if __name__ == '__main__':
    unittest.main()

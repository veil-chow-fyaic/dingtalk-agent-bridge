from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from dingtalk_bridge.core import Bridge, BridgeError
from scripts.probe_history_capacity import BoundedHistory, CONFIG, probe


class HistoryContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dab-history-candidate-')
        self.root = Path(self.temp.name)
        self.provider = BoundedHistory(1001)
        self.bridge = Bridge(self.root, CONFIG, self.provider)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: self.bridge.close())

    def value(self, key):
        row = self.bridge.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return row[0] if row else None

    def restart(self):
        self.bridge.close();self.bridge = Bridge(self.root, CONFIG, self.provider)

    def test_backlog_restart_and_dedup(self):
        self.bridge.sync();before = self.value('history_window')
        self.assertIsNone(self.value('watermark'));self.restart()
        self.assertEqual(before, self.value('history_window'))
        result = self.bridge.sync()
        self.assertEqual(result['inserted'], 1);self.assertTrue(result['complete'])
        self.assertTrue(self.provider.calls[-1]['resumed'])
        self.assertEqual(self.value('watermark'), json.loads(before)['end'])
        self.assertIsNone(self.value('history_window'))
        self.assertEqual(self.bridge.sync()['inserted'], 0)
        self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM events').fetchone()[0], 1001)

    def test_new_arrival_after_frozen_end_is_read_in_next_window(self):
        self.bridge.sync();before = json.loads(self.value('history_window'))
        end = datetime.fromisoformat(before['end'])
        self.provider.messages.append({**self.provider.messages[-1], 'messageId': 'synthetic-new',
                                       'createTime': (end + timedelta(seconds=1)).isoformat()})
        with patch('dingtalk_bridge.core.datetime') as clock:
            clock.now.return_value = end + timedelta(seconds=3)
            clock.fromisoformat.side_effect = datetime.fromisoformat
            self.assertEqual(self.bridge.sync()['inserted'], 1)
            self.assertEqual(self.value('watermark'), before['end'])
            # Subsequent 5-minute overlap excludes this old two-hour backlog.
            self.assertEqual(self.bridge.sync()['inserted'], 1)
        self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM events').fetchone()[0], 1002)

    def test_read_error_partial_and_failure_ledger_retain_cursor(self):
        self.bridge.sync();before = self.value('history_window');real_call = self.provider.call
        with patch.object(self.provider, 'call', side_effect=BridgeError('synthetic read failure')):
            with self.assertRaises(BridgeError):self.bridge.sync()
        self.assertEqual(self.value('history_window'), before)
        for failure in ({'partial': True}, {'failedCount': 1}, {'failures': [{'stage': 'synthetic'}]}):
            def incomplete(args):return {**real_call(args), **failure, 'nextPageToken': 'not-safe-to-use'}
            with patch.object(self.provider, 'call', side_effect=incomplete):self.assertFalse(self.bridge.sync()['complete'])
            self.assertEqual(self.value('history_window'), before);self.assertIsNone(self.value('watermark'))
        self.restart();self.assertTrue(self.bridge.sync()['complete'])
        self.assertEqual(self.value('watermark'), json.loads(before)['end'])

    def test_unsafe_and_repeated_tokens_report_error_without_advancing(self):
        self.bridge.sync();before = self.value('history_window');old = json.loads(before)
        for token in (None, '', 4, 'a' * 8193, 'has whitespace', old['token']):
            response = {'messages': [], 'complete': False, 'hasMore': True, 'stopReason': 'result_limit', 'nextPageToken': token}
            with self.subTest(tokenType=type(token).__name__), patch.object(self.provider, 'call', return_value=response):
                with self.assertRaises(BridgeError):self.bridge.sync()
                self.assertEqual(self.value('history_window'), before);self.assertIsNone(self.value('watermark'))
        with patch.object(self.provider, 'call', return_value={'messages': [], 'complete': True, 'hasMore': True}):
            with self.assertRaises(BridgeError):self.bridge.sync()
        self.assertEqual(self.value('history_window'), before);self.assertTrue(self.bridge.sync()['complete'])

    def test_cursor_cycle_rejected_across_restart(self):
        self.bridge.sync();old = json.loads(self.value('history_window'))
        response = {'messages': [], 'complete': False, 'hasMore': True, 'stopReason': 'page_limit', 'nextPageToken': 'synthetic-next-token'}
        with patch.object(self.provider, 'call', return_value=response):self.bridge.sync()
        current = self.value('history_window');self.restart()
        with patch.object(self.provider, 'call', return_value={**response, 'nextPageToken': old['token']}):
            with self.assertRaises(BridgeError):self.bridge.sync()
        self.assertEqual(self.value('history_window'), current);self.assertIsNone(self.value('watermark'))

    def test_transaction_failure_cannot_advance_cursor_or_watermark(self):
        self.bridge.db.executescript("""CREATE TRIGGER fail_checkpoint BEFORE UPDATE ON meta
            WHEN NEW.key='history_window' BEGIN SELECT RAISE(ABORT,'synthetic crash boundary'); END;""")
        with self.assertRaises(sqlite3.IntegrityError):self.bridge.sync()
        self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM events').fetchone()[0], 0)
        self.assertIsNone(json.loads(self.value('history_window'))['token']);self.assertIsNone(self.value('watermark'))
        self.bridge.db.execute('DROP TRIGGER fail_checkpoint');self.bridge.db.commit();self.restart()
        self.assertEqual(self.bridge.sync()['inserted'], 1000);before = self.value('history_window')
        self.bridge.db.executescript("""CREATE TRIGGER fail_watermark BEFORE INSERT ON meta
            WHEN NEW.key='watermark' BEGIN SELECT RAISE(ABORT,'synthetic completion boundary'); END;""")
        with self.assertRaises(sqlite3.IntegrityError):self.bridge.sync()
        self.assertEqual(self.value('history_window'), before)
        self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM events').fetchone()[0], 1000)
        self.assertIsNone(self.value('watermark'))
        self.bridge.db.execute('DROP TRIGGER fail_watermark');self.bridge.db.commit();self.restart()
        self.assertEqual(self.bridge.sync()['inserted'], 1);self.assertTrue(self.provider.calls[-1]['resumed'])

    def test_corrupt_persisted_state_fails_before_provider(self):
        self.bridge.sync();valid = json.loads(self.value('history_window'));bad_states = ['{', 'null', '[]']
        for key, value in [('version', True), ('deep', 1), ('target', ['--group', 'other']), ('start', '2026-01-01'),
                           ('end', 'bad'), ('token', None), ('seen', []), ('seen', ['not-hash']), ('extra', 1)]:
            bad_states.append(json.dumps({**valid, key: value}))
        for saved in bad_states:
            with self.subTest(saved=saved[:40]):
                self.bridge.db.execute('UPDATE meta SET value=? WHERE key="history_window"', (saved,));self.bridge.db.commit()
                with patch.object(self.provider, 'call') as call:
                    with self.assertRaises(BridgeError):self.bridge.sync()
                    call.assert_not_called()
                self.assertEqual(self.value('history_window'), saved);self.assertIsNone(self.value('watermark'))

    def test_large_probe_completes_with_one_bounded_request_per_poll(self):
        result = probe(5000, 5)
        self.assertTrue(result['progressSatisfied']);self.assertEqual(result['insertedPerPoll'], [1000] * 5)
        self.assertEqual([c['resumed'] for c in result['calls']], [False, True, True, True, True])
        self.assertEqual(result['completePerPoll'], [False] * 4 + [True])


if __name__ == '__main__':unittest.main()

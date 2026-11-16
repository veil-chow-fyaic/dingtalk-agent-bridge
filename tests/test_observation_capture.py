import copy
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import capture_service_observations as capture
import service_observation_evidence as evidence
import review_service_observations as reviewer


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def version():
    return {'sourceSha256': {'dingtalk_bridge/core.py': 'synthetic-source'},
            'collectorSha256': {'capture_service_observations.py': 'synthetic-collector'},
            'configSha256': {'local/service-config.json': 'synthetic-config'},
            'components': [{'name': 'transport', 'pid': 123, 'identity': 'synthetic',
                            'status': 'running', 'configMatches': True}],
            'managerJournal': '', 'managerJournalSha256': evidence.digest(b''),
            'loadedSourceProven': False}


class ObservationCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.run = self.root / 'run'; self.run.mkdir()
        self.route = {'accountId': 'synthetic', 'profile': 'synthetic:user', 'conversationId': 'room',
                      'conversationType': 'group', 'binary': 'unused', 'stateStorage': 'legacy'}
        folder = self.root / 'local/runtime'; folder.mkdir(parents=True)
        self.dbpath = folder / 'bridge.sqlite3'
        with closing(sqlite3.connect(self.dbpath)) as db:
            db.executescript('PRAGMA journal_mode=WAL; CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);'
                'CREATE TABLE events(seq INTEGER PRIMARY KEY,body TEXT); CREATE TABLE deliveries(state TEXT);')
            db.executemany('INSERT INTO meta VALUES (?,?)', [('scope', json.dumps(['synthetic:user', 'room'])),
                                                            ('watermark', iso(86410))])
            db.execute('INSERT INTO deliveries VALUES ("outcome_unknown")')
            db.commit()
        self.event = {'account_id': 'synthetic', 'conversation_id': 'room', 'message_id': 'm1', 'content': 'synthetic'}

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, after=None, at=9):
        return evidence.route_snapshot(self.root, self.route, None, 0, after, clock=lambda: at)

    def bundle(self):
        start = self.snapshot()
        baseline = {'schemaVersion': 2, 'at': 9, 'routes': [self.route], 'cursors': [0],
                    'snapshots': [start], 'version': version(), 'cutoffAt': 86410}
        status = {'schemaVersion': 2, 'startedAt': 10, 'updatedAt': 86410, 'elapsed_seconds': 86400,
                  'cutoffAt': 86410, 'interval_seconds': 30, 'duration_seconds': 86400,
                  'samples': 2880, 'unavailable_samples': 0, 'new_events': 0,
                  'active': False, 'stop_reason': 'duration_reached'}
        samples = [{'observedAt': 10 + n * 30, 'events': [], 'health': {}, 'version': version()} for n in range(2880)]
        ledger = {'schemaVersion': 2, 'cutoffAt': 86410, 'routes': [self.snapshot(0, 86410)], 'version': version()}
        return baseline, status, samples, ledger

    def save_bundle(self, bundle):
        baseline, status, samples, ledger = bundle
        for name, data in [('baseline', baseline), ('status', status), ('ledger', ledger)]:
            evidence.write_json(self.run / (name + '.json'), data)
        (self.run / 'observations.ndjson').write_text(''.join(json.dumps(s) + '\n' for s in samples))
        (self.run / 'maintenance.ndjson').write_text('')
        evidence.seal(self.run)

    def test_complete_capture_does_not_claim_loaded_code_or_refresh(self):
        self.save_bundle(self.bundle())
        report = reviewer.load_review(self.run)
        self.assertTrue(report['evidence_valid']); self.assertTrue(report['observation_complete_24h'])
        self.assertFalse(report['stability_pass'])
        self.assertFalse(report['cutoff']['uniform_loaded_version_proven'])
        self.assertFalse(report['cutoff']['natural_refresh_proven'])
        self.assertEqual(self.snapshot()['deliveries'], {'outcome_unknown': 1})

    def test_missing_tampered_and_truncated_files_fail_closed(self):
        self.save_bundle(self.bundle())
        for name in (*evidence.SEALED_FILES, 'completion.json'):
            path = self.run / name; original = path.read_bytes()
            with self.subTest(file=name):
                mutations = [None, b'invalid-json' if name == 'completion.json' else original + b' ']
                if len(original) > 12: mutations.append(original[:12])
                for data in mutations:
                    if data is None: path.unlink()
                    else: path.write_bytes(data)
                    with self.assertRaises((OSError, ValueError, KeyError, TypeError)):
                        reviewer.load_review(self.run)
                    path.write_bytes(original)

    def test_removing_schema_markers_cannot_skip_new_cutoff_checks(self):
        bundle = self.bundle(); del bundle[0]['schemaVersion']; del bundle[1]['schemaVersion']
        self.save_bundle(bundle)
        with self.assertRaisesRegex(ValueError, 'downgraded'):
            reviewer.load_review(self.run)
        (self.run / 'completion.json').unlink()
        with self.assertRaisesRegex(ValueError, 'downgraded'):
            reviewer.load_review(self.run)

    def test_review_cli_cannot_overwrite_preserved_artifacts(self):
        self.save_bundle(self.bundle())
        original = (self.run / 'status.json').read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPTS / 'review_service_observations.py'),
            '--run-dir', str(self.run), '--output', str(self.run / 'status.json')], capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.run / 'status.json').read_bytes(), original)

    def test_late_early_missing_wrong_route_and_uncovered_cutoff_are_rejected(self):
        bundle = self.bundle()
        cases = {'late': lambda r: r.update(snapshotStartedAt=86416, snapshotAcquiredAt=86416, snapshotEndedAt=86416),
                 'too_long': lambda r: r.update(snapshotEndedAt=86426),
                 'early': lambda r: r.update(snapshotStartedAt=86409),
                 'uncovered': lambda r: r.update(watermark=iso(86409)),
                 'naive_time': lambda r: r.update(watermark='1970-01-02T00:00:10'),
                 'pending_page': lambda r: r.update(history_window='{}'),
                 'scope': lambda r: r.update(scope=['other', 'room']),
                 'failed': lambda r: r.update(error='OperationalError'),
                 'sequence': lambda r: r.update(highSequence=10)}
        for name, change in cases.items():
            mutated = copy.deepcopy(bundle); change(mutated[3]['routes'][0])
            with self.subTest(case=name):
                self.assertFalse(evidence.review_cutoff(*mutated, [])['cutoff_evidence_valid'])
        for rows in ([], bundle[3]['routes'] * 2):
            mutated = copy.deepcopy(bundle); mutated[3]['routes'] = rows
            self.assertFalse(evidence.review_cutoff(*mutated, [])['cutoff_evidence_valid'])

    def test_concurrent_wal_commit_does_not_mix_watermark_and_event_rows(self):
        calls = 0
        def clock():
            nonlocal calls
            calls += 1
            if calls == 2:  # Snapshot acquired by meta SELECT, before events SELECT.
                with closing(sqlite3.connect(self.dbpath)) as writer:
                    writer.execute('INSERT INTO events VALUES (1,?)', (json.dumps(self.event),))
                    writer.execute('UPDATE meta SET value=? WHERE key="watermark"', (iso(90000),))
                    writer.commit()
            return 86410
        row = evidence.route_snapshot(self.root, self.route, None, 0, 0, clock)
        self.assertEqual(row['highSequence'], 0); self.assertEqual(row['events'], [])
        self.assertEqual(row['watermark'], iso(86410))
        later = self.snapshot(0, 86411)
        self.assertEqual(later['highSequence'], 1); self.assertEqual(later['watermark'], iso(90000))

    def test_each_route_has_its_own_cutoff_and_failure_cannot_hide_behind_first_route(self):
        baseline, status, samples, ledger = self.bundle()
        second = {**self.route, 'conversationId': 'second-room'}
        baseline['routes'].append(second); baseline['cursors'].append(0)
        for rows in (baseline['snapshots'], ledger['routes']):
            row = copy.deepcopy(rows[0]); row.update(routeIndex=1, conversation_id='second-room',
                                                    scope=['synthetic:user', 'second-room'])
            rows.append(row)
        ledger['routes'][1].update(snapshotStartedAt=86411, snapshotAcquiredAt=86411, snapshotEndedAt=86412)
        self.assertTrue(evidence.review_cutoff(baseline, status, samples, ledger, [])['cutoff_evidence_valid'])
        ledger['routes'][1]['history_window'] = '{}'
        result = evidence.review_cutoff(baseline, status, samples, ledger, [])
        self.assertTrue(result['checks']['route_0_coverage']); self.assertFalse(result['checks']['route_1_coverage'])
        self.assertFalse(result['cutoff_evidence_valid'])

    def test_sampled_content_is_exact_and_ledger_only_tail_is_separate(self):
        bundle = self.bundle()
        event = {**self.event, 'seq': 2}
        bundle[3]['routes'][0].update(highSequence=2, events=[event])
        result = evidence.review_cutoff(*bundle, [])
        self.assertTrue(result['cutoff_evidence_valid']); self.assertEqual(result['routes'][0]['ledgerOnlyTailEvents'], 1)
        bundle[2][0]['events'] = [{'route': 0, 'event': {**event, 'content': 'mutated'}}]
        self.assertFalse(evidence.review_cutoff(*bundle, [])['cutoff_evidence_valid'])

    def test_version_changes_restart_missing_evidence_and_maintenance_fail(self):
        bundle = self.bundle()
        for key, value in [('sourceSha256', {}), ('collectorSha256', {}), ('configSha256', {}), ('components', []),
                           ('managerJournal', 'restart'), ('error', 'OSError')]:
            changed = copy.deepcopy(bundle); changed[2][5]['version'][key] = value
            with self.subTest(key=key):
                self.assertFalse(evidence.review_cutoff(*changed, [])['cutoff_evidence_valid'])
        self.assertFalse(evidence.review_cutoff(*bundle, [{'at': 20, 'reason': 'maintenance'}])['cutoff_evidence_valid'])
        bundle[3]['version']['loadedSourceProven'] = True
        self.assertFalse(evidence.review_cutoff(*bundle, [])['uniform_loaded_version_proven'])

    def test_version_snapshot_hashes_config_without_copying_values_or_claiming_loaded_source(self):
        (self.root / 'dingtalk_bridge').mkdir()
        (self.root / 'dingtalk_bridge/core.py').write_text('# synthetic source')
        (self.root / 'scripts').mkdir()
        for name in ('capture_service_observations.py', 'service_observation_evidence.py', 'review_service_observations.py'):
            (self.root / 'scripts' / name).write_text('# synthetic collector')
        config = self.root / 'local/service-config.json'; config.write_text('{"synthetic":"not-for-copying"}')
        record = {'name': 'transport', 'pid': 123, 'identity': 'synthetic', 'startedAt': 10,
                  'config': str(config), 'configSha256': evidence.digest(config.read_bytes())}
        with patch.object(evidence, 'Manager') as manager:
            manager.return_value.read_state.return_value = {'components': [record]}
            manager.return_value.component_status.return_value = 'running'
            result = evidence.version_snapshot(self.root)
            self.assertTrue(result['components'][0]['configMatches'])
            self.assertEqual(len(result['collectorSha256']), 3)
            self.assertNotIn('not-for-copying', json.dumps(result))
            self.assertFalse(result['loadedSourceProven'])
            config.write_text('{}')
            self.assertFalse(evidence.version_snapshot(self.root)['components'][0]['configMatches'])

    def test_database_failure_is_saved_without_creating_a_database(self):
        self.dbpath.unlink()
        rows = evidence.snapshot_routes(self.root, [self.route], [0])
        self.assertEqual(rows[0]['error'], 'OperationalError'); self.assertFalse(self.dbpath.exists())

    def run_capture(self, fail=False, signal=False, finalization=False):
        class Clock:
            now = 10
            def time(self): return self.now
            def is_set(self): return signal
            def wait(self, duration): self.now += duration
        clock = Clock()
        calls = 0
        def get(path):
            nonlocal calls
            calls += 1
            if fail and calls == 2: raise KeyboardInterrupt()
            return {'events': [], 'next_cursor': 0} if path.startswith('/v1/events') else {}
        def snapshots(root, routes, cursors=None):
            if finalization and cursors is not None: raise OSError('synthetic disk failure')
            return [self.snapshot(None if cursors is None else cursors[0], clock.now)]
        with patch.object(capture, 'safe_version_snapshot', return_value=version()), patch.object(capture, 'snapshot_routes', side_effect=snapshots):
            return capture.capture(self.root, self.run, [self.route], get, 10, 1, clock, clock.time, clock.time)

    def test_collector_publishes_all_artifacts_and_seal_on_normal_expiry(self):
        status = self.run_capture()
        self.assertEqual(status['stop_reason'], 'duration_reached')
        report = reviewer.load_review(self.run)
        self.assertTrue(report['evidence_valid']); self.assertFalse(report['observation_complete_24h'])
        self.assertEqual((self.run / 'ledger.json').stat().st_mode & 0o077, 0)

    def test_exception_and_signal_preserve_terminal_reason_and_never_pass(self):
        with self.assertRaises(KeyboardInterrupt): self.run_capture(fail=True)
        self.assertEqual(json.loads((self.run / 'status.json').read_text())['stop_reason'], 'exception')
        self.assertFalse(reviewer.load_review(self.run)['evidence_valid'])
        for path in self.run.iterdir(): path.unlink()
        self.run_capture(signal=True)
        self.assertEqual(json.loads((self.run / 'status.json').read_text())['stop_reason'], 'signal')
        self.assertFalse(reviewer.load_review(self.run)['evidence_valid'])

    def test_finalization_failure_leaves_no_completion_seal(self):
        with self.assertRaises(OSError): self.run_capture(finalization=True)
        self.assertEqual(json.loads((self.run / 'status.json').read_text())['stop_reason'], 'finalization_failed')
        self.assertFalse((self.run / 'completion.json').exists())
        with self.assertRaises(OSError): reviewer.load_review(self.run)

    def test_real_sigkill_cannot_produce_a_completed_run(self):
        code = '''import json,os,signal,sys,threading
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import capture_service_observations as c
c.safe_version_snapshot=lambda root: {}
calls=0
def get(path):
 global calls
 calls+=1
 if calls==2: os.kill(os.getpid(),signal.SIGKILL)
 return {}
c.capture(Path(sys.argv[2]),Path(sys.argv[3]),json.loads(sys.argv[4]),get,10,1,threading.Event())
'''
        result = subprocess.run([sys.executable, '-c', code, str(SCRIPTS), str(self.root), str(self.run),
                                 json.dumps([self.route])], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, -9)
        self.assertTrue(json.loads((self.run / 'status.json').read_text())['active'])
        self.assertFalse((self.run / 'completion.json').exists())
        with self.assertRaises(OSError): reviewer.load_review(self.run)


if __name__ == '__main__': unittest.main()

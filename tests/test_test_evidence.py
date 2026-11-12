import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_tests_with_evidence import ManagerEvidence, run_suite
from dingtalk_bridge.service_manager import Manager


class TestEvidenceTests(unittest.TestCase):
    def test_empty_suite_is_rejected_but_executed_suite_still_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            empty = run_suite(unittest.TestSuite(), root / 'empty', io.StringIO())
            self.assertFalse(empty['ok'])
            self.assertFalse(empty['suitePassed'])
            self.assertEqual(empty['testsRun'], 0)
            self.assertEqual(empty['validationErrors'], ['no_tests_executed'])
            executed = []
            suite = unittest.TestSuite([unittest.FunctionTestCase(lambda: executed.append(True))])
            actual = run_suite(suite, root / 'actual', io.StringIO())
            self.assertEqual(executed, [True])
            self.assertTrue(actual['ok']);self.assertTrue(actual['suitePassed'])
            self.assertEqual(actual['validationErrors'], [])

    def test_unmatched_cli_pattern_fails_with_retained_empty_summary(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            p = subprocess.run([sys.executable, str(root / 'scripts/run_tests_with_evidence.py'),
                                '--start-directory', temp, '--pattern', 'not_a_test_*.py'],
                               cwd=root, capture_output=True, text=True, timeout=15)
        result = json.loads(p.stdout.splitlines()[-1])
        self.assertEqual(p.returncode, 1)
        self.assertFalse(result['ok']);self.assertEqual(result['testsRun'], 0)
        summary = json.loads((Path(result['evidence']) / 'summary.json').read_text())
        self.assertFalse(summary['suitePassed']);self.assertFalse(summary['ok'])
        self.assertEqual(summary['validationErrors'], ['no_tests_executed'])

    def test_original_failure_and_exact_observation_survive_fixture_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);fixture = root / 'fixture';output = root / 'evidence'
            observed = {'stdout': 'synthetic exact deciding ps output', 'returncode': 0}

            class FailingFixture(unittest.TestCase):
                def runTest(self):
                    self.manager = Manager(fixture)
                    self.manager.observations[12345] = observed
                    self.manager.ownership_error({'name': 'transport', 'pid': 12345,
                                                 'identity': 'synthetic owned'}, 'stop-after-signal', 'original refusal')

                def tearDown(self):
                    shutil.rmtree(fixture)

            with patch('dingtalk_bridge.service_manager.os.kill') as kill, \
                    patch('dingtalk_bridge.service_manager.process_identity') as identity:
                report = run_suite(unittest.TestSuite([FailingFixture()]), output, io.StringIO())
            self.assertFalse(report['ok']);self.assertEqual(report['errors'], 1)
            self.assertFalse(fixture.exists());self.assertEqual(report['retentionErrors'], [])
            self.assertEqual(len(report['refusals']), 1)
            saved = output / report['refusals'][0]['folder']
            self.assertEqual(json.loads((saved / 'decision.json').read_text())['observed'], observed)
            self.assertEqual(json.loads((saved / 'manager-identity-errors.ndjson').read_text())['observed'], observed)
            self.assertEqual(saved.stat().st_mode & 0o777, 0o700)
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in saved.iterdir()))
            kill.assert_not_called();identity.assert_not_called()

    def test_retention_failure_does_not_mask_original_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);blocked = root / 'blocked';blocked.write_text('file')
            evidence = ManagerEvidence(blocked)
            with evidence.capture(), self.assertRaisesRegex(RuntimeError, '^original refusal$'):
                Manager(root / 'fixture').ownership_error({'name': 'transport', 'pid': 12345,
                    'identity': 'synthetic owned'}, 'stop-precheck', 'original refusal')
            self.assertEqual(evidence.records, [])
            self.assertEqual(evidence.write_errors, ['FileExistsError'])


if __name__ == '__main__':unittest.main()

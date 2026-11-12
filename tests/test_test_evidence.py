import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_tests_with_evidence import ManagerEvidence, run_suite
from dingtalk_bridge.service_manager import Manager


class TestEvidenceTests(unittest.TestCase):
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

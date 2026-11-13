"""Synthetic persisted-session migration; no real runtime or official CLI."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from dingtalk_bridge.agent_gateway import Gateway,session_contract,contract_json
from dingtalk_bridge.dws_access import DWSAccess
from dingtalk_bridge.official_tools import CONTEXT, GUIDE, WRAPPER
from test_agent_gateway import FakeAPI, FakeRuntime, SETTINGS
from test_routing_consumer import CFG, event


class OfficialContextUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.api, self.runtime = FakeAPI(), FakeRuntime()
        self.g = Gateway(self.root, CFG, None, SETTINGS, self.api, self.runtime)
        self.addCleanup(lambda: self.g.close())
        # Seed a completed task/native session and a distinct failed task.
        self.api.events = [event(1, text='/agent original task')]
        self.g.intake(); self.assertTrue(self.g.execute_one()); self.g.flush()
        original = self.runtime.run
        def fail(*args):
            raise RuntimeError('synthetic prior failure')
        self.runtime.run = fail
        self.api.events.append(event(2, text='/agent prior failed task'))
        self.g.intake(); self.assertTrue(self.g.execute_one()); self.g.flush()
        self.runtime.run = original
        self.old_jobs = [tuple(r) for r in self.g.db.execute('SELECT * FROM jobs ORDER BY seq')]
        self.old_outbox = [tuple(r) for r in self.g.db.execute('SELECT * FROM outbox ORDER BY key')]
        self.old_keys = set(self.api.sends)
        self.workspace = self.g.workspace()
        self.binary = self.root / 'dws'
        self.binary.write_text('#!/bin/sh\ntouch "' + str(self.root / 'unexpected-invocation') + '"\nexit 91\n')
        self.binary.chmod(0o700)
        (self.workspace / CONTEXT).write_text(json.dumps({
            'schemaVersion': 1, 'binary': str(self.binary), 'profile': CFG['profile']}))
        (self.workspace / GUIDE).write_text('legacy instructions: use raw binary --as user')
        self.keep = self.workspace / 'user-notes.txt'
        self.keep.write_text('keep user history')
        self.keep_bytes = self.keep.read_bytes()
        self.artifact = self.workspace / 'exports/report.txt'
        self.artifact_bytes = self.artifact.read_bytes()
        access = DWSAccess(self.root)
        with access.lock(timeout=0):
            access.block('operator_suspended')
        self.pause_path, self.pause_bytes = access.block_path, access.block_path.read_bytes()

    def reopen(self, enabled):
        self.g.close()
        self.g = Gateway(self.root, CFG, None,
                         {**SETTINGS, 'officialDwsTools': enabled}, self.api, self.runtime)
        self.g.intake()
        self.assertFalse(self.g.execute_one())
        self.g.flush()
        self.assertEqual(set(self.api.sends), self.old_keys)

    def assert_history_preserved(self):
        self.assertEqual([tuple(r) for r in self.g.db.execute('SELECT * FROM jobs WHERE seq <= 2 ORDER BY seq')], self.old_jobs)
        old_ids = {r[0] for r in self.old_jobs}
        self.assertEqual([tuple(r) for r in self.g.db.execute('SELECT * FROM outbox ORDER BY key')
                          if r['job_id'] in old_ids], self.old_outbox)
        self.assertEqual(dict(self.g.db.execute('SELECT key,value FROM meta'))['session_id'], 'native-session')
        self.assertEqual(dict(self.g.db.execute('SELECT key,value FROM meta'))['generation'], '0')
        self.assertEqual(self.keep.read_bytes(), self.keep_bytes)
        self.assertEqual(self.artifact.read_bytes(), self.artifact_bytes)
        self.assertEqual(self.pause_path.read_bytes(), self.pause_bytes)
        self.assertFalse((self.root / 'unexpected-invocation').exists())
        self.assertEqual([r[0] for r in self.g.db.execute('SELECT state FROM jobs ORDER BY seq')],
                         ['completed', 'failed', 'completed'])

    def test_legacy_direct_binary_is_refreshed_before_resuming_existing_session(self):
        self.reopen(True)
        # C04 makes enabling a tool surface an explicit compatibility decision.
        # This fixture's reviewed migration changes only the generated wrapper;
        # unreviewed changes are rejected in test_session_compatibility.
        with self.g.db:self.g.db.execute('UPDATE meta SET value=? WHERE key="session_contract"',
                                        (contract_json(session_contract(self.g.settings)),))
        seen = []
        def resumed(prompt, workspace, run_dir, session, cancel, remember, images):
            seen.append(session)
            self.assertEqual(workspace, self.workspace)
            self.assertEqual(session, 'native-session')
            context = json.loads((workspace / CONTEXT).read_text())
            self.assertEqual(context['schemaVersion'], 2)
            self.assertEqual(context['profile'], CFG['profile'])
            self.assertEqual(Path(context['binary']), workspace / WRAPPER)
            self.assertIn(GUIDE, prompt); self.assertIn(CONTEXT, prompt)
            self.assertNotIn(str(self.binary), prompt)
            self.assertIn('办公命令没有通用--as参数', (workspace / GUIDE).read_text())
            # Run only the generated bridge wrapper. The synthetic binary
            # would leave a marker if suspension were bypassed.
            result = subprocess.run([context['binary'], 'doc', '--help'], cwd=workspace,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 75, result.stderr)
            self.assertEqual(json.loads(result.stderr)['error']['reason'], 'operator_suspended')
            return {'text': 'synthetic guarded continuation', 'files': []}
        self.runtime.run = resumed
        self.api.events.append(event(3, text='/agent new explicit task'))
        self.g.intake(); self.assertTrue(self.g.execute_one()); self.assertFalse(self.g.execute_one())
        self.assertEqual(seen, ['native-session'])
        self.assert_history_preserved()

    def test_disabling_office_tools_removes_legacy_context_without_resetting_session(self):
        self.reopen(False)
        seen = []
        def resumed(prompt, workspace, run_dir, session, cancel, remember, images):
            seen.append(session)
            self.assertEqual(session, 'native-session')
            self.assertEqual(workspace, self.workspace)
            for name in (CONTEXT, GUIDE, WRAPPER):
                self.assertFalse((workspace / name).exists())
                self.assertNotIn(name, prompt)
            return {'text': 'synthetic ordinary continuation', 'files': []}
        self.runtime.run = resumed
        self.api.events.append(event(3, text='/agent new non-office task'))
        self.g.intake(); self.assertTrue(self.g.execute_one()); self.assertFalse(self.g.execute_one())
        self.assertEqual(seen, ['native-session'])
        self.assert_history_preserved()


if __name__ == '__main__':
    unittest.main()

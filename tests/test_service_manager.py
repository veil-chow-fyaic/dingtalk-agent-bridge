import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge.service_manager import Manager, process_identity


WORKER = '''import argparse,json,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config');a=p.parse_args()
if json.loads(Path(a.config).read_text()).get('fail'):
 time.sleep(.3);raise SystemExit(7)
print(json.dumps({'synthetic_ready':True}),flush=True)
while True:time.sleep(.1)
'''


class SyntheticManager(Manager):
    """Real owned processes, controlled modules, no DWS or HTTP/network calls."""
    def specs(self):
        paths = [self.config, *self.agents]
        return [{'name': 'transport' if i == 0 else 'agent-' + str(i),
                 'module': 'dingtalk_bridge' if i == 0 else 'dingtalk_bridge.agent_gateway',
                 'config': str(p), 'configSha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for i, p in enumerate(paths)]

    def port_unused(self): return True

    def ready(self, record):
        if self.component_status(record) != 'running': return False
        with (self.root / record['log']).open('rb') as log:
            log.seek(record['logOffset'])
            return b'"synthetic_ready": true' in log.read()


class ServiceManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        package = self.root / 'dingtalk_bridge'; package.mkdir()
        (package / '__init__.py').write_text('')
        for name in ('__main__.py', 'agent_gateway.py'): (package / name).write_text(WORKER)
        for name in ('service.json', 'agent-a.json', 'agent-b.json'):
            (self.root / name).write_text('{}')
        self.manager = SyntheticManager(self.root, 'service.json', ['agent-a.json', 'agent-b.json'])

    def tearDown(self):
        try:
            self.manager.stop(timeout=3)
        finally:
            for child in self.manager.children.values():
                if child.poll() is None: child.terminate()
                child.wait(timeout=3)
            self.tmp.cleanup()

    def test_real_process_start_is_idempotent_and_stop_uses_persisted_ownership(self):
        result = self.manager.start(timeout=3)
        self.assertTrue(result['all_running']);self.assertEqual(len(result['components']),3)
        pids = [c['pid'] for c in result['components']]
        self.assertEqual([c['pid'] for c in self.manager.start(timeout=3)['components']],pids)
        other = SyntheticManager(self.root, 'service.json', ['agent-a.json', 'agent-b.json'])
        stopped = other.stop(timeout=3)
        self.assertTrue(all(c['status']=='stopped' for c in stopped['components']))
        self.assertTrue(all(process_identity(pid) is None for pid in pids))
        self.assertEqual(self.manager.state_path.stat().st_mode & 0o077,0)

    def test_startup_failure_rolls_back_only_new_children(self):
        self.manager.agents=[]
        transport=self.manager.start(timeout=3)['components'][0]['pid']
        (self.root/'agent-a.json').write_text('{"fail":true}')
        self.manager.agents=[self.root/'agent-a.json']
        with self.assertRaises(RuntimeError): self.manager.start(timeout=2)
        self.assertIsNotNone(process_identity(transport))
        for record in self.manager.read_state()['components']:
            if record['name']!='transport':self.assertEqual(self.manager.component_status(record),'stopped')

    def test_initial_startup_failure_rolls_back_transport_and_prior_new_agents(self):
        (self.root/'agent-b.json').write_text('{"fail":true}')
        with self.assertRaises(RuntimeError):self.manager.start(timeout=2)
        self.assertTrue(all(c['status']=='stopped' for c in self.manager.status()['components']))

    def test_transient_pre_exec_identity_is_not_persisted(self):
        seen=set()
        def observed(pid):
            if pid not in seen:
                seen.add(pid)
                return 'transient launcher before exec'
            return process_identity(pid)
        with patch('dingtalk_bridge.service_manager.process_identity',side_effect=observed):
            self.assertTrue(self.manager.start(timeout=3)['all_running'])
        state=self.manager.read_state()
        self.assertEqual(len(state['components']),3)
        self.assertTrue(all(not r.get('starting') for r in state['components']))
        self.assertTrue(all('transient launcher' not in r['identity'] for r in state['components']))

    def test_changed_pid_identity_never_signals_foreign_process(self):
        self.manager.start(timeout=3); original=self.manager.read_state()
        foreign=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        try:
            changed=json.loads(json.dumps(original));changed['components'][0]['pid']=foreign.pid
            self.manager.save(changed)
            with self.assertRaisesRegex(RuntimeError,'ownership'):self.manager.stop(timeout=1)
            with self.assertRaisesRegex(RuntimeError,'ownership'):self.manager.start(timeout=1)
            self.assertIsNone(foreign.poll())
        finally:
            self.manager.save(original);foreign.terminate();foreign.wait(timeout=3)

    def test_config_drift_requires_stop_and_stop_does_not_need_current_config(self):
        self.manager.start(timeout=3)
        (self.root/'agent-a.json').write_text('{"updated":true}')
        with self.assertRaisesRegex(RuntimeError,'configuration changed'):self.manager.start(timeout=1)
        (self.root/'service.json').unlink()
        self.assertTrue(all(c['status']=='stopped' for c in self.manager.stop(timeout=3)['components']))

    def test_unmanaged_port_is_not_adopted_or_signalled(self):
        with patch.object(self.manager,'port_unused',return_value=False),patch.object(self.manager,'spawn') as spawn:
            with self.assertRaisesRegex(RuntimeError,'unmanaged'):self.manager.start(timeout=1)
        spawn.assert_not_called()
        self.assertEqual(self.manager.read_state()['components'],[])

    def test_status_stop_and_plan_are_read_only_without_existing_state(self):
        self.assertFalse(self.manager.status()['managed']);self.manager.stop();self.manager.plan()
        self.assertFalse(self.manager.folder.exists())

    def test_concurrent_lifecycle_operation_is_rejected(self):
        with self.manager.locked():
            with self.assertRaisesRegex(RuntimeError,'operation is in progress'):
                SyntheticManager(self.root,'service.json',[]).start(timeout=1)

    def test_duplicate_agent_scopes_and_mismatched_bridge_config_are_rejected(self):
        (self.root/'agent-a.json').write_text(json.dumps({'bridgeConfig':'service.json','accountId':'a','conversationId':'g'}))
        (self.root/'agent-b.json').write_bytes((self.root/'agent-a.json').read_bytes())
        actual=Manager(self.root,'service.json',['agent-a.json','agent-b.json'])
        with patch('dingtalk_bridge.service_manager.diagnose',return_value={'ok':True}):
            with self.assertRaisesRegex(ValueError,'same conversation'):actual.specs()
            actual.agents=[self.root/'agent-a.json'];actual.config=self.root/'other-service.json'
            with self.assertRaisesRegex(ValueError,'selected bridge'):actual.specs()

    def test_preflight_failure_creates_no_runtime_files(self):
        with patch('dingtalk_bridge.service_manager.diagnose',return_value={'ok':False}):
            with self.assertRaisesRegex(ValueError,'preflight'):Manager(self.root,'missing.json').start()
        self.assertFalse(self.manager.folder.exists())


if __name__ == '__main__':unittest.main()

from contextlib import closing, nullcontext, redirect_stdout
import io
import importlib.util
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.routing import route_configs

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_migration', ROOT / 'scripts/migrate_agent_runtime_binding.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class RuntimeBindingMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='runtime migration 空格 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'local').mkdir()
        service = {'routes': [{'accountId': 'synthetic-account', 'profile': 'synthetic-profile',
            'conversationId': 'synthetic-dm', 'conversationType': 'direct',
            'peerOpenDingTalkId': 'synthetic-peer', 'binary': 'not-executed'}]}
        (self.root / 'local/service-config.json').write_text(json.dumps(service))
        self.old = self.root / 'local/old.json'
        self.new = self.root / 'local/active.json'
        self.settings = {'accountId': 'synthetic-account', 'conversationId': 'synthetic-dm',
            'bridgeConfig': 'local/service-config.json', 'allowedSenderIds': ['synthetic-user'],
            'runtime': {'kind': 'kimi', 'binary': 'synthetic-kimi', 'timeoutSeconds': 60}}
        self.old.write_text(json.dumps(self.settings))
        candidate = json.loads(self.old.read_text())
        candidate['runtime']['kind'] = 'codex'
        candidate['runtime']['binary'] = 'synthetic-codex'
        self.new.write_text(json.dumps(candidate))
        route, state = next(route_configs(service))
        gateway = Gateway(self.root, route, state, self.settings, api=object(), runtime=object())
        self.database = gateway.local / 'tasks.sqlite3'
        gateway.db.execute('UPDATE meta SET value="1" WHERE key="generation"')
        gateway.db.execute('INSERT INTO meta VALUES("session_history/0",?)', ('private-old-session-and-contract',))
        for seq, status, command in [(1, 'completed', 'old private task'), (2, 'failed', 'old failure'), (3, 'completed', 'new')]:
            gateway.db.execute('INSERT INTO jobs(id,seq,command,model,state) VALUES(?,?,?,?,?)',
                               (str(seq), seq, command, '{}', status))
        for key, status in [('old-confirmed', 'confirmed'), ('old-failed', 'failed')]:
            gateway.db.execute('INSERT INTO outbox(key,job_id,payload,state) VALUES(?,?,?,?)',
                               (key, '1', 'private-payload', status))
        gateway.db.commit()
        gateway.close()

    def plan(self):
        return migration.create_plan(self.root, self.old, self.new)

    def openclaw_candidate(self, name='host'):
        from test_openclaw_runtime import configuration
        host=self.root/'local'/(name+'.json');host.write_text(json.dumps(configuration()))
        return {'kind':'openclaw','binary':'synthetic-openclaw','model':'fixture/model',
                'openclaw':{'configPath':str(host),'configSha256':hashlib.sha256(host.read_bytes()).hexdigest()}}

    def test_openclaw_migration_includes_host_identity_and_retains_history(self):
        candidate=json.loads(self.old.read_text());candidate['runtime']=self.openclaw_candidate()
        self.new.write_text(json.dumps(candidate));before=self.view()
        with patch('subprocess.Popen',side_effect=AssertionError('migration must not run CLI')):
            plan=self.plan();self.execute(plan)
        after=self.view();self.assertEqual(before['jobs'],after['jobs']);self.assertEqual(before['outbox'],after['outbox'])
        binding=json.loads(dict(after['meta'])['binding'])
        self.assertEqual(binding[3]['configSha256'],candidate['runtime']['openclaw']['configSha256'])
        self.assertEqual(binding[3]['agentId'],'main')

    def test_openclaw_host_change_still_requires_native_new(self):
        candidate=json.loads(self.old.read_text());candidate['runtime']=self.openclaw_candidate()
        self.new.write_text(json.dumps(candidate));self.execute(self.plan());self.old.write_text(json.dumps(candidate))
        candidate['runtime']=self.openclaw_candidate('host-v2');self.new.write_text(json.dumps(candidate))
        self.mutate('INSERT INTO meta VALUES("session_id","synthetic-active-session")')
        with self.assertRaisesRegex(ValueError,'explicit_new_required'):self.plan()
        self.mutate('DELETE FROM meta WHERE key="session_id"')
        self.mutate('UPDATE jobs SET command="ordinary task" WHERE id="3"')
        with self.assertRaisesRegex(ValueError,'completed_new'):self.plan()
        self.mutate('UPDATE jobs SET command="new" WHERE id="3"')
        self.mutate('UPDATE meta SET value="2" WHERE key="generation"')
        self.execute(self.plan())
        self.assertIn('runtime_binding_history/2',dict(self.view()['meta']))

    def view(self):
        with closing(sqlite3.connect(self.database)) as db:
            return migration.ledger_view(db)

    def execute(self, plan):
        with closing(sqlite3.connect(self.database)) as db:
            return migration.apply_transaction(db, plan, 12345)

    def mutate(self, query, args=()):
        with closing(sqlite3.connect(self.database)) as db:
            db.execute(query, args)
            db.commit()

    def test_plan_read_only_and_apply_preserves_all_history(self):
        before = self.view()
        configs = (self.old.read_bytes(), self.new.read_bytes())
        with patch('subprocess.Popen', side_effect=AssertionError('no process')):
            plan = self.plan()
            self.assertEqual(before, self.view())
            key = self.execute(plan)
        after = self.view()
        self.assertEqual(before['jobs'], after['jobs'])
        self.assertEqual(before['outbox'], after['outbox'])
        oldmeta, newmeta = dict(before['meta']), dict(after['meta'])
        self.assertEqual(newmeta.pop('binding'), plan['newBinding'])
        audit = json.loads(newmeta.pop(key))
        oldmeta.pop('binding')
        self.assertEqual(oldmeta, newmeta)
        self.assertEqual(audit['from'], plan['oldBinding'])
        self.assertEqual(configs, (self.old.read_bytes(), self.new.read_bytes()))

    def test_runtime_or_scope_change_cannot_skip_explicit_new(self):
        for key in ['session_id', 'session_contract']:
            self.mutate('INSERT INTO meta VALUES(?,?)', (key, 'private-original'))
            before = self.view()
            with self.assertRaisesRegex(ValueError, 'explicit_new'):
                self.plan()
            self.assertEqual(before, self.view())
            self.mutate('DELETE FROM meta WHERE key=?', (key,))
        self.mutate('UPDATE jobs SET command="ordinary task" WHERE id="3"')
        with self.assertRaisesRegex(ValueError, 'completed_new'):
            self.plan()

    def test_busy_jobs_and_unknown_deliveries_preserved_and_refused(self):
        for state in ['queued', 'running', 'waiting_media']:
            self.mutate('UPDATE jobs SET state=? WHERE id="1"', (state,))
            with self.assertRaisesRegex(ValueError, 'unfinished_jobs'):
                self.plan()
        self.mutate('UPDATE jobs SET state="completed" WHERE id="1"')
        for state in ['pending', 'submitted', 'outcome_unknown', 'upload_unknown']:
            self.mutate('UPDATE outbox SET state=? WHERE key="old-confirmed"', (state,))
            before = self.view()
            with self.assertRaisesRegex(ValueError, 'unconfirmed_outbox'):
                self.plan()
            self.assertEqual(before, self.view())

    def test_stale_ledger_and_wrong_binding_refused(self):
        plan = self.plan()
        self.mutate('UPDATE jobs SET error="new observation" WHERE id="2"')
        before = self.view()
        with self.assertRaisesRegex(ValueError, 'ledger_changed'):
            self.execute(plan)
        self.assertEqual(before, self.view())
        self.mutate('UPDATE meta SET value="different" WHERE key="binding"')
        with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
            self.plan()

    def test_atomic_failure_rolls_back_audit_and_binding(self):
        plan = self.plan()
        self.mutate('CREATE TRIGGER reject_binding BEFORE UPDATE ON meta WHEN NEW.key="binding" BEGIN SELECT RAISE(ABORT,"synthetic failure"); END')
        before = self.view()
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'synthetic failure'):
            self.execute(plan)
        self.assertEqual(before, self.view())

    def test_same_plan_cannot_be_reapplied(self):
        plan = self.plan()
        self.execute(plan)
        before = self.view()
        with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
            self.execute(plan)
        self.assertEqual(before, self.view())

    def test_only_runtime_fields_may_change_and_missing_db_not_created(self):
        candidate = json.loads(self.new.read_text())
        candidate['allowedSenderIds'] = ['different']
        self.new.write_text(json.dumps(candidate))
        with self.assertRaisesRegex(ValueError, 'only_runtime'):
            self.plan()
        candidate['allowedSenderIds'] = self.settings['allowedSenderIds']
        self.new.write_text(json.dumps(candidate))
        self.database.rename(self.database.with_suffix('.preserved'))
        with self.assertRaises(sqlite3.OperationalError):
            self.plan()
        self.assertFalse(self.database.exists())

    def test_unknown_or_running_owner_and_nonlocal_plan_refused(self):
        class FakeManager:
            status = 'running'
            def read_state(inner):
                return {'components': [{'module': 'dingtalk_bridge.agent_gateway', 'config': str(self.new)}]}
            def component_status(inner, record):
                return inner.status
        manager = FakeManager()
        for status in ['running', 'ownership_mismatch']:
            manager.status = status
            with self.assertRaisesRegex(ValueError, 'must_be_stopped'):
                migration.require_stopped(manager, self.new)
        manager.status = 'stopped'
        migration.require_stopped(manager, self.new)
        with self.assertRaisesRegex(ValueError, 'stay_local'):
            migration.private_path(self.root, self.root / 'public-plan.json')

    def test_cli_plan_then_apply_records_receipt_and_never_spawns(self):
        planfile = self.root / 'local/plan.json'
        class FakeManager:
            def __init__(inner, root):
                pass
            def locked(inner):
                return nullcontext()
            def read_state(inner):
                return {'components': [{'module': 'dingtalk_bridge.agent_gateway', 'config': str(self.new)}]}
            def component_status(inner, record):
                return 'stopped'
        args = ['migrate', '--root', str(self.root), '--plan', str(planfile)]
        with patch.object(migration, 'Manager', FakeManager), patch('subprocess.Popen', side_effect=AssertionError('no process')), redirect_stdout(io.StringIO()) as output:
            with patch.object(sys, 'argv', args + ['--from-config', str(self.old), '--to-config', str(self.new)]):
                migration.main()
            before = self.view()
            self.assertFalse(Path(str(planfile) + '.receipt.json').exists())
            with patch.object(sys, 'argv', args + ['--apply']):
                migration.main()
            self.assertEqual(before['jobs'], self.view()['jobs'])
            receipt = json.loads(Path(str(planfile) + '.receipt.json').read_text())
            self.assertEqual(receipt['state'], 'completed')
            self.assertFalse(receipt['automaticStart'])
            with patch.object(sys, 'argv', args + ['--apply']), self.assertRaisesRegex(ValueError, 'binding_mismatch'):
                migration.main()
        self.assertNotIn('synthetic-profile', output.getvalue())

    def test_config_bytes_change_invalidates_plan_with_same_ledger(self):
        plan = self.plan()
        self.new.write_text(self.new.read_text() + '\n')
        self.assertNotEqual(plan, self.plan())
        self.assertEqual(plan['ledgerSha256'], self.plan()['ledgerSha256'])


if __name__ == '__main__':
    unittest.main()

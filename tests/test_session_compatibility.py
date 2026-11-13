"""Compatibility gates preserve durable history and never replay refused jobs."""
import json
from pathlib import Path
import tempfile
import unittest
from dingtalk_bridge.agent_gateway import Gateway,session_contract,contract_json
from test_agent_gateway import SETTINGS,FakeAPI,FakeRuntime
from test_routing_consumer import CFG,event


class SessionCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.api=FakeAPI();self.runtime=FakeRuntime();self.settings={**SETTINGS,'runtime':dict(SETTINGS['runtime'])}
        self.g=Gateway(self.root,CFG,None,self.settings,self.api,self.runtime)
    def tearDown(self):self.g.close();self.tmp.cleanup()
    def task(self,text):
        self.api.events.append(event(len(self.api.events)+1,text='/agent '+text,sender='self'))
        self.g.intake();self.assertTrue(self.g.execute_one());self.g.flush()
    def meta(self):return dict(self.g.db.execute('SELECT key,value FROM meta'))
    def restart(self,settings=None):
        self.g.close();self.g=Gateway(self.root,CFG,None,settings or self.settings,self.api,self.runtime)

    def test_session_and_each_run_contract_survive_restart(self):
        self.task('first');first=self.meta();first_row=dict(self.g.db.execute('SELECT * FROM jobs').fetchone())
        self.restart();self.task('second')
        self.assertEqual(self.runtime.sessions,[None,'native-session'])
        self.assertEqual(self.meta()['session_contract'],first['session_contract'])
        self.assertEqual(dict(self.g.db.execute('SELECT * FROM jobs WHERE seq=1').fetchone()),first_row)
        contexts=[json.loads(r[0]) for r in self.g.db.execute('SELECT runtime_context FROM jobs ORDER BY seq')]
        self.assertEqual([x['sessionId'] for x in contexts],[None,'native-session'])
        self.assertEqual(contexts[0]['contract'],contexts[1]['contract'])

    def test_deadline_and_routing_prompt_changes_do_not_invalidate_session(self):
        self.task('first')
        settings={**self.settings,'prefix':'/agent','runtime':{**self.settings['runtime'],'timeoutSeconds':90}}
        self.restart(settings);self.task('a different task')
        self.assertEqual(self.runtime.sessions,[None,'native-session'])
        self.assertEqual(self.g.summary()['jobs'],{'completed':2})

    def test_model_change_blocks_before_tools_keeps_history_and_new_is_explicit(self):
        self.task('first');old=self.meta();old_job=dict(self.g.db.execute('SELECT * FROM jobs').fetchone())
        old_out=[dict(r) for r in self.g.db.execute('SELECT * FROM outbox')]
        settings={**self.settings,'runtime':{**self.settings['runtime'],'model':'different-model'}}
        self.restart(settings);self.task('do not execute')
        self.assertEqual(self.runtime.calls,1);self.assertEqual(self.meta(),old)
        row=self.g.db.execute('SELECT * FROM jobs WHERE seq=2').fetchone()
        self.assertEqual((row['state'],row['error']),('blocked','runtime_session_contract_changed'))
        self.assertEqual(json.loads(row['runtime_context'])['contract']['model'],'different-model')
        self.assertEqual(dict(self.g.db.execute('SELECT * FROM jobs WHERE seq=1').fetchone()),old_job)
        self.assertEqual([dict(r) for r in self.g.db.execute('SELECT * FROM outbox LIMIT 3')],old_out)
        self.assertFalse((self.g.local/'runs'/row['id']).exists())
        self.restart(settings);self.g.intake();self.assertFalse(self.g.execute_one())
        self.task('new');self.assertNotIn('session_id',self.meta())
        history=json.loads(self.meta()['session_history/0'])
        self.assertEqual(history['sessionId'],'native-session');self.assertEqual(history['contract'],json.loads(old['session_contract']))
        self.task('new task');self.assertEqual(self.runtime.sessions,[None,None])
        self.assertEqual(self.meta()['generation'],'1')
        self.assertTrue((self.g.local/'workspaces/0/exports/report.txt').exists())
        self.assertEqual(self.g.db.execute('SELECT state FROM jobs WHERE seq=2').fetchone()[0],'blocked')

    def test_office_tool_contract_change_is_not_silent_resume(self):
        self.task('first');old=self.meta()
        self.restart({**self.settings,'officialDwsTools':True});self.task('office task')
        self.assertEqual(self.runtime.calls,1);self.assertEqual(self.meta(),old)
        self.assertEqual(self.g.db.execute('SELECT error FROM jobs WHERE seq=2').fetchone()[0],
                         'runtime_session_contract_changed')

    def test_legacy_unknown_contract_is_preserved_and_not_automatically_blessed(self):
        with self.g.db:self.g.db.execute('INSERT INTO meta VALUES("session_id","legacy")')
        before=self.meta();self.task('blocked legacy')
        self.assertEqual(self.runtime.calls,0);self.assertEqual(self.meta(),before)
        row=self.g.db.execute('SELECT * FROM jobs').fetchone()
        self.assertEqual(row['error'],'runtime_session_contract_missing')
        self.assertIsNotNone(row['runtime_context'])
        self.task('new');self.task('fresh task')
        self.assertEqual(self.runtime.sessions,[None])
        self.assertEqual(json.loads(self.meta()['session_history/0']),{'sessionId':'legacy','contract':None})

    def test_reviewed_legacy_contract_preserves_session_without_replaying_old_job(self):
        self.task('old job')
        with self.g.db:self.g.db.execute('DELETE FROM meta WHERE key="session_contract"')
        self.restart();self.g.intake();self.assertFalse(self.g.execute_one())
        # An offline migration can seed only the reviewed old descriptor. The
        # gateway never fabricates it from whatever settings happen to load now.
        with self.g.db:self.g.db.execute('INSERT INTO meta VALUES("session_contract",?)',
                                        (contract_json(session_contract(self.settings)),))
        self.task('next job');self.assertEqual(self.runtime.sessions,[None,'native-session'])
        self.assertEqual(self.runtime.calls,2)

    def test_adapter_cannot_overwrite_previous_session_or_stage_outputs(self):
        self.task('first');before=self.meta()
        def wrong(prompt,workspace,run_dir,session,cancel,remember,images):
            (workspace/'exports/partial.txt').write_text('effect exists');remember('wrong-native-session')
            return {'text':'false success','files':['exports/partial.txt']}
        self.runtime.run=wrong;self.task('bad resume')
        self.assertEqual(self.meta(),before)
        self.assertEqual(self.g.db.execute('SELECT error FROM jobs WHERE seq=2').fetchone()[0],'runtime_session_mismatch')
        self.assertTrue((self.g.workspace()/'exports/partial.txt').exists())
        self.assertFalse(any('partial.txt' in str(v) for v in self.api.sends.values()))

    def test_frozen_contract_does_not_follow_adapter_mutation_during_call(self):
        original=self.runtime.run
        def mutate(*args):
            self.g.settings['runtime']['model']='mutated';return original(*args)
        self.runtime.run=mutate;self.task('first')
        self.assertIsNone(json.loads(self.meta()['session_contract'])['model'])
        self.task('second');self.assertEqual(self.runtime.calls,1)
        self.assertEqual(self.g.db.execute('SELECT error FROM jobs WHERE seq=2').fetchone()[0],'runtime_session_contract_changed')

    def test_invalid_saved_contract_is_not_repaired_and_new_preserves_raw_record(self):
        self.task('first')
        with self.g.db:self.g.db.execute('UPDATE meta SET value="broken-json" WHERE key="session_contract"')
        self.task('blocked');self.assertEqual(self.runtime.calls,1)
        self.assertEqual(self.meta()['session_contract'],'broken-json')
        self.task('new');self.task('fresh')
        self.assertEqual(self.runtime.sessions,[None,None])
        self.assertEqual(json.loads(self.meta()['session_history/0'])['invalidContractRaw'],'broken-json')

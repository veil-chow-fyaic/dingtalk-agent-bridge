"""Synthetic local CLI contracts only; never discover an installed runtime or auth."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from dingtalk_bridge.agent_runtime import LocalRuntime, RuntimeFailure, RuntimeStopped, runtime_binding, runtime_manifest
from dingtalk_bridge.agent_gateway import Gateway, session_contract
from dingtalk_bridge.openclaw_runtime import expected_agents, terminal_text

SID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


def configuration():
    return {'agents': expected_agents('fixture/model'), 'plugins': {'enabled': False},
        'env': {'shellEnv': {'enabled': False}}, 'tools': {'allow': ['exec', 'process'],
        'codeMode': False, 'swarm': False, 'exec': {'host': 'gateway', 'security': 'full', 'ask': 'off'},
        'fs': {'workspaceOnly': True}}, 'models': {'mode': 'replace', 'providers': {'fixture': {
        'api': 'openai-completions', 'apiKey': 'synthetic-unused', 'baseUrl': 'http://127.0.0.1:9/v1',
        'models': [{'id': 'model', 'name': 'Fixture'}]}}}}


def envelope(sid=SID):
    return {'payloads': [{'text': 'not the result'}], 'meta': {'agentMeta': {'sessionId': sid},
        'stopReason': 'stop', 'aborted': False, 'completion': {'stopReason': 'stop', 'finishReason': 'stop'},
        'finalAssistantVisibleText': '{"text":"done","files":[]}', 'livenessState': 'working'}}


class OpenClawRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve();self.work = self.root / 'work';self.work.mkdir()
        self.config = self.root / 'host.json';self.config.write_text(json.dumps(configuration()))
        self.settings = {'kind': 'openclaw', 'binary': str(self.root / 'cli'), 'model': 'fixture/model',
                         'timeoutSeconds': 8, 'openclaw': {'configPath': str(self.config),
                         'configSha256': hashlib.sha256(self.config.read_bytes()).hexdigest()}}
        self.sessions = [];self.number = 0

    def save_config(self, value):
        self.config.write_text(json.dumps(value))
        self.settings['openclaw']['configSha256'] = hashlib.sha256(self.config.read_bytes()).hexdigest()

    def runtime(self, body=None, before='', after='', raw=None):
        self.number += 1
        script = ('#!'+sys.executable+'\nimport sys,os,json,time,signal,subprocess\nfrom pathlib import Path\n'
                  'prompt=sys.stdin.read()\n'+before+'\n')
        if raw is None:
            script += 'body='+repr(body or envelope())+'\n'
            script += "body['meta']['agentMeta']['sessionId']=sys.argv[sys.argv.index('--session-id')+1]\n"
            script += 'print(json.dumps(body,indent=2),flush=True)\n'
        else:script += 'sys.stdout.write('+repr(raw)+');sys.stdout.flush()\n'
        script += after+'\n'
        binary = Path(self.settings['binary']);binary.write_text(script);binary.chmod(0o700)
        return LocalRuntime(copy.deepcopy(self.settings))

    def invoke(self, runtime, session=SID, cancel=None):
        return runtime.run('task 中文', self.work, self.root / ('run-'+str(self.number)),
                           session, cancel or threading.Event(), self.sessions.append)

    def test_local_stdin_full_json_and_pre_execution_uuid(self):
        runtime = self.runtime(before="Path('args.json').write_text(json.dumps(sys.argv));Path('input').write_text(prompt)")
        result = self.invoke(runtime, None)
        self.assertEqual(result, {'text': 'done', 'files': []});self.assertEqual(len(self.sessions), 1)
        args = json.loads((self.work/'args.json').read_text())
        self.assertEqual(args[1:5], ['agent', '--local', '--agent', 'main'])
        self.assertEqual(args[args.index('--session-id')+1], self.sessions[0]);self.assertEqual(len(self.sessions[0]),36)
        self.assertEqual(args[-2:], ['--message-file', '-']);self.assertNotIn('--deliver', args)
        self.assertEqual((self.work/'input').read_text(), 'task 中文')

    def test_uuid_remembered_even_if_cli_exits_without_json(self):
        runtime = self.runtime(raw='', after='sys.exit(7)')
        with self.assertRaisesRegex(RuntimeFailure, 'runtime_exit_nonzero'):self.invoke(runtime, None)
        self.assertEqual(len(self.sessions),1)
        self.assertFalse((self.root/'run-1/validated-response.json').exists())

    def test_wrong_uuid_or_short_session_rejected(self):
        with self.assertRaisesRegex(RuntimeFailure, 'runtime_session_mismatch'):
            terminal_text(json.dumps(envelope(OTHER)), SID, 0)
        runtime = self.runtime()
        for value in ('../other', '11111111', '/tmp/session.jsonl'):
            with self.subTest(value=value),self.assertRaisesRegex(RuntimeFailure,'runtime_session_invalid'):
                self.invoke(runtime,value)
        self.assertFalse((self.root/'run-1').exists())

    def test_exit_zero_partial_abort_error_and_unresolved_tool_rejected(self):
        changes = [{'stopReason':'length'}, {'aborted':True}, {'aborted':None}, {'error':{}},
            {'timeoutPhase':'tool_execution'}, {'completion':{'stopReason':'length'}}, {'completion':None},
            {'toolSummary':{'calls':1,'failures':1}}, {'toolSummary':{'failures':0,'unresolvedError':{}}},
            {'toolSummary':{'failures':False}}, {'replayInvalid':'true'},
            {'completion':{'stopReason':'stop','finishReason':'length'}}]
        for change in changes:
            with self.subTest(change=change),self.assertRaisesRegex(RuntimeFailure,'runtime_turn_failed'):
                body=envelope();body['meta'].update(change);terminal_text(json.dumps(body),SID,0)

    def test_missing_stop_or_abort_is_not_completed(self):
        for key in ('stopReason','aborted','completion'):
            with self.subTest(key=key),self.assertRaises(RuntimeFailure):
                body=envelope();body['meta'].pop(key);terminal_text(json.dumps(body),SID,0)

    def test_successful_side_effect_is_deliverable_but_not_replayed(self):
        body=envelope();body['meta'].update(replayInvalid=True,toolSummary={'calls':1,'failures':0,'tools':['exec']})
        runtime=self.runtime(body,before="p=Path('calls');p.write_text(str(int(p.read_text())+1) if p.exists() else '1')")
        self.assertEqual(self.invoke(runtime),{'text':'done','files':[]})
        with self.assertRaisesRegex(RuntimeFailure,'runtime_run_reuse'):self.invoke(runtime)
        self.assertEqual((self.work/'calls').read_text(),'1')

    def test_payload_or_tool_text_cannot_replace_final_assistant(self):
        body=envelope();body['payloads']=[{'text':'{"text":"echo","files":[]}'}]
        body['meta'].pop('finalAssistantVisibleText')
        with self.assertRaisesRegex(RuntimeFailure,'runtime_result_missing'):terminal_text(json.dumps(body),SID,0)

    def test_entire_envelope_duplicate_keys_nonfinite_and_prose_rejected(self):
        raw=json.dumps(envelope())
        for bad in ('prefix '+raw,raw+raw,'[]',raw.replace('"stopReason": "stop"','"stopReason":"length","stopReason":"stop"',1),raw.replace('"working"','NaN')):
            with self.subTest(raw=bad[:40]),self.assertRaisesRegex(RuntimeFailure,'runtime_protocol_invalid'):
                terminal_text(bad,SID,0)

    def test_full_output_must_finish_and_cli_exit_zero(self):
        runtime=self.runtime(after='sys.exit(9)')
        with self.assertRaisesRegex(RuntimeFailure,'runtime_exit_nonzero'):self.invoke(runtime)
        runtime=self.runtime(raw=json.dumps(envelope())+'\n'+json.dumps(envelope()))
        with self.assertRaisesRegex(RuntimeFailure,'runtime_protocol_invalid'):self.invoke(runtime)

    def test_general_result_schema_still_applies(self):
        body=envelope();body['meta']['finalAssistantVisibleText']='{"text":"done"}'
        with self.assertRaisesRegex(ValueError,'runtime_result_schema_invalid'):self.invoke(self.runtime(body))

    def test_no_ambient_env_config_or_profile_and_new_generation_isolated(self):
        runtime=self.runtime()
        with patch.dict('os.environ',{'OPENCLAW_STATE_DIR':'private-old','OPENAI_API_KEY':'private-key','NODE_OPTIONS':'private-hook','BASH_ENV':'private-shell'}):
            first=runtime.openclaw.environment(self.work,dict(__import__('os').environ))
        self.assertNotIn('OPENAI_API_KEY',first);self.assertNotIn('NODE_OPTIONS',first);self.assertNotIn('BASH_ENV',first)
        self.assertNotIn('HOME',first);self.assertNotIn('CODEX_HOME',first)
        self.assertEqual(first['OPENCLAW_CONFIG_PATH'],str(self.config));self.assertEqual(first['DAB_OPENCLAW_WORKSPACE'],str(self.work))
        second=runtime.openclaw.environment(self.root/'new',{})
        for key in ('OPENCLAW_HOME','OPENCLAW_STATE_DIR','XDG_CACHE_HOME','OPENCLAW_PROFILE'):
            self.assertNotEqual(first[key],second[key])
        self.assertEqual(self.config.read_text(),json.dumps(configuration()))

    def test_mutated_or_ambient_config_rejected_before_spawn(self):
        runtime=self.runtime();self.config.write_text('{}')
        with self.assertRaisesRegex(RuntimeFailure,'openclaw_host_config_invalid'):self.invoke(runtime)
        self.assertEqual(self.sessions,[]);self.assertFalse((self.root/'run-1').exists())
        for mutate in (lambda c:c.update(channels={}),lambda c:c['agents']['entries']['main'].update(workspace='/elsewhere'),
                       lambda c:c['plugins'].update(enabled=True),lambda c:c['agents']['entries']['main'].update(runtime={'type':'acp'}),
                       lambda c:c['env'].update(vars={'DAB_OPENCLAW_WORKSPACE':'/other'})):
            with self.subTest(mutation=str(mutate)),self.assertRaisesRegex(RuntimeFailure,'openclaw_host_config_invalid'):
                cfg=configuration();mutate(cfg);self.save_config(cfg);LocalRuntime(self.settings)

    def test_state_symlink_and_existing_ambient_profile_rejected(self):
        runtime=self.runtime();(self.work/'.openclaw-host').symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(RuntimeFailure,'openclaw_host_path_escaped'):self.invoke(runtime)
        (self.work/'.openclaw-host').unlink()
        fake_home=self.root/'os-home';fake_home.mkdir()
        name='dab-host-'+hashlib.sha256(str(self.work).encode()).hexdigest()[:24]
        (fake_home/('.openclaw-'+name)).mkdir()
        with patch('pathlib.Path.home',return_value=fake_home),self.assertRaisesRegex(RuntimeFailure,'openclaw_ambient_profile_exists'):
            self.invoke(runtime)

    def test_nested_includes_and_missing_endpoint_refused_without_reading_target(self):
        for location in ('models', 'request', 'endpoint'):
            with self.subTest(location=location),self.assertRaisesRegex(RuntimeFailure,'openclaw_host_config_invalid'):
                cfg=configuration();provider=cfg['models']['providers']['fixture']
                if location=='models':provider['models'][0]['$include']='/must-not-read.json'
                elif location=='request':provider['request']={'$include':'/must-not-read.json'}
                else:provider.pop('baseUrl')
                self.save_config(cfg);LocalRuntime(self.settings)

    def test_config_under_agent_workspace_rejected(self):
        self.config=self.work/'host.json';self.settings['openclaw']['configPath']=str(self.config);self.save_config(configuration())
        with self.assertRaisesRegex(RuntimeFailure,'openclaw_config_inside_workspace'):self.invoke(self.runtime())

    def test_host_identity_participates_in_binding_and_session_contract(self):
        original=runtime_binding('scope',self.settings);contract=session_contract({'runtime':self.settings})
        other=copy.deepcopy(self.settings);other['openclaw']['configSha256']='f'*64
        self.assertNotEqual(original,runtime_binding('scope',other))
        self.assertNotEqual(contract,session_contract({'runtime':other}))
        legacy={'kind':'pi','binary':'pi'}
        self.assertEqual(runtime_binding('scope',legacy),json.dumps(['scope','pi','pi']))

    def test_gateway_cannot_resume_changed_host_configuration(self):
        route={'accountId':'synthetic-account','profile':'synthetic-profile','group':'synthetic-chat','conversationType':'direct'}
        settings={'allowedSenderIds':['synthetic-sender'],'runtime':self.settings}
        gateway=Gateway(self.root,route,None,settings,api=object(),runtime=object());gateway.close()
        changed=copy.deepcopy(settings);changed['runtime']['openclaw']['configSha256']='f'*64
        with self.assertRaisesRegex(ValueError,'runtime/scope changed'):
            Gateway(self.root,route,None,changed,api=object(),runtime=object())

    def test_images_not_declared(self):
        runtime=self.runtime();self.assertNotIn('image_files',runtime_manifest(self.settings)['capabilities'])
        with self.assertRaisesRegex(RuntimeFailure,'runtime_capability_unsupported'):
            runtime.run('image',self.work,self.root/'images',None,threading.Event(),self.sessions.append,['image.png'])

    def test_cancel_requests_native_interrupt_before_group_cleanup(self):
        cancel=threading.Event()
        runtime=self.runtime(raw='',before="signal.signal(signal.SIGINT,lambda *_:(Path('native-stop').touch(),sys.exit(130)));Path('ready').touch();time.sleep(20)")
        def request():
            limit=time.monotonic()+5
            while not (self.work/'ready').exists() and time.monotonic()<limit:time.sleep(.01)
            cancel.set()
        thread=threading.Thread(target=request);thread.start()
        with self.assertRaisesRegex(RuntimeStopped,'cancelled'):self.invoke(runtime,cancel=cancel)
        thread.join();self.assertTrue((self.work/'native-stop').exists())
        self.assertIn('sent_and_exited',(self.root/'run-1/stderr.log').read_text())

    def test_host_timeout_never_delivers_partial_envelope(self):
        self.settings['timeoutSeconds']=.3
        runtime=self.runtime(raw='{',after='time.sleep(20)')
        with self.assertRaisesRegex(RuntimeStopped,'timeout'):self.invoke(runtime)
        self.assertFalse((self.root/'run-1/validated-response.json').exists())


if __name__=='__main__':unittest.main()

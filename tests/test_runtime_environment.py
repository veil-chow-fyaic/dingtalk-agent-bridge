"""Persisted network settings reach actual children, without touching identities."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from dingtalk_bridge.agent_runtime import LocalRuntime, runtime_environment

class RuntimeEnvironmentTests(unittest.TestCase):
    def test_config_is_reloaded_by_new_runtime_and_reaches_guard_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'provider';cfg=root/'runtime.json'
            binary.write_text('#!'+sys.executable+'\n'+'''import os,json
from pathlib import Path
Path('environment-observed.json').write_text(json.dumps(dict(os.environ)))
print(json.dumps({'role':'assistant','content':'{"text":"done","files":[]}'}))
print(json.dumps({'type':'session.resume_hint','session_id':'synthetic-session'}))
''');binary.chmod(0o700)
            cfg.write_text(json.dumps({'kind':'kimi','binary':str(binary),'timeoutSeconds':5,
                'environment':{'HTTPS_PROXY':'http://127.0.0.1:9876','HTTP_PROXY':None,'NO_PROXY':'example.test'}}))
            inherited={**os.environ,'HTTP_PROXY':'http://stale.test:1','http_proxy':'http://stale.test:2',
                'https_proxy':'http://stale.test:3','CODEX_HOME':'identity-must-stay','SYNTH_AUTH':'keep'}
            with patch.dict(os.environ,inherited,clear=True):
                before=dict(os.environ)
                for n in range(2):
                    work=root/f'work-{n}';work.mkdir()
                    r=LocalRuntime(json.loads(cfg.read_text()))
                    result=r.run('synthetic',work,root/f'run-{n}',None,threading.Event(),lambda _:None)
                    self.assertEqual(result,{'text':'done','files':[]})
                    seen=json.loads((work/'environment-observed.json').read_text())
                    self.assertEqual(seen['HTTPS_PROXY'],seen['https_proxy'])
                    self.assertEqual(seen['HTTPS_PROXY'],'http://127.0.0.1:9876')
                    self.assertNotIn('HTTP_PROXY',seen);self.assertNotIn('http_proxy',seen)
                    self.assertEqual(set(seen['NO_PROXY'].split(',')),{'example.test','localhost','127.0.0.1','::1'})
                    for name in ('HOME','CODEX_HOME','SYNTH_AUTH'):self.assertEqual(seen.get(name),before.get(name))
                self.assertEqual(dict(os.environ),before)

    def test_absent_environment_preserves_legacy_inheritance_without_mutation(self):
        parent={'HOME':'private','https_proxy':'http://original.test','NO_PROXY':'custom'}
        for cfg in ({},{'environment':{}}):
            child=runtime_environment(cfg,parent);self.assertEqual(child,parent);self.assertIsNot(child,parent)
        self.assertEqual(parent,{'HOME':'private','https_proxy':'http://original.test','NO_PROXY':'custom'})

    def test_null_and_empty_clear_both_casings_and_protect_loopback(self):
        child=runtime_environment({'environment':{'ALL_PROXY':None,'HTTPS_PROXY':'','NO_PROXY':None}},
           {'ALL_PROXY':'socks5://old.test:1','all_proxy':'socks5://old.test:2','https_proxy':'http://old.test','NO_PROXY':'old'})
        self.assertEqual(child,{'NO_PROXY':'localhost,127.0.0.1,::1','no_proxy':'localhost,127.0.0.1,::1'})

    def test_invalid_settings_fail_before_spawn_and_do_not_echo_values(self):
        invalid=[None,[],{'HOME':'SECRET'},{'CODEX_HOME':'SECRET'},{'PATH':'SECRET'},
            {'HTTPS_PROXY':12},{'HTTPS_PROXY':'http://SECRET\n'}, {'HTTPS_PROXY':'file:///SECRET'},
            {'HTTPS_PROXY':'https://SECRET:65536'},{'HTTPS_PROXY':'http://SECRET/path'},
            {'HTTPS_PROXY':'http://SECRET?token=secret'},{'HTTPS_PROXY':'http://SECRET#fragment'},
            {'HTTPS_PROXY':'http://SECRET','https_proxy':'http://conflict'}, {'NO_PROXY':'SECRET\x7f'}]
        with patch('dingtalk_bridge.agent_runtime.subprocess.Popen') as spawn:
            for value in invalid:
                with self.subTest(value=value),self.assertRaises(ValueError) as caught:
                    LocalRuntime({'kind':'kimi','binary':'never','environment':value})
                self.assertNotIn('SECRET',str(caught.exception))
            spawn.assert_not_called()

    def test_mutated_configuration_revalidates_before_creating_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);settings={'kind':'kimi','binary':'never'};runtime=LocalRuntime(settings)
            settings['environment']={'DWS_TOKEN':'SECRET'}
            with patch('dingtalk_bridge.agent_runtime.subprocess.Popen') as spawn:
                with self.assertRaisesRegex(ValueError,'runtime_environment_key_not_allowed'):
                    runtime.run('x',root/'work',root/'run',None,threading.Event(),lambda _:None)
                spawn.assert_not_called()
            self.assertFalse((root/'run').exists());self.assertFalse((root/'work').exists())

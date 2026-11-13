"""Real synthetic CLIs exercise completion and resume trust, without providers."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from dingtalk_bridge.agent_runtime import LocalRuntime


class TerminalContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.work=self.root/'work';self.work.mkdir();self.sessions=[]
    def tearDown(self):self.tmp.cleanup()
    def provider(self,events,kind='kimi',before='',after=''):
        binary=self.root/'provider'
        body='import sys,json\nfrom pathlib import Path\n'
        if kind=='codex':body+='sys.stdin.read()\n'
        body+=before+'\n'+''.join('print('+repr(json.dumps(e))+',flush=True)\n' for e in events)+after
        binary.write_text('#!'+sys.executable+'\n'+body);binary.chmod(0o700)
        return LocalRuntime({'kind':kind,'binary':str(binary),'timeoutSeconds':5})
    def invoke(self,r,session=None):
        return r.run('synthetic',self.work,self.root/'run',session,threading.Event(),self.sessions.append)
    def answer(self):return {'role':'assistant','content':'{"text":"done","files":[]}'}
    def codex_file(self):
        return "Path(sys.argv[sys.argv.index('-o')+1]).write_text('{\"text\":\"done\",\"files\":[]}')"

    def test_resumed_kimi_cannot_replace_native_session(self):
        r=self.provider([self.answer(),{'type':'session.resume_hint','session_id':'another'}])
        with self.assertRaises(RuntimeError):self.invoke(r,'original')
        self.assertEqual(self.sessions,[])
        self.assertFalse((self.root/'run/validated-response.json').exists())

    def test_resumed_codex_cannot_replace_native_session(self):
        r=self.provider([{'type':'thread.started','thread_id':'another'},{'type':'turn.completed'}],
                        'codex',self.codex_file())
        with self.assertRaises(RuntimeError):self.invoke(r,'original')
        self.assertEqual(self.sessions,[])

    def test_codex_terminal_with_nonzero_exit_is_not_delivery(self):
        r=self.provider([{'type':'thread.started','thread_id':'original'},{'type':'turn.completed'}],
                        'codex',self.codex_file(), 'sys.exit(7)\n')
        with self.assertRaises(RuntimeError):self.invoke(r)
        self.assertTrue((self.root/'run/response.json').exists())
        self.assertFalse((self.root/'run/validated-response.json').exists())

    def test_previous_attempt_is_never_overwritten_or_accepted(self):
        run=self.root/'run';run.mkdir();(run/'events.jsonl').write_text('old evidence')
        (run/'response.json').write_text('{"text":"stale","files":[]}')
        r=self.provider([{'type':'thread.started','thread_id':'original'},{'type':'turn.completed'}],
                        'codex',"Path('effect').touch()")
        with self.assertRaises(RuntimeError):self.invoke(r)
        self.assertEqual((run/'events.jsonl').read_text(),'old evidence')
        self.assertFalse((self.work/'effect').exists())

    def test_progress_and_zero_exit_are_typed_incomplete(self):
        events=[{'type':'item.completed','item':{'type':'command_execution','aggregated_output':'429 auth failed turn.completed'}},
                {'type':'thread.started','thread_id':'original'}]
        with self.assertRaises(RuntimeError) as e:self.invoke(self.provider(events,'codex',self.codex_file()))
        self.assertEqual(e.exception.code,'runtime_terminal_missing')
        self.assertEqual(e.exception.stage,'process');self.assertFalse(e.exception.retry_safe)
        self.assertFalse((self.root/'run/validated-response.json').exists())

    def test_kimi_assistant_without_terminal_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError,'runtime_terminal_missing'):
            self.invoke(self.provider([self.answer()]))

    def test_kimi_resume_hint_before_answer_is_not_completion(self):
        with self.assertRaisesRegex(ValueError,'runtime_result_missing'):
            self.invoke(self.provider([{'type':'session.resume_hint','session_id':'original'},self.answer()]))

    def test_session_event_requires_valid_id_before_persisting(self):
        for value in (None,'',12,False,{},'bad\nid'):
            with self.subTest(value=value):
                r=self.provider([self.answer(),{'type':'session.resume_hint','session_id':value}])
                with self.assertRaisesRegex(RuntimeError,'runtime_session_invalid'):
                    r.run('x',self.work,self.root/('case-'+str(len(list(self.root.glob('case-*'))))),None,
                          threading.Event(),self.sessions.append)
        self.assertEqual(self.sessions,[])

    def test_conflicting_session_events_preserve_first_only(self):
        r=self.provider([{'type':'thread.started','thread_id':'first'},
                         {'type':'thread.started','thread_id':'second'},{'type':'turn.completed'}],
                        'codex',self.codex_file())
        with self.assertRaisesRegex(RuntimeError,'runtime_session_mismatch'):self.invoke(r)
        self.assertEqual(self.sessions,['first'])

    def test_provider_failure_is_unknown_not_classified_from_prose(self):
        r=self.provider([{'type':'turn.failed','error':{'message':'429 login failed'}}],'codex')
        with self.assertRaises(RuntimeError) as e:self.invoke(r)
        self.assertEqual(e.exception.code,'runtime_turn_failed')
        self.assertEqual(e.exception.stage,'unknown');self.assertFalse(e.exception.retry_safe)

    def test_codex_completion_without_file_is_result_failure(self):
        r=self.provider([{'type':'thread.started','thread_id':'original'},{'type':'turn.completed'}],'codex')
        with self.assertRaisesRegex(ValueError,'runtime_result_missing'):self.invoke(r)

    def test_conflicting_terminal_in_one_batch_cannot_deliver(self):
        batch='\n'.join(json.dumps(e) for e in [
            {'type':'thread.started','thread_id':'original'},
            {'type':'turn.completed'},{'type':'turn.failed'}])+'\n'
        r=self.provider([],'codex',self.codex_file(), 'sys.stdout.write('+repr(batch)+');sys.stdout.flush()\n')
        with self.assertRaisesRegex(RuntimeError,'runtime_turn_failed'):self.invoke(r)
        self.assertFalse((self.root/'run/validated-response.json').exists())

    def test_matching_resume_and_tool_output_errors_can_succeed(self):
        r=self.provider([{'type':'thread.started','thread_id':'original'},
                         {'type':'item.completed','item':{'aggregated_output':'auth failed 429'}},
                         {'type':'turn.completed'}],'codex',self.codex_file())
        self.assertEqual(self.invoke(r,'original'),{'text':'done','files':[]})
        self.assertEqual(self.sessions,['original'])

    def test_capabilities_are_static_and_missing_support_refuses_before_spawn(self):
        from dingtalk_bridge.agent_runtime import runtime_manifest
        for kind in ('kimi','codex'):
            manifest=runtime_manifest({'kind':kind})
            self.assertEqual(manifest['health'],'unknown')
            self.assertNotIn('healthy',manifest);self.assertIn('workspace_files',manifest['capabilities'])
        with patch('dingtalk_bridge.agent_runtime.subprocess.Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'runtime_capability_unsupported'):
                LocalRuntime({'kind':'kimi','binary':'never','requiredCapabilities':['native_image_arguments']})
            r=LocalRuntime({'kind':'kimi','binary':'never'})
            r.settings['requiredCapabilities']=['invented_feature']
            with self.assertRaisesRegex(RuntimeError,'runtime_capability_unsupported'):self.invoke(r)
        spawn.assert_not_called();self.assertFalse((self.root/'run').exists())

    def test_kimi_images_are_explicit_workspace_inputs_not_native_flags(self):
        from dingtalk_bridge.agent_runtime import runtime_manifest
        manifest=runtime_manifest({'kind':'kimi'})
        self.assertEqual(manifest['imageInput'],'workspace-file')
        self.assertNotIn('native_image_arguments',manifest['capabilities'])
        r=self.provider([self.answer(),{'type':'session.resume_hint','session_id':'original'}])
        self.assertEqual(self.invoke(r,'original')['text'],'done')

"""Pi wire/owned-process contract, synthetic CLIs only; no provider or credentials."""
import json
from pathlib import Path
import sys,tempfile,threading,time,unittest
from dingtalk_bridge.agent_runtime import LocalRuntime,RuntimeFailure,RuntimeStopped,runtime_manifest
SID='11111111-1111-4111-8111-111111111111'
OTHER='22222222-2222-4222-8222-222222222222'
def header(sid=SID):return {'type':'session','version':3,'id':sid}
def answer(text='{"text":"done","files":[]}',reason='stop',role='assistant'):
 return {'type':'message_end','message':{'role':role,'stopReason':reason,'content':[{'type':'text','text':text}]}}
def settled(**kw):return {'type':'agent_settled',**kw}
class PiRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.work=self.root/'work';self.work.mkdir();self.sessions=[];self.n=0
 def runtime(self,events,before='',after='',timeout=5):
  self.n+=1;binary=self.root/f'pi-{self.n}';binary.write_text('#!'+sys.executable+'\nimport json,sys,time,os,signal\nfrom pathlib import Path\nprompt=sys.stdin.read()\n'+before+'\n'+''.join('print('+repr(json.dumps(e,ensure_ascii=False))+',flush=True)\n' for e in events)+after);binary.chmod(0o700)
  return LocalRuntime({'kind':'pi','binary':str(binary),'timeoutSeconds':timeout})
 def invoke(self,r,session=None,cancel=None):return r.run('task',self.work,self.root/f'run-{self.n}',session,cancel or threading.Event(),self.sessions.append)
 def test_manifest_and_command_use_isolated_sessions_no_discovery(self):
  r=self.runtime([]);run=self.root/'command';run.mkdir();args=r.command(self.work,run,SID);self.assertEqual(args[1:4],['--mode','json','--print']);self.assertEqual(args[args.index('--session-dir')+1],str(self.work/'.pi-sessions'));self.assertIn('--no-extensions',args);self.assertIn('--no-skills',args);self.assertIn('--no-prompt-templates',args);self.assertIn('--no-themes',args);self.assertEqual(args[args.index('--session')+1],SID);self.assertNotIn('native_image_arguments',runtime_manifest(r.settings)['capabilities']);self.assertNotIn('image_files',runtime_manifest(r.settings)['capabilities'])
 def test_actual_json_pipeline_and_existing_session(self):
  result=self.invoke(self.runtime([header(),answer(),settled()],before="Path('input.txt').write_text(prompt)"),SID);self.assertEqual(result,{'text':'done','files':[]});self.assertEqual(self.sessions,[SID]);self.assertEqual((self.work/'input.txt').read_text(),'task')
 def test_agent_end_is_not_settled(self):
  with self.assertRaisesRegex(RuntimeFailure,'runtime_terminal_missing'):self.invoke(self.runtime([header(),answer(),{'type':'agent_end'}]))
 def test_retry_error_then_final_answer_only_at_settlement(self):
  r=self.runtime([header(),answer(reason='error'),{'type':'agent_end','willRetry':True},{'type':'auto_retry_start'},answer(),{'type':'agent_end','willRetry':False},settled()]);self.assertEqual(self.invoke(r)['text'],'done')
 def test_abort_error_length_tool_tail_rejected(self):
  for reason in ('aborted','error','length','toolUse',None):
   with self.subTest(reason=reason),self.assertRaisesRegex(RuntimeFailure,'runtime_turn_failed'):self.invoke(self.runtime([header(),answer(reason=reason),settled()]))
 def test_explicit_abort_settlement_rejected(self):
  with self.assertRaisesRegex(RuntimeFailure,'runtime_turn_failed'):self.invoke(self.runtime([header(),answer(),settled(aborted=True)]))
 def test_tool_output_cannot_supply_final_answer(self):
  with self.assertRaisesRegex(RuntimeFailure,'runtime_turn_failed'):self.invoke(self.runtime([header(),answer(role='toolResult'),settled()]))
 def test_no_session_or_wrong_session_cannot_deliver(self):
  with self.assertRaisesRegex(RuntimeFailure,'runtime_session_missing'):self.invoke(self.runtime([answer(),settled()]))
  with self.assertRaisesRegex(RuntimeFailure,'runtime_session_mismatch'):self.invoke(self.runtime([header(OTHER),answer(),settled()]),SID)
  self.assertEqual(self.sessions,[])
 def test_session_path_or_prefix_rejected_before_spawn(self):
  for value in ('../outside','11111111','/tmp/session.jsonl'):
   with self.subTest(value=value),self.assertRaisesRegex(RuntimeFailure,'runtime_session_invalid'):self.invoke(self.runtime([],before="Path('bad').touch()"),value)
  self.assertFalse((self.work/'bad').exists())
 def test_nonzero_exit_after_settlement_rejected(self):
  with self.assertRaisesRegex(RuntimeFailure,'runtime_exit_nonzero'):self.invoke(self.runtime([header(),answer(),settled()],after='sys.exit(4)\n'))
 def test_new_turn_after_terminal_cannot_be_ignored(self):
  with self.assertRaisesRegex(RuntimeFailure,'runtime_terminal_conflict'):self.invoke(self.runtime([header(),answer(),settled(),{'type':'agent_start'}]))
 def test_strict_lf_preserves_unicode_separators(self):
  text='one\u2028two\u2029three';r=self.runtime([header(),answer(json.dumps({'text':text,'files':[]},ensure_ascii=False)),settled()]);self.assertEqual(self.invoke(r)['text'],text)
 def test_bad_json_non_object_and_unterminated_terminal_rejected(self):
  for trailing,code in [('print("bad json",flush=True)','runtime_protocol_invalid'),('print("[]",flush=True)','runtime_protocol_invalid'),('sys.stdout.write('+repr(json.dumps(settled()))+');sys.stdout.flush()','runtime_protocol_unterminated')]:
   with self.subTest(code=code),self.assertRaisesRegex(RuntimeFailure,code):self.invoke(self.runtime([header(),answer()],after=trailing+'\n'))
 def test_invalid_result_schema_rejected(self):
  with self.assertRaisesRegex(ValueError,'runtime_result_schema_invalid'):self.invoke(self.runtime([header(),answer('{"text":"done"}'),settled()]))
 def test_malformed_message_and_duplicate_session_are_classified(self):
  for message in (None,[],"not an object"):
   with self.subTest(message=message),self.assertRaisesRegex(RuntimeFailure,'runtime_protocol_invalid'):self.invoke(self.runtime([header(),{'type':'message_end','message':message},settled()]))
  with self.assertRaisesRegex(RuntimeFailure,'runtime_session_duplicate'):self.invoke(self.runtime([header(),header(),answer(),settled()]))
 def test_images_require_an_explicit_future_capability(self):
  r=self.runtime([]);self.assertEqual(runtime_manifest(r.settings)['imageInput'],'unsupported')
  with self.assertRaisesRegex(RuntimeFailure,'runtime_capability_unsupported'):r.command(self.work,self.root,None,images=[self.root/'image.png'])
  with self.assertRaisesRegex(RuntimeFailure,'runtime_capability_unsupported'):LocalRuntime({**r.settings,'requiredCapabilities':['image_files']})
 def test_cancellation_stops_owned_cli(self):
  cancel=threading.Event();r=self.runtime([header()],before="Path('started').touch()",after='time.sleep(10)\n')
  def request():
   deadline=time.monotonic()+4
   while not(self.work/'started').exists() and time.monotonic()<deadline:time.sleep(.01)
   cancel.set()
  t=threading.Thread(target=request);t.start()
  with self.assertRaisesRegex(RuntimeStopped,'cancelled'):self.invoke(r,cancel=cancel)
  t.join();self.assertFalse((self.root/f'run-{self.n}/validated-response.json').exists())
 def test_timeout_without_settled_not_success(self):
  with self.assertRaisesRegex(RuntimeStopped,'timeout'):self.invoke(self.runtime([header(),answer()],after='time.sleep(10)\n',timeout=.5))

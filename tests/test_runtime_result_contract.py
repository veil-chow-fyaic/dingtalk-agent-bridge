"""Runtime-neutral result failures must preserve effects without dispatch/replay."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.agent_runtime import LocalRuntime,RuntimeResultError,decode_runtime_result
from test_agent_gateway import SETTINGS,FakeAPI,FakeRuntime
from test_routing_consumer import CFG,event


class RuntimeResultContractTests(unittest.TestCase):
    def test_exact_json_and_whole_fenced_result_preserve_unicode(self):
        result={'text':'中文\n🙂','files':['exports/结果.txt']}
        body=json.dumps(result,ensure_ascii=False)
        for text in (body,' \n'+body+'\n ','```json\n'+body+'\n```','```\n'+body+'\n```'):
            with self.subTest(text=text):self.assertEqual(decode_runtime_result(text),result)

    def test_missing_response_is_classified_without_retry_permission(self):
        for value in (None,'',' \n',False,{}):
            with self.subTest(value=value),self.assertRaises(RuntimeResultError) as caught:
                decode_runtime_result(value)
            self.assertEqual(caught.exception.code,'runtime_result_missing')
            self.assertEqual(caught.exception.stage,'result');self.assertFalse(caught.exception.retry_safe)

    def test_prose_prompt_echo_and_multiple_objects_are_not_extracted(self):
        body='{"text":"done","files":[]}'
        for text in ('已处理。\n\n'+body,body+'\nadditional text',body+body,
                     'User request: return '+body+'.','```json\n'+body+'\n```\nextra',
                     '```python\n'+body+'\n```','```json\n'+body):
            with self.subTest(text=text),self.assertRaisesRegex(RuntimeResultError,'runtime_result_invalid_json'):
                decode_runtime_result(text)

    def test_duplicate_keys_and_non_json_constants_cannot_choose_a_result(self):
        for text in ('{"text":"a","text":"b","files":[]}',
                     '{"text":"a","files":[],"files":["exports/unreviewed"]}',
                     '{"text":"a","files":[],"extra":NaN}',
                     '{"text":"a","files":[Infinity]}'):
            with self.subTest(text=text),self.assertRaisesRegex(RuntimeResultError,'runtime_result_invalid_json'):
                decode_runtime_result(text)

    def test_exact_adapter_schema_and_artifact_limit(self):
        for value in ([],None,{'text':'a'},{'files':[]},{'text':5,'files':[]},
                      {'text':'a','files':'exports/x'},{'text':'a','files':[False]},
                      {'text':'a','files':[],'claimedSent':True},
                      {'text':'a','files':['exports/x']*11}):
            with self.subTest(value=value),self.assertRaisesRegex(RuntimeResultError,'runtime_result_schema_invalid'):
                decode_runtime_result(json.dumps(value))
        accepted={'text':'','files':['exports/x']*10}
        self.assertEqual(decode_runtime_result(json.dumps(accepted)),accepted)

    def test_real_terminal_with_prose_keeps_partial_effect_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);workspace=root/'work';workspace.mkdir();run=root/'run'
            body='已完成工具处理。\n\n'+json.dumps({'text':'done','files':['exports/result.txt']})
            provider=root/'provider'
            provider.write_text('#!'+sys.executable+'\nimport json\nfrom pathlib import Path\n'
                'Path("exports").mkdir()\nPath("exports/result.txt").write_text("computed once")\n'
                'with Path("effects").open("a") as f: f.write("one\\n")\n'
                'print(json.dumps({"role":"assistant","content":'+repr(body)+'}),flush=True)\n'
                'print(json.dumps({"type":"session.resume_hint","session_id":"synthetic-session"}),flush=True)\n')
            provider.chmod(0o700);sessions=[]
            runtime=LocalRuntime({'kind':'kimi','binary':str(provider),'timeoutSeconds':10})
            with self.assertRaisesRegex(RuntimeResultError,'runtime_result_invalid_json'):
                runtime.run('synthetic',workspace,run,None,threading.Event(),sessions.append)
            self.assertEqual(sessions,['synthetic-session'])
            self.assertEqual((workspace/'effects').read_text(),'one\n')
            self.assertEqual((workspace/'exports/result.txt').read_text(),'computed once')
            self.assertIn('session.resume_hint',(run/'events.jsonl').read_text())
            self.assertFalse((run/'validated-response.json').exists())

    def test_gateway_rejects_nonlocal_adapter_schema_before_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);api=FakeAPI();runtime=FakeRuntime();original=runtime.run
            def invalid(*args):
                return {**original(*args),'claimedSent':True}
            runtime.run=invalid
            gateway=Gateway(root,CFG,None,SETTINGS,api,runtime)
            try:
                api.events=[event(1,text='/agent invalid result',sender='self')]
                gateway.intake();gateway.execute_one();gateway.flush()
                self.assertEqual(tuple(gateway.db.execute('SELECT state,error,result FROM jobs').fetchone()),
                    ('failed','runtime_result_schema_invalid',None))
                self.assertFalse(any('file' in x or 'image' in x for x in api.sends.values()))
                self.assertEqual((gateway.workspace()/'exports/report.txt').read_text(),'task result')
                gateway.close();gateway=Gateway(root,CFG,None,SETTINGS,api,runtime)
                gateway.intake();gateway.flush();self.assertFalse(gateway.execute_one())
                self.assertEqual(runtime.calls,1)
                runtime.run=original;api.events.append(event(2,text='/agent next legitimate task',sender='self'))
                gateway.intake();self.assertTrue(gateway.execute_one());gateway.flush()
                self.assertEqual(gateway.summary()['jobs'],{'completed':1,'failed':1})
                self.assertEqual(runtime.sessions,[None,'native-session'])
            finally:gateway.close()

    def test_result_failure_notice_preserves_effects_and_does_not_leak_raw_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);api=FakeAPI();runtime=FakeRuntime();calls=[]
            def malformed(prompt,workspace,*args):
                calls.append(prompt);(workspace/'exports/partial.txt').write_text('existing effect')
                raise RuntimeResultError('runtime_result_invalid_json')
            runtime.run=malformed;gateway=Gateway(root,CFG,None,SETTINGS,api,runtime)
            try:
                api.events=[event(1,text='/agent malformed result',sender='self')]
                gateway.intake();gateway.execute_one();gateway.flush()
                notice=next(v['text'] for v in api.sends.values() if '格式无法确认' in v.get('text',''))
                self.assertIn('未自动重做',notice);self.assertIn('可能已生成文件',notice)
                self.assertIn('只读校验和交付',notice)
                self.assertEqual(gateway.db.execute('SELECT error FROM jobs').fetchone()[0],'runtime_result_invalid_json')
                self.assertFalse(any('file' in x or 'image' in x for x in api.sends.values()))
                self.assertFalse(gateway.execute_one());self.assertEqual(len(calls),1)
                self.assertEqual((gateway.workspace()/'exports/partial.txt').read_text(),'existing effect')
            finally:gateway.close()

"""Exercise real child processes with deterministic provider events; no model/network calls."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from dingtalk_bridge.agent_runtime import LocalRuntime,RuntimeStopped

class RuntimeProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.workspace=self.root/'workspace';self.workspace.mkdir();self.cancel=threading.Event();self.sessions=[]
    def tearDown(self):self.tmp.cleanup()
    def runtime(self,body,kind='kimi',timeout=10):
        binary=self.root/'provider';binary.write_text('#!'+sys.executable+'\n'+body);binary.chmod(0o700)
        return LocalRuntime({'kind':kind,'binary':str(binary),'timeoutSeconds':timeout})
    def run_provider(self,r):return r.run('synthetic task',self.workspace,self.root/'run',None,self.cancel,self.sessions.append)
    def terminal(self,text='{"text":"完成","files":[]}',newline=True):
        return 'import json,sys\nprint(json.dumps({"role":"assistant","content":'+repr(text)+'}),flush=True)\nprint(json.dumps({"type":"session.resume_hint","session_id":"test-session"}),end='+repr('\n' if newline else '')+',flush=True)\n'
    def test_completed_terminal_without_final_newline(self):
        self.assertEqual(self.run_provider(self.runtime(self.terminal(newline=False)))['text'],'完成')
        self.assertEqual(self.sessions,['test-session'])
    def test_completed_but_lingering_child_is_reaped(self):
        body=self.terminal()+'import os,time\nopen("pid","w").write(str(os.getpid()))\ntime.sleep(30)\n'
        self.run_provider(self.runtime(body))
        if (self.workspace/'pid').exists():
            with self.assertRaises(ProcessLookupError):os.kill(int((self.workspace/'pid').read_text()),0)
    def test_timeout_reaps_child(self):
        import subprocess
        from unittest.mock import patch
        spawned=[];real=subprocess.Popen
        def spawn(*a,**kw):
            child=real(*a,**kw);spawned.append(child);return child
        with patch('dingtalk_bridge.agent_runtime.subprocess.Popen',side_effect=spawn):
            with self.assertRaisesRegex(RuntimeStopped,'timeout'):
                self.run_provider(self.runtime('import time\ntime.sleep(30)\n',timeout=.3))
        self.assertIsNotNone(spawned[0].poll())
        with self.assertRaises(ProcessLookupError):os.kill(spawned[0].pid,0)
    def test_cancel_reaps_child(self):
        timer=threading.Timer(.2,self.cancel.set);timer.start()
        try:
            with self.assertRaisesRegex(RuntimeStopped,'cancelled'):
                self.run_provider(self.runtime('import time\ntime.sleep(30)\n'))
        finally:timer.join()
    def test_invalid_structured_answer_is_rejected(self):
        with self.assertRaises(ValueError):self.run_provider(self.runtime(self.terminal('this is not JSON')))
    def test_partial_artifact_and_prompt_echo_are_not_retried_or_accepted(self):
        body='''from pathlib import Path
Path('exports').mkdir()
Path('exports/partial.txt').write_text('computed once')
with Path('attempts').open('a') as f: f.write('one\n')
'''.replace("'one\n'", "'one\\n'") + self.terminal('User task: imaginary next instruction; return {"text":"example","files":[]}.')
        with self.assertRaises(json.JSONDecodeError):
            self.run_provider(self.runtime(body))
        self.assertEqual((self.workspace/'attempts').read_text(),'one\n')
        self.assertEqual((self.workspace/'exports/partial.txt').read_text(),'computed once')
        self.assertTrue((self.root/'run/events.jsonl').is_file())
        self.assertFalse((self.root/'run/validated-response.json').exists())
    def test_too_many_artifacts_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'artifact'):
            self.run_provider(self.runtime(self.terminal(json.dumps({'text':'x','files':['exports/x']*11}))))
    def test_exit_without_terminal_is_not_success(self):
        with self.assertRaises(RuntimeError):self.run_provider(self.runtime('print("{}")\n'))
    def test_oversized_event_is_bounded(self):
        with self.assertRaisesRegex(ValueError,'Oversized'):
            self.run_provider(self.runtime('import sys\nsys.stdout.write("x"*(4*1024*1024+1));sys.stdout.flush()\n'))
    def test_codex_completed_schema_file_and_session(self):
        body='''import sys,json,pathlib
sys.stdin.read()
pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_text(json.dumps({'text':'codex fixture','files':[]}))
print(json.dumps({'type':'thread.started','thread_id':'codex-fixture'}),flush=True)
print(json.dumps({'type':'turn.completed'}),flush=True)
'''
        self.assertEqual(self.run_provider(self.runtime(body,kind='codex'))['text'],'codex fixture')
        self.assertEqual(self.sessions,['codex-fixture'])
    def test_codex_failed_turn_is_not_success(self):
        with self.assertRaises(RuntimeError):
            self.run_provider(self.runtime('import sys\nsys.stdin.read()\nprint(\'{"type":"turn.failed"}\')\n',kind='codex'))

    def test_codex_stalled_stdin_is_still_cancellable(self):
        runtime=self.runtime('import time\ntime.sleep(30)\n',kind='codex',timeout=.3)
        with self.assertRaisesRegex(RuntimeStopped,'timeout'):
            runtime.run('x'*1000000,self.workspace,self.root/'run',None,self.cancel,self.sessions.append)

    def test_group_signal_race_reaps_owned_child(self):
        from unittest.mock import patch
        body=self.terminal()+'import time\ntime.sleep(30)\n'
        with patch('dingtalk_bridge.agent_runtime.os.killpg',side_effect=PermissionError):
            self.assertEqual(self.run_provider(self.runtime(body))['text'],'完成')

    def forked_tool(self):
        return """import os,signal,time
from pathlib import Path
if os.fork() == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path('child-ready').touch()
    end=time.monotonic()+6
    while not Path('release-child').exists() and time.monotonic()<end: time.sleep(.01)
    if Path('release-child').exists(): Path('late-artifact').write_text('must not run after return')
    os._exit(0)
while not Path('child-ready').exists(): time.sleep(.01)
"""

    def assert_tool_stopped(self):
        import time
        self.assertTrue((self.workspace/'child-ready').exists())
        (self.workspace/'release-child').touch()
        time.sleep(.3)
        self.assertFalse((self.workspace/'late-artifact').exists())

    def test_exited_leader_cannot_leave_a_writing_tool_after_timeout(self):
        body=self.forked_tool()+'os._exit(0)\n'
        with self.assertRaisesRegex(RuntimeStopped,'timeout'):
            self.run_provider(self.runtime(body,timeout=2))
        self.assert_tool_stopped()

    def test_completed_runtime_cleans_term_ignoring_tool_before_return(self):
        body=self.forked_tool()+self.terminal()+'time.sleep(30)\n'
        self.assertEqual(self.run_provider(self.runtime(body))['text'],'完成')
        self.assert_tool_stopped()

    def test_cancel_cleans_tool_and_leaves_unrelated_process_alive(self):
        import subprocess,time
        unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
        def cancel_ready():
            deadline=time.monotonic()+4
            while not (self.workspace/'child-ready').exists() and time.monotonic()<deadline:time.sleep(.01)
            self.cancel.set()
        canceller=threading.Thread(target=cancel_ready);canceller.start()
        try:
            with self.assertRaisesRegex(RuntimeStopped,'cancelled'):
                self.run_provider(self.runtime(self.forked_tool()+'os._exit(0)\n'))
            self.assert_tool_stopped()
            self.assertIsNone(unrelated.poll())
        finally:
            canceller.join();unrelated.terminate();unrelated.wait()

    def test_codex_completed_exit_retains_group_identity_until_cleanup(self):
        body=self.forked_tool()+"""import sys,json
sys.stdin.read()
Path(sys.argv[sys.argv.index('-o')+1]).write_text(json.dumps({'text':'fixture','files':[]}))
print(json.dumps({'type':'thread.started','thread_id':'fixture-session'}),flush=True)
print(json.dumps({'type':'turn.completed'}),flush=True)
os._exit(0)
"""
        self.assertEqual(self.run_provider(self.runtime(body,kind='codex'))['text'],'fixture')
        self.assert_tool_stopped()

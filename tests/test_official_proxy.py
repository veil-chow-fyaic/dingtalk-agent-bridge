"""Runtime-facing official CLI entrypoint, exercised with synthetic executables."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import threading

from dingtalk_bridge.official_tools import prepare, CONTEXT
from dingtalk_bridge.official_proxy import OFFICE_COMMANDS, execute
from dingtalk_bridge.dws_access import DWSAccess, DWSAccessSuspended
from dingtalk_bridge.core import DWS
from dingtalk_bridge.agent_runtime import LocalRuntime

ROOT=Path(__file__).resolve().parents[1]

ERROR={'error':{'category':'internal','code':51,'message':
    'resolve access token: load access token: load from keychain: read DEK from macOS Keychain: private-marker'}}


class OfficialProxyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="办公 wrapper '$ ");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.workspace=self.root/'task workspace';self.workspace.mkdir()
        self.binary=self.root/'synthetic-dws';self.route={'binary':self.binary.name,'profile':'synthetic-corp:synthetic-user'}

    def program(self, body, timeout=600):
        self.binary.write_text('#!'+sys.executable+'\n'+body);self.binary.chmod(0o700)
        prepare(self.root,self.workspace,self.route,{'officialDwsTools':True,'runtime':{'timeoutSeconds':timeout}})
        self.entry=Path(json.loads((self.workspace/CONTEXT).read_text())['binary'])

    def invoke(self, *args):
        return subprocess.run([str(self.entry),*args],cwd=self.workspace,capture_output=True,timeout=15)

    def test_runtime_context_cannot_automatically_repeat_credential_reads(self):
        self.program("from pathlib import Path\nimport sys\nwith Path('calls').open('a') as f:f.write('call\\n')\nprint("+
                     repr(json.dumps(ERROR))+",file=sys.stderr)\nraise SystemExit(51)")
        first=self.invoke('doc','--help');second=self.invoke('doc','--help')
        self.assertEqual(first.returncode,51)
        self.assertNotEqual(second.returncode,0)
        self.assertEqual((self.workspace/'calls').read_text(),'call\n')
        self.assertNotIn(b'private-marker',second.stderr)

    def test_passthrough_keeps_bytes_exit_status_working_directory_and_arguments(self):
        self.program("import json,sys,os\nfrom pathlib import Path\nPath('received.json').write_text(json.dumps({'args':sys.argv[1:],'cwd':os.getcwd()}))\nsys.stdout.buffer.write(b'\\xff\\x00raw\\n');sys.stderr.buffer.write(b'\\xfeprivate stderr');raise SystemExit(42)")
        for family in OFFICE_COMMANDS:
            with self.subTest(command=family):
                arguments=[family,'+synthetic','--title',"中文 '\" $literal",'--file','inputs/space name.csv']
                result=self.invoke(*arguments)
                self.assertEqual(result.returncode,42);self.assertEqual(result.stdout,b'\xff\x00raw\n')
                self.assertEqual(result.stderr,b'\xfeprivate stderr')
                received=json.loads((self.workspace/'received.json').read_text())
                self.assertEqual(Path(received['cwd']).resolve(),self.workspace.resolve())
                self.assertEqual(received['args'],arguments+['--profile',self.route['profile'],'--format','json','--as','user'])
        self.assertEqual(DWSAccess(self.root).status()['state'],'ready')

    def test_explicit_identity_is_preserved_and_invalid_requests_never_start_cli(self):
        self.program("import json,sys\nfrom pathlib import Path\nPath('calls').write_text(json.dumps(sys.argv[1:]))\nprint('{}')")
        args=['doc','--help','--profile='+self.route['profile'],'--format=json','--as=user']
        self.assertEqual(self.invoke(*args).returncode,0)
        self.assertEqual(json.loads((self.workspace/'calls').read_text()),args)
        previous=(self.workspace/'calls').read_bytes()
        cases=[[],['auth','login'],['event','consume'],['dev','connect'],['mcp'],['config','set'],
               ['doc','--profile','other:account'],['doc','--profile',self.route['profile'],'--profile='+self.route['profile']],
               ['doc','--format','text'],['doc','--as','app'],['doc','--token=private-marker'],
               ['doc','--client-secret','private-marker'],['doc','--'],['doc','--profile']]
        for args in cases:
            with self.subTest(arguments=args):
                result=self.invoke(*args);self.assertEqual(result.returncode,75)
                self.assertNotIn(b'private-marker',result.stderr)
                self.assertEqual((self.workspace/'calls').read_bytes(),previous)

    def test_invalid_deadline_never_spawns_or_touches_circuit(self):
        for timeout in (0,-1,True,None,'600',float('nan'),float('inf'),10**1000):
            with self.subTest(timeout_type=type(timeout).__name__),self.assertRaisesRegex(ValueError,'invalid_timeout'):
                execute(self.root,'never-spawn',self.route['profile'],['doc','--help'],timeout=timeout)
        self.assertFalse((self.root/'local').exists())

    def test_transport_and_office_share_the_same_root_circuit(self):
        self.program("from pathlib import Path\nimport sys\nwith Path('calls').open('a') as f:f.write('call\\n')\nprint("+
                     repr(json.dumps(ERROR))+",file=sys.stderr)\nraise SystemExit(51)")
        self.assertEqual(self.invoke('doc','--help').returncode,51)
        with self.assertRaises(DWSAccessSuspended):DWS(self.root,self.route).call(['chat','+synthetic'])
        self.assertFalse((self.root/'calls').exists())
        self.assertFalse((self.workspace/'local/runtime').exists())
        DWSAccess(self.root).resume()
        with self.assertRaises(DWSAccessSuspended):DWS(self.root,self.route).call(['chat','+synthetic'])
        self.assertEqual(self.invoke('doc','--help').returncode,75)
        self.assertEqual((self.root/'calls').read_text(),'call\n')
        self.assertEqual((self.workspace/'calls').read_text(),'call\n')

    def alive(self,pid):
        result=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
        return bool(result.stdout.strip()) and not result.stdout.strip().startswith('Z')

    def until(self,predicate,seconds=10):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.025)
        self.fail('Expected synthetic process state did not appear')

    def descendant_program(self,timeout=600):
        child="import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('child.ready').touch();\nwhile not Path('release').exists():time.sleep(.01)\nPath('late-write').touch();time.sleep(30)"
        body=('import subprocess,sys,time\nfrom pathlib import Path\n'
              f'p=subprocess.Popen([sys.executable,"-c",{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
              'Path("child.pid").write_text(str(p.pid))\n'
              'while not Path("child.ready").exists():time.sleep(.01)\n'
              'Path("called").touch()\ntime.sleep(60)')
        self.program(body,timeout)
        def clean():
            path=self.workspace/'child.pid'
            if path.exists() and self.alive(int(path.read_text())):os.kill(int(path.read_text()),signal.SIGKILL)
        self.addCleanup(clean)

    def assert_cleaned(self):
        self.until(lambda:not self.alive(int((self.workspace/'child.pid').read_text())))
        (self.workspace/'release').touch();time.sleep(.25)
        self.assertFalse((self.workspace/'late-write').exists())

    def test_office_timeout_cleans_descendants_and_never_retries(self):
        self.descendant_program(timeout=2)
        result=self.invoke('minutes','+synthetic')
        self.assertEqual(result.returncode,75);self.assertIn(b'dws_timeout',result.stderr)
        self.assertTrue((self.workspace/'called').exists());self.assert_cleaned()
        pid=(self.workspace/'child.pid').read_bytes()
        self.assertEqual(self.invoke('minutes','+synthetic').returncode,75)
        self.assertEqual((self.workspace/'child.pid').read_bytes(),pid)

    def test_wrapper_sigkill_cleans_descendants_and_persists_interruption(self):
        self.descendant_program()
        process=subprocess.Popen([str(self.entry),'doc','+synthetic'],cwd=self.workspace,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            self.until(lambda:(self.workspace/'called').exists())
            process.kill();process.wait(timeout=5);self.assert_cleaned()
            result=self.invoke('doc','+synthetic')
            self.assertEqual(result.returncode,75);self.assertIn(b'dws_process_interrupted',result.stderr)
        finally:
            if process.poll() is None:process.kill();process.wait()

    def test_real_synthetic_runtime_executes_through_generated_context(self):
        self.program("import json,sys\nfrom pathlib import Path\nPath('office-args.json').write_text(json.dumps(sys.argv[1:]))\nprint('{\"ok\":true,\"value\":42}')")
        provider=self.root/'synthetic-runtime'
        provider.write_text('#!'+sys.executable+'''\nimport json,subprocess
from pathlib import Path
context=json.loads(Path('.dab-official-dws.json').read_text())
result=subprocess.run([context['binary'],'doc','+synthetic'],capture_output=True,check=True)
answer=json.loads(result.stdout)
print(json.dumps({'role':'assistant','content':json.dumps({'text':str(answer['value']),'files':[]})}),flush=True)
print(json.dumps({'type':'session.resume_hint','session_id':'synthetic-office-session'}),flush=True)
''');provider.chmod(0o700)
        runtime=LocalRuntime({'kind':'kimi','binary':str(provider),'timeoutSeconds':10})
        result=runtime.run('synthetic office task',self.workspace,self.root/'run',None,threading.Event(),lambda _:None)
        self.assertEqual(result['text'],'42')
        self.assertIn(self.route['profile'],json.loads((self.workspace/'office-args.json').read_text()))

    def test_gateway_sigkill_cleans_runtime_proxy_and_official_descendants(self):
        self.descendant_program()
        provider=self.root/'synthetic-runtime'
        provider.write_text('#!'+sys.executable+'''\nimport json,subprocess
from pathlib import Path
context=json.loads(Path('.dab-official-dws.json').read_text())
subprocess.run([context['binary'],'doc','+synthetic'],check=True)
''');provider.chmod(0o700)
        code=('import threading\nfrom dingtalk_bridge.agent_runtime import LocalRuntime\n'
              f'LocalRuntime({{"kind":"kimi","binary":{str(provider)!r},"timeoutSeconds":60}}).run("synthetic",{str(self.workspace)!r},{str(self.root/"run")!r},None,threading.Event(),lambda _:None)')
        gateway=subprocess.Popen([sys.executable,'-c',code],env={**os.environ,'PYTHONPATH':str(ROOT)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            self.until(lambda:(self.workspace/'called').exists())
            gateway.kill();gateway.wait(timeout=5);self.assert_cleaned()
            self.assertEqual(self.invoke('doc','+synthetic').returncode,75)
        finally:
            if gateway.poll() is None:gateway.kill();gateway.wait()


if __name__=='__main__':unittest.main()

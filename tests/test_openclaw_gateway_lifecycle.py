"""Real bridge/gateway/guard, synthetic OpenClaw protocol and detached tool only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.service_manager import process_identity
from test_agent_gateway import FakeAPI
from test_openclaw_runtime import configuration, envelope
from test_routing_consumer import CFG, event


class OpenClawGatewayLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        config = self.root / 'host.json'
        config.write_text(json.dumps(configuration()))
        self.binary = self.root / 'synthetic-openclaw'
        self.settings = {'allowedSenderIds': ['other'], 'runtime': {
            'kind': 'openclaw', 'binary': str(self.binary), 'model': 'fixture/model',
            'timeoutSeconds': 30, 'openclaw': {'configPath': str(config),
            'configSha256': hashlib.sha256(config.read_bytes()).hexdigest()}}}
        self.api = FakeAPI()
        self.g = None
        self.write_cli()
        self.addCleanup(self.close)

    def close(self):
        if self.g is not None:
            self.g.close()
            self.g = None

    def open(self):
        self.g = Gateway(self.root, CFG, None, self.settings, self.api)
        return self.g

    def write_cli(self, partial=False, wait=False):
        body = envelope()
        body['meta']['finalAssistantVisibleText'] = json.dumps({'text': 'synthetic result', 'files': ['exports/report.json']})
        if partial:
            body['meta']['stopReason'] = 'length'
        child = """import os,time,json
from pathlib import Path
Path('tool-ready.json').write_text(json.dumps({'pid':os.getpid(),'at':time.time()}))
deadline=time.monotonic()+20
while not Path('release-tool').exists() and time.monotonic()<deadline:time.sleep(.02)
if Path('release-tool').exists():Path('late').touch()
"""
        wait_code = f"""
tool=subprocess.Popen([sys.executable,'-c',{child!r}],start_new_session=True,
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def interrupt(*_):
    tool.terminate();tool.wait(timeout=3)
    Path('native-stop').touch()
    raise SystemExit(130)
signal.signal(signal.SIGINT,interrupt)
Path('owners.json').write_text(json.dumps({{'cli':os.getpid(),'guard':os.getppid(),'tool':tool.pid}}))
while True:time.sleep(.02)
""" if wait else ''
        script = '#!' + sys.executable + '\n' + f"""import json,os,sys,signal,subprocess,time
from pathlib import Path
prompt=sys.stdin.read()
sid=sys.argv[sys.argv.index('--session-id')+1]
record={{'sid':sid,'state':os.environ['OPENCLAW_STATE_DIR'],'profile':os.environ['OPENCLAW_PROFILE'],'prompt':prompt}}
with Path('calls.jsonl').open('a') as out:out.write(json.dumps(record)+'\\n')
{wait_code}
Path('exports/report.json').write_text(json.dumps({{'value':31*19+4}})+'\\n')
body={body!r}
body['meta']['agentMeta']['sessionId']=sid
print(json.dumps(body,indent=2),flush=True)
"""
        self.binary.write_text(script)
        self.binary.chmod(0o700)

    def dispatch(self, seq, text):
        self.api.events.append(event(seq, text='/agent ' + text))
        self.g.intake()
        self.assertTrue(self.g.execute_one())

    def test_gateway_resume_new_and_lost_receipt_keep_file_and_original_key(self):
        g = self.open()
        self.dispatch(1, 'FIRST')
        work = g.workspace()
        first_meta = dict(g.db.execute('SELECT key,value FROM meta'))
        g.flush()
        self.close()
        g = self.open()
        self.dispatch(2, 'RESUME')
        calls = [json.loads(x) for x in (work / 'calls.jsonl').read_text().splitlines()]
        self.assertEqual([x['sid'] for x in calls], [first_meta['session_id']] * 2)
        old_result = g.db.execute('SELECT result FROM jobs WHERE seq=1').fetchone()[0]
        self.dispatch(3, 'new')
        meta = dict(g.db.execute('SELECT key,value FROM meta'))
        archive = json.loads(meta['session_history/0'])
        self.assertEqual(archive['sessionId'], first_meta['session_id'])
        self.assertEqual(archive['contract'], json.loads(first_meta['session_contract']))
        self.assertEqual(meta['binding'], first_meta['binding'])
        self.assertNotIn('session_id', meta)
        self.assertNotIn('session_contract', meta)
        self.assertEqual(meta['generation'], '1')
        self.dispatch(4, 'FRESH')
        fresh = g.workspace()
        new_call = json.loads((fresh / 'calls.jsonl').read_text())
        for key in ('sid', 'state', 'profile'):
            self.assertNotEqual(new_call[key], calls[0][key])
        self.assertEqual(g.db.execute('SELECT result FROM jobs WHERE seq=1').fetchone()[0], old_result)
        self.assertEqual(len((work / 'calls.jsonl').read_text().splitlines()), 2)
        # Lose a file receipt after the fake transport records it. Restart must
        # re-use exactly that key and payload without re-running the producer.
        original = self.api.__call__
        lost = []
        def send(path, data=None):
            result = original(path, data)
            if path == '/v1/send' and 'file' in data and not lost:
                lost.append(copy.deepcopy(data))
                raise OSError('synthetic lost file receipt')
            return result
        g.api = send
        g.flush()
        self.assertEqual(len(lost), 1)
        self.close()
        g = self.open()
        g.intake()
        self.assertFalse(g.execute_one())
        g.flush()
        self.assertEqual(self.api.sends[lost[0]['idempotency_key']], lost[0])
        self.assertEqual(g.summary()['delivery'], {'confirmed': 7})
        for data in self.api.sends.values():
            if 'file' in data:
                content = (self.root / data['file']).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), data['expected_sha256'])
                self.assertEqual(json.loads(content), {'value': 593})
        self.assertEqual(len((fresh / 'calls.jsonl').read_text().splitlines()), 1)

    def test_partial_turn_keeps_side_effect_but_never_queues_result_or_file(self):
        self.write_cli(partial=True)
        g = self.open()
        self.dispatch(1, 'PARTIAL')
        self.assertTrue((g.workspace() / 'exports/report.json').exists())
        job = dict(g.db.execute('SELECT * FROM jobs').fetchone())
        self.assertEqual((job['state'], job['error'], job['result']), ('failed', 'runtime_turn_failed', None))
        self.assertFalse((g.local / 'runs' / job['id'] / 'validated-response.json').exists())
        g.flush()
        self.assertEqual(len(self.api.sends), 1)
        self.assertTrue(all('file' not in x and 'synthetic result' not in x.get('text', '') for x in self.api.sends.values()))
        self.close()
        g = self.open()
        g.intake()
        self.assertFalse(g.execute_one())
        self.assertEqual(len((g.workspace() / 'calls.jsonl').read_text().splitlines()), 1)

    def test_sigkill_gateway_cleans_detached_tool_and_restart_never_reexecutes(self):
        self.write_cli(wait=True)
        g = self.open()
        work = g.workspace()
        local = g.local
        self.close()
        driver = """import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
from dingtalk_bridge.agent_gateway import Gateway
from test_agent_gateway import FakeAPI
from test_routing_consumer import CFG,event
api=FakeAPI();api.events=[event(1,text='/agent CRASH')]
g=Gateway(Path(sys.argv[3]),CFG,None,json.loads(sys.argv[4]),api)
g.intake();g.execute_one();g.close()
"""
        with (self.root / 'driver.log').open('wb') as log:
            owner = subprocess.Popen([sys.executable, '-c', driver, str(Path(__file__).resolve().parents[1]),
                str(Path(__file__).resolve().parent), str(self.root), json.dumps(self.settings)], stdout=log, stderr=log)
            try:
                limit = time.monotonic() + 10
                while not (work / 'tool-ready.json').exists() or not (work / 'owners.json').exists():
                    self.assertIsNone(owner.poll())
                    self.assertLess(time.monotonic(), limit)
                    time.sleep(.02)
                owners = json.loads((work / 'owners.json').read_text())
                with sqlite3.connect('file:' + str(local / 'tasks.sqlite3') + '?mode=ro', uri=True) as db:
                    before = dict(db.execute('SELECT key,value FROM meta'))
                    self.assertEqual(db.execute('SELECT state FROM jobs').fetchone()[0], 'running')
                self.assertEqual(len(before['session_id']), 36)
                owner.kill()
                self.assertEqual(owner.wait(timeout=5), -9)
                limit = time.monotonic() + 12
                while any(process_identity(pid) for pid in owners.values()):
                    self.assertLess(time.monotonic(), limit)
                    time.sleep(.02)
                self.assertTrue((work / 'native-stop').exists())
                (work / 'release-tool').touch()
                time.sleep(.2)
                self.assertFalse((work / 'late').exists())
            finally:
                if owner.poll() is None:
                    owner.kill()
                    owner.wait(timeout=5)
        self.api.events = [event(1, text='/agent CRASH')]
        for _ in range(2):
            g = self.open()
            g.intake()
            self.assertFalse(g.execute_one())
            g.flush()
            self.assertEqual(tuple(g.db.execute('SELECT state,error,result FROM jobs').fetchone()), ('interrupted', 'process_restart', None))
            self.assertEqual(dict(g.db.execute('SELECT key,value FROM meta'))['session_id'], before['session_id'])
            self.close()
        self.assertEqual(len(self.api.sends), 1)
        self.assertEqual(len((work / 'calls.jsonl').read_text().splitlines()), 1)
        stderr = next((local / 'runs').glob('*/stderr.log')).read_text()
        self.assertIn('gateway_pipe_closed', stderr)
        self.assertIn('sent_and_exited', stderr)
        self.assertFalse(list((local / 'runs').glob('*/validated-response.json')))


if __name__ == '__main__':
    unittest.main()

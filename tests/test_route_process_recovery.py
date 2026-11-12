"""Actual independent processes: route lock contention and crash recovery."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKER = '''
import json,signal,sys
from pathlib import Path
from dingtalk_bridge.core import Bridge,BridgeError
from test_core import CFG,Fake
mode,route=sys.argv[1:];root=Path.cwd();cfg=dict(CFG)
if route=='b':cfg['group']='independent-group'
if mode=='wrong-scope':cfg['profile']='different-profile'
class Provider(Fake):
 def call(self,args):
  if '+messages-send' in args:
   with (root/'provider-sends.ndjson').open('a') as out:out.write(json.dumps({'route':route,'key':args[args.index('--idempotency-key')+1]})+'\\n')
   if mode=='uncertain':
    print(json.dumps({'ready':True,'phase':'send_entered','state':bridge.delivery('stable')['state']}),flush=True)
    signal.pause()
  return super().call(args)
provider=Provider()
try:bridge=Bridge(root,cfg,provider,state_name=route*64)
except BridgeError as error:
 print(json.dumps({'rejected':True,'error':str(error),'sends':provider.sent}));raise SystemExit(0)
if mode in ('confirmed','uncertain'):
 bridge.sync();bridge.send('stable',text='synthetic task')
 print(json.dumps({'ready':True,'phase':'confirmed','state':bridge.delivery('stable')['state']}),flush=True)
 signal.pause()
elif mode=='probe':
 print(json.dumps({'rejected':False,'events':bridge.db.execute('SELECT count(*) FROM events').fetchone()[0],'deliveries':bridge.db.execute('SELECT count(*) FROM deliveries').fetchone()[0],'sends':provider.sent}))
else:
 before=bridge.delivery('stable');result=bridge.send('stable',text='synthetic task')
 mismatch=False
 try:bridge.send('stable',text='different task')
 except ValueError:mismatch=True
 print(json.dumps({'before':before,'result':result,'sends':provider.sent,'mismatchRejected':mismatch,'events':bridge.db.execute('SELECT count(*) FROM events').fetchone()[0],'deliveries':bridge.db.execute('SELECT count(*) FROM deliveries').fetchone()[0]}))
bridge.close()
'''


class RouteProcessRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.observations = []

    def command(self, mode, route='a'):
        return [sys.executable, '-c', WORKER, mode, route]

    def environment(self):
        return {**os.environ, 'PYTHONPATH': os.pathsep.join((str(ROOT / 'tests'), str(ROOT)))}

    def probe(self, root, mode, route='a'):
        result = subprocess.run(self.command(mode, route), cwd=root, env=self.environment(),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.observations.append({'mode': mode, 'route': route, 'exitCode': result.returncode, 'data': data})
        return data

    def exercise(self, mode):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            owner = subprocess.Popen(self.command(mode), cwd=root, env=self.environment(),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                with selectors.DefaultSelector() as ready:
                    ready.register(owner.stdout, selectors.EVENT_READ)
                    self.assertTrue(ready.select(timeout=10), 'owner did not reach the crash boundary')
                initial = json.loads(owner.stdout.readline())
                self.observations.append({'mode': mode, 'ready': initial})
                self.assertTrue(initial['ready'])
                self.assertEqual(initial['state'], 'confirmed' if mode == 'confirmed' else 'executing')
                conflict = self.probe(root, 'probe')
                self.assertTrue(conflict['rejected']);self.assertIn('Another bridge owns', conflict['error'])
                self.assertEqual(conflict['sends'], 0)
                independent = self.probe(root, 'probe', 'b')
                self.assertEqual(independent, {'rejected': False, 'events': 0, 'deliveries': 0, 'sends': 0})
                self.assertIsNone(owner.poll())
                owner.send_signal(signal.SIGKILL)
                owner.communicate(timeout=10)
                self.assertEqual(owner.returncode, -signal.SIGKILL)
                self.observations.append({'mode': mode, 'ownerExitCode': owner.returncode})
                wrong = self.probe(root, 'wrong-scope')
                self.assertTrue(wrong['rejected']);self.assertIn('different profile/conversation', wrong['error'])
                recovered = self.probe(root, 'resume')
                expected = 'confirmed' if mode == 'confirmed' else 'outcome_unknown'
                self.assertEqual(recovered['before']['state'], expected)
                self.assertEqual(recovered['result'], {**recovered['before'], 'replayed': True})
                self.assertEqual(recovered['sends'], 0);self.assertTrue(recovered['mismatchRejected'])
                self.assertEqual((recovered['events'], recovered['deliveries']), (2, 1))
                sends = [json.loads(line) for line in (root / 'provider-sends.ndjson').read_text().splitlines()]
                self.assertEqual(sends, [{'route': 'a', 'key': 'stable'}])
                # Normal close releases the lock too; no additional provider call.
                self.assertEqual(self.probe(root, 'resume'), recovered)
            finally:
                if owner.poll() is None:owner.terminate()
                owner.communicate(timeout=10)

    def test_confirmed_delivery_survives_actual_owner_death_without_resend(self):
        self.exercise('confirmed')

    def test_inflight_delivery_becomes_unknown_after_actual_owner_death_without_resend(self):
        self.exercise('uncertain')


if __name__ == '__main__':unittest.main()

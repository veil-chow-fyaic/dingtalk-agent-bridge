"""Synthetic subprocesses only: never invoke the official CLI or Keychain."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from dingtalk_bridge.core import DWS, BridgeError
from dingtalk_bridge.dws_access import DWSAccess, DWSAccessSuspended, SupervisedDWS, run_dws
from dingtalk_bridge.stream import StreamListener

ROOT = Path(__file__).resolve().parents[1]
ERROR = {'error': {'category': 'internal', 'code': 51, 'message':
    'resolve access token: load access token: load from keychain: read DEK from macOS Keychain: private-marker'}}


class DWSContainmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'binary': 'synthetic-dws', 'profile': 'synthetic-profile'}

    def binary(self, code):
        path = self.root / self.config['binary']
        path.write_text('#!' + sys.executable + '\n' + code); path.chmod(0o700)
        return path

    def alive(self, pid):
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='], capture_output=True, text=True)
        return bool(result.stdout.strip()) and not result.stdout.strip().startswith('Z')

    def cleanup_child(self):
        path = self.root / 'child.pid'
        if path.exists() and self.alive(int(path.read_text())):
            os.kill(int(path.read_text()), signal.SIGKILL)

    def until(self, predicate, seconds=8):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.025)
        self.fail('Expected synthetic process condition did not occur')

    def spawn_code(self, parent='print(\'{"ok":true}\',flush=True)'):
        # The child deliberately ignores TERM. It never invokes security/dws.
        child = "import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('child.ready').touch();time.sleep(3);Path('late-write').touch();time.sleep(60)"
        return ('import subprocess,sys,time\nfrom pathlib import Path\n'
                f'p=subprocess.Popen([sys.executable,"-c",{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
                'Path("child.pid").write_text(str(p.pid))\n'
                'while not Path("child.ready").exists():time.sleep(.01)\n' + parent + '\n')

    def test_exited_cli_cannot_leave_a_credential_reader_alive(self):
        self.addCleanup(self.cleanup_child)
        self.binary(self.spawn_code())
        self.assertTrue(DWS(self.root, self.config).call([])['ok'])
        self.assertFalse(self.alive(int((self.root / 'child.pid').read_text())))
        time.sleep(.1)
        self.assertFalse((self.root / 'late-write').exists())

    def test_timeout_cleans_descendants_and_suspends_future_calls(self):
        self.addCleanup(self.cleanup_child)
        self.binary(self.spawn_code('time.sleep(60)'))
        def started_descendant(*args, **kwargs):
            owned = SupervisedDWS(*args, **kwargs)
            try:
                # Exercise post-start descendant cleanup, not scheduler speed.
                # run_dws starts its 2s budget after this constructor returns.
                self.until(lambda:(self.root/'child.ready').exists())
                return owned
            except BaseException:
                owned.close()
                raise
        with patch('dingtalk_bridge.dws_access.SupervisedDWS', side_effect=started_descendant), patch('dingtalk_bridge.core.run_dws',
                   lambda command, cwd, stop: run_dws(command,cwd,stop=stop,timeout=2)):
            with self.assertRaisesRegex(DWSAccessSuspended,'dws_timeout'):
                DWS(self.root,self.config).call([])
        self.until(lambda:not self.alive(int((self.root/'child.pid').read_text())))
        old=(self.root/'child.pid').read_bytes()
        for _ in range(3):
            with self.assertRaisesRegex(DWSAccessSuspended,'dws_timeout'):DWS(self.root,self.config).call([])
        self.assertEqual((self.root/'child.pid').read_bytes(),old)

    def test_parent_sigkill_closes_lifetime_and_stale_reservation_blocks_restart(self):
        self.addCleanup(self.cleanup_child)
        self.binary(self.spawn_code('time.sleep(60)'))
        parent=subprocess.Popen([sys.executable,'-c',
            'from dingtalk_bridge.core import DWS;DWS(".",'+repr(self.config)+').call([])'],cwd=self.root,
            env={**os.environ,'PYTHONPATH':str(ROOT)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            self.until(lambda:(self.root/'child.ready').exists())
            parent.kill();parent.wait(timeout=3)
            self.until(lambda:not self.alive(int((self.root/'child.pid').read_text())))
            with self.assertRaisesRegex(DWSAccessSuspended,'dws_process_interrupted'):DWS(self.root,self.config).call([])
            time.sleep(3.1)
            self.assertFalse((self.root/'late-write').exists())
        finally:
            if parent.poll() is None:parent.kill();parent.wait()

    def test_concurrent_profiles_and_companion_share_one_failure_and_persist(self):
        self.binary("import json,time\nfrom pathlib import Path\nwith Path('calls').open('a') as f:f.write('call\\n')\ntime.sleep(.15)\nprint("+repr(json.dumps(ERROR))+",flush=True)\nraise SystemExit(51)")
        failures=[]
        def invoke(index):
            try:DWS(self.root,{**self.config,'profile':'synthetic-'+str(index)}).call([])
            except BridgeError as exc:failures.append(str(exc))
        workers=[threading.Thread(target=invoke,args=(i,)) for i in range(6)]
        for worker in workers:worker.start()
        for worker in workers:worker.join(timeout=8);self.assertFalse(worker.is_alive())
        self.assertEqual(failures,['credential_store_unavailable']*6)
        calls=(self.root/'calls').read_text()
        self.assertIn(calls,('call\n','call\ncall\n'))
        with self.assertRaises(DWSAccessSuspended):
            DWS(self.root,{**self.config,'imageUploadBinary':'never-spawn-this'}).upload_image('synthetic.png')
        self.assertNotIn('private-marker',json.dumps(DWSAccess(self.root).status()))
        self.assertEqual(DWSAccess(self.root).block_path.stat().st_mode & 0o777,0o600)
        restarted=subprocess.run([sys.executable,'-c',
            'from dingtalk_bridge.core import DWS;DWS(".",'+repr(self.config)+').call([])'],cwd=self.root,
            env={**os.environ,'PYTHONPATH':str(ROOT)},capture_output=True,text=True)
        self.assertNotEqual(restarted.returncode,0)
        self.assertNotIn('private-marker',restarted.stderr)
        self.assertEqual((self.root/'calls').read_text(),calls)

    def test_explicit_resume_is_required_and_does_not_itself_spawn(self):
        access=DWSAccess(self.root)
        with access.lock():access.block('operator_suspended')
        command=[sys.executable,'-m','dingtalk_bridge.dws_access','resume','--root',str(self.root)]
        denied=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(denied.returncode,0);self.assertEqual(access.status()['state'],'suspended')
        allowed=subprocess.run(command+['--confirm-retry'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(allowed.returncode,0);self.assertEqual(access.status(),{'state':'ready'})
        self.assertFalse((self.root/'calls').exists())
        self.binary("from pathlib import Path\nPath('calls').touch()\nprint('{\"ok\":true}')")
        self.assertTrue(DWS(self.root,self.config).call([])['ok'])

    def test_malformed_state_fails_closed_and_success_cannot_erase_external_latch(self):
        access=DWSAccess(self.root)
        with access.lock():
            access.path.write_text('{bad')
        with self.assertRaisesRegex(DWSAccessSuspended,'dws_access_state_invalid'):DWS(self.root,self.config).call([])
        access.resume()
        with access.lease() as lease:
            other=DWSAccess(self.root);other.block('credential_store_unavailable')
            lease.complete()
        self.assertEqual(access.status()['reason'],'credential_store_unavailable')
        access.block_path.write_text(json.dumps({'reason':['private-marker']}))
        self.assertEqual(access.status()['reason'],'dws_access_state_invalid')

    def test_stream_credential_failure_stops_reconnect_and_other_calls(self):
        self.binary("import sys\nfrom pathlib import Path\nwith Path('calls').open('a') as f:f.write('call\\n')\nprint("+
                    repr(json.dumps(ERROR,indent=2))+",file=sys.stderr,flush=True)\nraise SystemExit(51)")
        listener=StreamListener(self.root,{**self.config,'group':'synthetic'},lambda:None)
        stop=threading.Event();worker=threading.Thread(target=listener.run,args=(stop,));worker.start()
        try:
            self.until(lambda:listener.status()['state']=='suspended')
            time.sleep(1.1)
            with self.assertRaises(DWSAccessSuspended):DWS(self.root,self.config).call([])
            self.assertEqual((self.root/'calls').read_text(),'call\n')
            self.assertEqual(listener.status()['connections'],1)
            self.assertNotIn('private-marker',json.dumps(listener.status()))
        finally:stop.set();worker.join(timeout=8)
        self.assertFalse(worker.is_alive())

    def test_established_stream_stops_on_rpc_failure_and_cleans_child(self):
        self.addCleanup(self.cleanup_child)
        self.binary(self.spawn_code("print('[event] ready',file=sys.stderr,flush=True)\ntime.sleep(60)"))
        ready=threading.Event();stop=threading.Event()
        listener=StreamListener(self.root,{**self.config,'group':'synthetic'},ready.set)
        worker=threading.Thread(target=listener.run,args=(stop,));worker.start()
        try:
            self.assertTrue(ready.wait(8))
            failure=self.root/'synthetic-failure'
            failure.write_text('#!'+sys.executable+'\nprint('+repr(json.dumps(ERROR))+')\nraise SystemExit(51)\n')
            failure.chmod(0o700)
            with self.assertRaises(DWSAccessSuspended):DWS(self.root,{**self.config,'binary':failure.name}).call([])
            self.until(lambda:listener.status()['state']=='suspended')
            self.until(lambda:not self.alive(int((self.root/'child.pid').read_text())))
            self.assertEqual(listener.status()['connections'],1)
        finally:stop.set();worker.join(timeout=8)
        self.assertFalse(worker.is_alive())

    def test_stream_handshake_deadline_latches_without_assuming_descendant_readiness(self):
        self.binary('import time\ntime.sleep(60)')
        listener=StreamListener(self.root,{**self.config,'group':'synthetic'},lambda:None)
        with self.assertRaisesRegex(DWSAccessSuspended,'dws_timeout'):
            listener.run_once(threading.Event(),handshake_timeout=2)
        self.assertEqual(DWSAccess(self.root).status(), {'state':'suspended','reason':'dws_timeout'})
        audit=self.root/'local/runtime/dws-call-audit.ndjson';before=audit.read_bytes()
        with self.assertRaisesRegex(DWSAccessSuspended,'dws_timeout'):
            listener.run_once(threading.Event())
        self.assertEqual(audit.read_bytes(),before)
        self.assertEqual(listener.status()['connections'],1)

    def test_stream_handshake_timeout_cleans_child_and_latches(self):
        self.addCleanup(self.cleanup_child)
        self.binary(self.spawn_code('time.sleep(60)'))
        listener=StreamListener(self.root,{**self.config,'group':'synthetic'},lambda:None)
        # Unlike run_dws, run_once starts its handshake clock BEFORE constructing
        # the supervisor. Prepare a real owned descendant outside that clock;
        # only construction is supplied, never time, stop, close or reap.
        command=listener.command(3600)
        owned=SupervisedDWS(command,self.root,keep_stdin_open=True)
        try:
            self.until(lambda:(self.root/'child.pid').exists() and (self.root/'child.ready').exists())
            # The one-shot factory also rejects any unexpected second startup.
            with patch('dingtalk_bridge.stream.SupervisedDWS',side_effect=[owned]) as factory:
                with self.assertRaisesRegex(DWSAccessSuspended,'dws_timeout'):
                    listener.run_once(threading.Event(),handshake_timeout=2)
                self.until(lambda:not self.alive(int((self.root/'child.pid').read_text())))
                self.assertFalse((self.root/'late-write').exists())
                self.assertEqual(DWSAccess(self.root).status(), {'state':'suspended','reason':'dws_timeout'})
                audit=self.root/'local/runtime/dws-call-audit.ndjson';before=audit.read_bytes()
                with self.assertRaisesRegex(DWSAccessSuspended,'dws_timeout'):
                    listener.run_once(threading.Event())
                self.assertEqual(audit.read_bytes(),before)
                self.assertEqual(listener.status()['connections'],1)
                factory.assert_called_once_with(command,self.root,keep_stdin_open=True)
        finally:
            owned.close()

    def test_stream_ready_then_pretty_error_cannot_resume_automatically(self):
        self.binary('import sys\nprint("[event] ready",file=sys.stderr,flush=True)\nprint('+
                    repr(json.dumps(ERROR,indent=2))+',file=sys.stderr,flush=True)\nraise SystemExit(51)')
        listener=StreamListener(self.root,{**self.config,'group':'synthetic'},lambda:None)
        with self.assertRaisesRegex(DWSAccessSuspended,'credential_store_unavailable'):
            listener.run_once(threading.Event())
        self.assertTrue(listener.status()['ever_ready'])
        with self.assertRaises(DWSAccessSuspended):DWS(self.root,self.config).call([])

    def test_stream_keeps_stdin_open_until_explicit_stop(self):
        self.binary('import sys,signal\nsignal.signal(signal.SIGTERM,lambda *_:exit(0))\n'
                    'print("[event] ready",file=sys.stderr,flush=True)\nsys.stdin.read()\n')
        ready=threading.Event();stop=threading.Event();errors=[]
        listener=StreamListener(self.root,{**self.config,'group':'synthetic'},ready.set)
        def run():
            try:listener.run_once(stop)
            except Exception as exc:errors.append(str(exc))
        worker=threading.Thread(target=run);worker.start()
        try:
            self.assertTrue(ready.wait(8));time.sleep(.3)
            self.assertTrue(worker.is_alive())
            self.assertTrue(listener.status()['ready'])
        finally:stop.set();worker.join(timeout=8)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])

    def test_stop_signal_interrupts_owned_call_without_late_write(self):
        self.addCleanup(self.cleanup_child)
        self.binary(self.spawn_code('time.sleep(60)'))
        client=DWS(self.root,self.config);errors=[]
        def run():
            try:client.call([])
            except BridgeError as exc:errors.append(str(exc))
        worker=threading.Thread(target=run);worker.start()
        try:
            self.until(lambda:(self.root/'child.ready').exists());client.stop.set();worker.join(timeout=8)
            self.assertFalse(worker.is_alive());self.assertEqual(errors,['dws_process_interrupted'])
            self.until(lambda:not self.alive(int((self.root/'child.pid').read_text())))
        finally:client.stop.set();worker.join(timeout=8)


if __name__ == '__main__': unittest.main()

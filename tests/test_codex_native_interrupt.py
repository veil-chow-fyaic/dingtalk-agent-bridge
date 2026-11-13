"""Synthetic Codex-like CLI owns a detached tool and cancels it on SIGINT only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from dingtalk_bridge.agent_runtime import LocalRuntime, RuntimeStopped
from dingtalk_bridge.service_manager import process_identity
from dingtalk_bridge.runtime_guard import interrupt_owned_cli


class CodexNativeInterruptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        child = """from pathlib import Path
import time
Path('tool-ready').touch()
deadline=time.monotonic()+6
while not Path('release-tool').exists() and time.monotonic()<deadline:time.sleep(.01)
if Path('release-tool').exists():Path('late-file').write_text('survived')
"""
        binary = self.root / 'fake-codex'
        binary.write_text('#!' + sys.executable + '\n' + f"""import os,sys,signal,subprocess,time,json
from pathlib import Path
tool=subprocess.Popen([sys.executable,'-c',{child!r}],start_new_session=True,
                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def interrupt(*args):
    tool.terminate()
    tool.wait(timeout=2)
    Path('native-interrupted').touch()
    print(json.dumps({{'type':'turn.failed'}}),flush=True)
    raise SystemExit(130)
signal.signal(signal.SIGINT,interrupt)
Path('owners.json').write_text(json.dumps({{'cli':os.getpid(),'guard':os.getppid()}}))
print(json.dumps({{'type':'thread.started','thread_id':'synthetic-codex'}}),flush=True)
while True:time.sleep(.1)
""")
        binary.chmod(0o700)
        self.settings = {'kind': 'codex', 'binary': str(binary), 'timeoutSeconds': 10}

    def wait_ready(self):
        deadline = time.monotonic() + 5
        while not (self.workspace / 'tool-ready').exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.01)

    def assert_native_cleanup(self):
        (self.workspace / 'release-tool').touch()
        time.sleep(.4)
        self.assertFalse((self.workspace / 'late-file').exists(), 'detached tool wrote after cancellation')
        self.assertTrue((self.workspace / 'native-interrupted').exists())
        stderr = (self.root / 'run/stderr.log').read_text()
        self.assertIn('owned_cli_process_group', stderr)
        self.assertIn('sent_and_exited', stderr)

    def test_cancel_uses_native_interrupt_before_group_cleanup(self):
        cancel = threading.Event()
        def trigger():
            self.wait_ready()
            cancel.set()
        worker = threading.Thread(target=trigger)
        worker.start()
        try:
            with self.assertRaisesRegex(RuntimeStopped, 'cancelled'):
                LocalRuntime(self.settings).run('synthetic', self.workspace, self.root / 'run', None, cancel, lambda _: None)
        finally:
            worker.join()
        self.assert_native_cleanup()

    def test_timeout_uses_native_interrupt(self):
        # Expire the host deadline after the synthetic CLI installed its
        # handler. A one-second cold Python startup deadline may terminate it
        # before the handler exists, which exercises a different boundary.
        self.settings['timeoutSeconds'] = 30
        offset = [0]
        def ready(_):
            self.wait_ready()
            offset[0] = 31
        clock = SimpleNamespace(monotonic=lambda: time.monotonic() + offset[0], sleep=time.sleep)
        with patch('dingtalk_bridge.agent_runtime.time', clock):
            with self.assertRaisesRegex(RuntimeStopped, 'timeout'):
                LocalRuntime(self.settings).run('synthetic', self.workspace, self.root / 'run', None, threading.Event(), ready)
        self.assert_native_cleanup()

    def test_cancellation_output_is_drained_before_pipe_closes(self):
        binary = Path(self.settings['binary'])
        binary.write_text(binary.read_text().replace('    tool.terminate()',
            "    sys.stdout.write('x'*1024*1024+'\\n');sys.stdout.flush()\n    tool.terminate()"))
        self.test_cancel_uses_native_interrupt_before_group_cleanup()
        self.assertGreater((self.root / 'run/events.jsonl').stat().st_size, 1024*1024)

    def test_native_interrupt_pending_remains_explicit_and_bounded(self):
        process = Mock(pid=123)
        with patch('dingtalk_bridge.runtime_guard.wait_unreaped', side_effect=subprocess.TimeoutExpired('fixture', .01)) as wait, patch('dingtalk_bridge.runtime_guard.os.kill') as kill:
            self.assertEqual(interrupt_owned_cli(process, .01), 'sent_but_pending')
        self.assertEqual(wait.call_args_list[-1].args, (process, .01))
        self.assertEqual(kill.call_count, 1)

    def test_native_interrupt_does_not_signal_exited_cli(self):
        with patch('dingtalk_bridge.runtime_guard.wait_unreaped'), patch('dingtalk_bridge.runtime_guard.os.kill') as kill:
            self.assertEqual(interrupt_owned_cli(Mock()), 'already_exited')
        kill.assert_not_called()

    def test_native_interrupt_permission_failure_not_claimed_success(self):
        with patch('dingtalk_bridge.runtime_guard.wait_unreaped', side_effect=subprocess.TimeoutExpired('fixture', 0)), patch('dingtalk_bridge.runtime_guard.os.kill', side_effect=PermissionError):
            self.assertEqual(interrupt_owned_cli(Mock(pid=123)), 'signal_denied')

    def test_gateway_death_still_reaches_native_interrupt(self):
        driver = '''import sys,json,threading
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from dingtalk_bridge.agent_runtime import LocalRuntime
LocalRuntime(json.loads(sys.argv[2])).run('synthetic',Path(sys.argv[3]),Path(sys.argv[4]),None,threading.Event(),lambda _:None)
'''
        with (self.root / 'driver.log').open('wb') as log:
            owner = subprocess.Popen([sys.executable, '-c', driver, str(Path(__file__).resolve().parents[1]),
                json.dumps(self.settings), str(self.workspace), str(self.root / 'run')], stdout=log, stderr=log)
            try:
                self.wait_ready()
                owners = json.loads((self.workspace / 'owners.json').read_text())
                owner.kill()
                owner.wait(timeout=5)
                deadline = time.monotonic() + 8
                while any(process_identity(pid) for pid in owners.values()):
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.02)
                self.assert_native_cleanup()
            finally:
                if owner.poll() is None:
                    owner.kill()
                    owner.wait()


if __name__ == '__main__':
    unittest.main()

"""Synthetic Pi-like CLI owns a detached tool and cancels it on SIGTERM only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from dingtalk_bridge.agent_runtime import LocalRuntime, RuntimeStopped
from dingtalk_bridge.service_manager import process_identity


class PiNativeCleanupTests(unittest.TestCase):
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
        binary = self.root / 'fake-pi'
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
signal.signal(signal.SIGTERM,interrupt)
Path('owners.json').write_text(json.dumps({{'cli':os.getpid(),'guard':os.getppid()}}))
print(json.dumps({{'type':'session','id':'11111111-1111-4111-8111-111111111111','version':3}}),flush=True)
while True:time.sleep(.1)
""")
        binary.chmod(0o700)
        self.settings = {'kind': 'pi', 'binary': str(binary), 'timeoutSeconds': 10}

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
        self.assertIn('not_requested', stderr)

    def test_cancel_allows_pi_sigterm_cleanup(self):
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

    def test_timeout_allows_pi_sigterm_cleanup(self):
        self.settings['timeoutSeconds'] = 4
        with self.assertRaisesRegex(RuntimeStopped, 'timeout'):
            LocalRuntime(self.settings).run('synthetic', self.workspace, self.root / 'run', None, threading.Event(), lambda _: None)
        self.assert_native_cleanup()





    def test_gateway_death_still_reaches_pi_sigterm_cleanup(self):
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

"""Regression from a captured macOS ps ?Es shutdown observation."""
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from dingtalk_bridge.service_manager import Manager


class ManagerExitTransitionTests(unittest.TestCase):
    identity = 'Thu Nov 12 08:55:40 2026 /synthetic/python -m dingtalk_bridge --config /synthetic/config'

    def run_stop(self, responses, timeout=1):
        with tempfile.TemporaryDirectory() as temp:
            manager = Manager(Path(temp));manager.folder.mkdir(parents=True)
            record = {'name': 'transport', 'pid': 12345, 'identity': self.identity}
            with patch('dingtalk_bridge.service_manager.subprocess.run', side_effect=responses) as ps, \
                    patch('dingtalk_bridge.service_manager.os.kill') as kill:
                try:
                    manager.stop_component(record, timeout)
                    return ps.call_count, kill.call_args_list
                except RuntimeError as error:
                    return str(error), ps.call_count, kill.call_args_list

    def response(self, text, code=0):
        return subprocess.CompletedProcess([], code, text + '\n' if text else '', '')

    def test_same_birth_exiting_transition_waits_until_absent_without_another_signal(self):
        owned = self.response('Ss ' + self.identity)
        exiting = self.response('?Es Thu Nov 12 08:55:40 2026 (python3.11)')
        result = self.run_stop([owned, owned, exiting, self.response('', 1)])
        self.assertEqual(result[0], 4)
        self.assertEqual(len(result[1]), 1);self.assertEqual(result[1][0].args, (12345, signal.SIGTERM))

    def test_exiting_flag_does_not_authorize_signals_or_bypass_deadline(self):
        owned = self.response('Ss ' + self.identity)
        exiting = self.response('?Es Thu Nov 12 08:55:40 2026 (python3.11)')
        # The exemption is only waiting after an already-authorized TERM.
        for responses, signal_count in (([exiting], 0), ([owned, exiting], 0),
            ([owned, owned, self.response('?Es Thu Nov 12 08:55:41 2026 (python3.11)')], 1),
            ([owned, owned, self.response('Rs Thu Nov 12 08:55:40 2026 /synthetic/changed')], 1)):
            with self.subTest(responses=responses):
                result = self.run_stop(responses)
                self.assertIsInstance(result[0], str);self.assertEqual(len(result[2]), signal_count)
                self.assertIn('ownership' if signal_count == 0 else 'PID changed', result[0])
        result = self.run_stop([owned, owned, exiting], timeout=.01)
        self.assertEqual(result[0], 'Graceful shutdown still pending; no force kill performed')
        self.assertEqual(len(result[2]), 1)


if __name__ == '__main__':unittest.main()

"""Exercise overlapping HTTP clients and real synthetic CLI child processes."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


class ReconcileHTTPTests(unittest.TestCase):
    def test_late_status_or_cli_error_preserves_confirmed_http_delivery(self):
        for late in ('PENDING', 'FAILED', 'AUTH_ERROR', 'PARAM_ERROR'):
            with self.subTest(late=late), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / 'local').mkdir()
                (root / 'late').write_text(late)
                binary = root / 'dws'
                binary.write_text('#!' + sys.executable + '''
import fcntl,json,sys,time
from pathlib import Path
a=sys.argv
if '+conversation-info' in a:
 d={'result':{'conversationInfo':{'openConversationId':'fixture-conversation'}}}
elif '+chat-messages' in a:
 d={'messages':[],'complete':True}
elif '+messages-send' in a:
 p=Path('sends');p.write_text(str(int(p.read_text())+1 if p.exists() else 1))
 d={'sendReceipt':{'openTaskId':'fixture-task'}}
elif '+messages-query-send-status' in a:
 with Path('query-lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  p=Path('queries');n=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(n))
 if n==1:
  Path('query-entered').touch();deadline=time.monotonic()+6
  while not Path('release').exists() and time.monotonic()<deadline:time.sleep(.01)
  if not Path('release').exists():raise SystemExit(9)
  status=Path('late').read_text()
 else:status='SUCCESS'
 if status in ('AUTH_ERROR','PARAM_ERROR'):
  error={'reason':'authorization_required'} if status=='AUTH_ERROR' else {'reason':'invalid_request','server_error_code':'PARAM_ERROR'}
  print(json.dumps({'ok':False,'error':error}),file=sys.stderr);raise SystemExit(1)
 d={'result':{'sendStatus':status}}
 if status=='SUCCESS':d['messageRef']={'openConversationId':'fixture-conversation','openMessageId':'fixture-message'}
else:raise SystemExit(7)
print(json.dumps(d))
''')
                binary.chmod(0o700)
                (root / 'local/service-config.json').write_text(json.dumps({
                    'profile': 'fixture-profile', 'group': 'fixture-conversation',
                    'name': 'fixture', 'selfSenderId': 'fixture-self', 'binary': 'dws'}))
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0))
                    port = sock.getsockname()[1]
                child = subprocess.Popen([sys.executable, '-m', 'dingtalk_bridge', '--port', str(port)],
                    cwd=root, env={**os.environ, 'PYTHONPATH': str(ROOT)},
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                token_path = root / 'local/runtime/http-token'

                def request(path, body=None):
                    req = Request(f'http://127.0.0.1:{port}' + path,
                        data=None if body is None else json.dumps(body).encode(),
                        headers={'Authorization': 'Bearer ' + token_path.read_text().strip(),
                                 'Content-Type': 'application/json'})
                    with build_opener(ProxyHandler({})).open(req, timeout=8) as response:
                        return response.status, json.load(response)

                try:
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline:
                        self.assertIsNone(child.poll())
                        if token_path.exists():
                            try:
                                request('/v1/health')
                                break
                            except OSError:
                                pass
                        time.sleep(.03)
                    else:
                        self.fail('Synthetic HTTP service did not start')
                    payload = {'idempotency_key': 'fixture-key', 'text': 'synthetic'}
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        slow = pool.submit(request, '/v1/send', payload)
                        try:
                            deadline = time.monotonic() + 3
                            while not (root / 'query-entered').exists() and time.monotonic() < deadline:
                                time.sleep(.01)
                            self.assertTrue((root / 'query-entered').exists())
                            fast = request('/v1/reconcile', {'idempotency_key': 'fixture-key'})
                            self.assertEqual(fast[0], 200)
                            self.assertEqual(fast[1]['state'], 'confirmed')
                        finally:
                            (root / 'release').touch()
                        self.assertEqual(slow.result(timeout=8), fast)
                    self.assertEqual(request('/v1/deliveries/fixture-key'), fast)
                    replay_code, replay = request('/v1/send', payload)
                    self.assertEqual(replay_code, 200)
                    self.assertTrue(replay.pop('replayed'))
                    self.assertEqual(replay, fast[1])
                    self.assertEqual((root / 'sends').read_text(), '1')
                    self.assertEqual((root / 'queries').read_text(), '2')
                finally:
                    (root / 'release').touch()
                    child.send_signal(signal.SIGTERM)
                    try:
                        code = child.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                        self.fail('Synthetic service did not stop gracefully')
                self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()

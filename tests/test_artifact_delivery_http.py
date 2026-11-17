"""Real loopback HTTP/CLI boundary with a synthetic executable, no DWS account."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from dingtalk_bridge import cli
from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.core import ArtifactIntegrityError

ROOT = Path(__file__).resolve().parents[1]


class ArtifactHTTPTests(unittest.TestCase):
    def test_expected_digest_http_cli_and_gateway_error_contract(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile() as child_log:
            root = Path(temp); (root / 'local/outbox').mkdir(parents=True)
            original = b'approved synthetic artifact'; digest = hashlib.sha256(original).hexdigest()
            artifact = root / 'local/outbox/result.txt'; artifact.write_bytes(b'changed')
            binary = root / 'synthetic-dws'
            binary.write_text('#!' + sys.executable + '''
import json,sys,hashlib
from pathlib import Path
a=sys.argv
if '+conversation-info' in a:d={'result':{'conversationInfo':{'openConversationId':'fixture-chat'}}}
elif '+chat-messages' in a:d={'messages':[],'complete':True}
elif '+messages-send' in a:
 p=Path('sends');p.write_text(str(int(p.read_text())+1 if p.exists() else 1))
 Path('sent-sha256').write_text(hashlib.sha256(Path(a[a.index('--file')+1]).read_bytes()).hexdigest())
 d={'sendReceipt':{'openTaskId':'fixture-task'}}
elif '+messages-query-send-status' in a:
 d={'result':{'sendStatus':'SUCCESS'},'messageRef':{'openConversationId':'fixture-chat','openMessageId':'fixture-message'}}
else:raise SystemExit(7)
print(json.dumps(d))
''')
            binary.chmod(0o700)
            (root / 'local/service-config.json').write_text(json.dumps({
                'profile': 'fixture-profile', 'group': 'fixture-chat', 'name': 'fixture',
                'binary': binary.name, 'selfSenderId': 'fixture-self', 'receiveMode': 'history'}))
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            # This synthetic child has no account or real provider. Retain its startup
            # traceback before the unchanged 8-second readiness deadline; otherwise
            # a blocked interpreter/server constructor is indistinguishable from
            # an HTTP failure when stderr is discarded.
            bootstrap = ("import faulthandler,runpy; "
                         "faulthandler.dump_traceback_later(4,repeat=False); "
                         "runpy.run_module('dingtalk_bridge',run_name='__main__',alter_sys=True)")
            child = subprocess.Popen([sys.executable, '-c', bootstrap, '--port', str(port)],
                cwd=root, env={**os.environ, 'PYTHONPATH': str(ROOT)},
                stdout=child_log, stderr=subprocess.STDOUT)
            token_path = root / 'local/runtime/http-token'
            opener = build_opener(ProxyHandler({})); base = f'http://127.0.0.1:{port}'
            def request(path, data=None):
                return opener.open(Request(base + path, data=None if data is None else json.dumps(data).encode(),
                    headers={'Authorization': 'Bearer ' + token_path.read_text().strip(),
                             'Content-Type': 'application/json'}), timeout=5)
            def routed_urlopen(req, timeout=None):
                return opener.open(Request(req.full_url.replace('http://127.0.0.1:18768', base),
                    data=req.data, headers=dict(req.header_items())), timeout=5)
            def startup_failure():
                output = os.pread(child_log.fileno(), 16384, 0).decode('utf-8', errors='replace')
                return ('Synthetic HTTP service did not start; '
                        f'child_exit={child.poll()!r}; token_created={token_path.exists()}; '
                        f'last_probe={last_probe!r}; child_output={output!r}')
            try:
                last_probe = 'not attempted: token absent'
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if child.poll() is not None: self.fail(startup_failure())
                    if token_path.exists():
                        try:
                            with request('/v1/health'): break
                        except OSError as exc: last_probe = f'{type(exc).__name__}: {exc}'
                    time.sleep(.03)
                else: self.fail(startup_failure())
                payload = {'idempotency_key': 'original-key', 'file': 'local/outbox/result.txt', 'expected_sha256': digest}
                with self.assertRaises(HTTPError) as caught: request('/v1/send', payload)
                with caught.exception as response:
                    self.assertEqual(response.code, 409)
                    self.assertEqual(json.load(response), {'error': 'artifact_integrity_mismatch', 'delivery_attempted': False})
                self.assertFalse((root / 'sends').exists())
                with patch('dingtalk_bridge.agent_gateway.urlopen', routed_urlopen):
                    with self.assertRaises(ArtifactIntegrityError):
                        Gateway.http(SimpleNamespace(root=root, scope={}), '/v1/send', payload)
                artifact.write_bytes(original)
                output = io.StringIO()
                argv = ['dab', '--token-file', str(token_path), 'send', '--key', 'original-key',
                        '--file', 'local/outbox/result.txt', '--expected-sha256', digest]
                with patch.object(sys, 'argv', argv), patch.object(cli, 'urlopen', routed_urlopen), redirect_stdout(output):
                    cli.main()
                self.assertEqual(json.loads(output.getvalue())['state'], 'confirmed')
                self.assertEqual((root / 'sent-sha256').read_text(), digest)
                artifact.unlink()
                with request('/v1/send', payload) as response:
                    replay = json.load(response)
                self.assertTrue(replay['replayed']); self.assertEqual(replay['state'], 'confirmed')
                self.assertEqual((root / 'sends').read_text(), '1')
            finally:
                child.send_signal(signal.SIGTERM)
                try: code = child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(); self.fail('Synthetic service did not stop')
            self.assertEqual(code, 0)


if __name__ == '__main__': unittest.main()

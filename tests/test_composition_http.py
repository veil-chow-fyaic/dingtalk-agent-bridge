"""Actual loopback HTTP and CLI parsing; synthetic DWS, no account or model."""
from contextlib import redirect_stdout
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
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from dingtalk_bridge import cli
from test_composition import png
import hashlib

ROOT = Path(__file__).resolve().parents[1]


class CompositionHTTPTests(unittest.TestCase):
    def test_cli_http_composition_digest_gate_originals_and_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'local/outbox').mkdir(parents=True)
            value = {'text': 'two originals', 'images': []}
            for i, color in enumerate(((255, 0, 0), (0, 0, 255))):
                path = f'local/outbox/{i}.png'; content = png(color)
                (root / path).write_bytes(content)
                value['images'].append({'path': path, 'sha256': hashlib.sha256(content).hexdigest()})
            binary = root / 'synthetic-dws'
            binary.write_text('#!' + sys.executable + '''
import json,sys,hashlib,re
from pathlib import Path
a=sys.argv
if '+conversation-info' in a:d={'result':{'conversationInfo':{'openConversationId':'fixture-chat'}}}
elif '+chat-messages' in a:d={'messages':[],'complete':True}
elif '+messages-send' in a:
 p=Path('sends');p.write_text(str(int(p.read_text())+1 if p.exists() else 1))
 paths=re.findall(r'!\\[image \\d+\\]\\(([^)]+)\\)',a[a.index('--markdown')+1])
 Path('sent-digests').write_text(json.dumps([hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths]))
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
            child = subprocess.Popen([sys.executable, '-m', 'dingtalk_bridge', '--port', str(port)],
                cwd=root, env={**os.environ, 'PYTHONPATH': str(ROOT)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            token_path = root / 'local/runtime/http-token'
            opener = build_opener(ProxyHandler({})); base = f'http://127.0.0.1:{port}'
            def request(path, data=None):
                return opener.open(Request(base + path, data=None if data is None else json.dumps(data).encode(),
                    headers={'Authorization': 'Bearer ' + token_path.read_text().strip(), 'Content-Type': 'application/json'}), timeout=5)
            def routed_urlopen(req, timeout=None):
                return opener.open(Request(req.full_url.replace('http://127.0.0.1:18768', base),
                    data=req.data, headers=dict(req.header_items())), timeout=5)
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    self.assertIsNone(child.poll())
                    if token_path.exists():
                        try:
                            with request('/v1/health'): break
                        except OSError: pass
                    time.sleep(.03)
                else: self.fail('Synthetic HTTP service did not start')
                payload = {'idempotency_key': 'fixed-key', 'composition': value}
                original = root / value['images'][1]['path']; content = original.read_bytes(); original.write_bytes(b'changed')
                with self.assertRaises(HTTPError) as caught: request('/v1/send', payload)
                with caught.exception as response:
                    self.assertEqual(response.code, 409)
                    self.assertEqual(json.load(response), {'error': 'artifact_integrity_mismatch', 'delivery_attempted': False})
                self.assertFalse((root / 'sends').exists()); original.write_bytes(content)
                value_path = root / 'composition.json'; value_path.write_text(json.dumps(value))
                output = io.StringIO()
                argv = ['dab', '--token-file', str(token_path), 'send', '--key', 'fixed-key', '--composition-json', str(value_path)]
                with patch.object(sys, 'argv', argv), patch.object(cli, 'urlopen', routed_urlopen), redirect_stdout(output): cli.main()
                self.assertEqual(json.loads(output.getvalue())['state'], 'confirmed')
                self.assertEqual(json.loads((root / 'sent-digests').read_text()), [image['sha256'] for image in value['images']])
                for item in value['images']: (root / item['path']).unlink()
                with request('/v1/send', payload) as response: replay = json.load(response)
                self.assertTrue(replay['replayed']); self.assertEqual((root / 'sends').read_text(), '1')
            finally:
                child.send_signal(signal.SIGTERM)
                try: code = child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(); self.fail('Synthetic service did not stop')
            self.assertEqual(code, 0)


if __name__ == '__main__': unittest.main()

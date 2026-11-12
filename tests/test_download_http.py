"""Real local HTTP/CLI processes must not expose invalid attachment success."""
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
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


class DownloadHTTPTests(unittest.TestCase):
    def test_invalid_size_is_502_then_same_message_recovers_and_caches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);(root / 'local').mkdir()
            binary = root / 'dws'
            binary.write_text('#!' + sys.executable + '''
import json,sys
from pathlib import Path
a=sys.argv
if '+conversation-info' in a:d={'result':{'conversationInfo':{'openConversationId':'g'}}}
elif '+chat-messages' in a:d={'complete':True,'messages':[{'messageId':'m1','conversationId':'g','senderId':'other','text':'[文件] fixture.txt fileId: f','resourceRefs':[{'type':'fileId','resourceId':'f'}]}]}
elif '+messages-mget' in a:
 p=Path('downloads-count');n=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(n))
 dest=Path(a[a.index('--output-dir')+1])/'fixture.txt';dest.parent.mkdir(parents=True);dest.write_bytes(b'original')
 d={'messages':[{'messageId':'m1','conversationId':'g'}],'resourceDownloads':{'ok':True,'downloads':[{'resourceType':'fileId','resourceId':'f','localPath':str(dest),'sizeBytes':999 if n==1 else 8}]}}
else:raise SystemExit(7)
print(json.dumps(d))
''')
            binary.chmod(0o700)
            (root / 'local/service-config.json').write_text(json.dumps({
                'profile': 'synthetic-profile', 'group': 'g', 'name': 'synthetic',
                'selfSenderId': 'self', 'binary': 'dws'}))
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0));port = sock.getsockname()[1]
            child = subprocess.Popen([sys.executable, '-m', 'dingtalk_bridge', '--port', str(port)],
                cwd=root, env={**os.environ, 'PYTHONPATH': str(ROOT)},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            token_path = root / 'local/runtime/http-token'
            def request(path, body=None):
                req = Request(f'http://127.0.0.1:{port}' + path,
                    data=None if body is None else json.dumps(body).encode(),
                    headers={'Authorization': 'Bearer ' + token_path.read_text().strip(), 'Content-Type': 'application/json'})
                try:
                    with build_opener(ProxyHandler({})).open(req, timeout=8) as response:return response.status, json.load(response)
                except HTTPError as error:
                    with error:return error.code, json.load(error)
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    self.assertIsNone(child.poll())
                    if token_path.exists():
                        try:
                            request('/v1/health');break
                        except OSError:pass
                    time.sleep(.03)
                else:self.fail('Synthetic HTTP service did not start')
                self.assertEqual(request('/v1/sync', {})[0], 200)
                code, body = request('/v1/attachments', {'message_id': 'm1'})
                self.assertEqual(code, 502);self.assertIn('Downloaded attachment', body['error'])
                self.assertEqual(list((root / 'local/runtime').rglob('manifest.json')), [])
                code, body = request('/v1/attachments', {'message_id': 'm1'})
                self.assertEqual(code, 200);self.assertIs(body['ok'], True)
                self.assertEqual((root / body['downloads'][0]['localPath']).read_bytes(), b'original')
                self.assertEqual(request('/v1/attachments', {'message_id': 'm1'}), (code, body))
                self.assertEqual((root / 'downloads-count').read_text(), '2')
                self.assertEqual(len(list((root / 'local/runtime').rglob('fixture.txt'))), 2)
            finally:
                child.send_signal(signal.SIGTERM)
                try:exit_code = child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill();child.wait();self.fail('Synthetic service did not stop gracefully')
            self.assertEqual(exit_code, 0)


if __name__ == '__main__':unittest.main()

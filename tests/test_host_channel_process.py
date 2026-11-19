"""Two real sidecar processes and the loopback bridge, backed by synthetic DWS."""
import base64
import hashlib
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
from urllib.request import Request

from dingtalk_bridge.local_http import urlopen


class HostChannelProcessTests(unittest.TestCase):
    def test_process_restart_original_file_and_literal_replies(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'local').mkdir()
            dws = root / 'test-dws'
            dws.write_text('#!' + sys.executable + """
import json, sys
from pathlib import Path
a = sys.argv
if '+conversation-info' in a:
    record = {'result': {'conversationInfo': {'openConversationId': 'g'}}}
elif '+chat-messages' in a:
    raw = {'conversationId':'g', 'createTime':'2026-11-17T12:00:00+08:00'}
    record = {'complete': True, 'messages': [
        {**raw, 'messageId':'original', 'senderId':'other', 'text':'[文件] source.txt fileId: f',
         'resourceRefs':[{'type':'fileId','resourceId':'f'}]},
        {**raw, 'messageId':'output', 'senderId':'self', 'text':'my reply'}]}
    if Path('submit-selector').exists():
        record['messages'].append({**raw,'messageId':'request','senderId':'other',
                                   'text':'/agent --files ["source.txt"] inspect'})
elif '+messages-mget' in a:
    dest = Path(a[a.index('--output-dir')+1])/'source.txt'
    dest.parent.mkdir(parents=True); dest.write_bytes(b'verified')
    record = {'messages':[{'messageId':'original','conversationId':'g'}],
              'resourceDownloads': {'ok':True,'downloads':[
                  {'resourceType':'fileId','resourceId':'f','localPath':str(dest),'sizeBytes':8}]}}
elif '+messages-send' in a:
    key = a[a.index('--idempotency-key')+1]
    with Path('sent.jsonl').open('a') as stream:
        content = a[a.index('--text')+1] if '--text' in a else Path(a[a.index('--file')+1]).read_text()
        stream.write(json.dumps([key, content])+'\\n')
    record = {'sendReceipt': {'openTaskId': key}}
elif '+messages-query-send-status' in a:
    task = a[a.index('--open-task-id')+1]
    record = {'result': {'sendStatus':'SUCCESS'}, 'messageRef':{'openConversationId':'g','openMessageId':'sent-'+task}}
else:
    sys.exit(7)
print(json.dumps(record))
""")
            dws.chmod(0o700)
            settings = {'profile': 'synthetic', 'group': 'g', 'accountId': 'synthetic',
                        'name': 'test', 'selfSenderId': 'self', 'binary': dws.name,
                        'executionOwner': 'openclaw'}
            (root / 'local/service-config.json').write_text(json.dumps(settings))
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = {**os.environ, 'PYTHONPATH': str(source)}
            with tempfile.TemporaryFile() as log:
                service = subprocess.Popen([sys.executable, '-m', 'dingtalk_bridge', '--port', str(port)],
                                           cwd=root, env=env, stdout=log, stderr=log)
                try:
                    token_path = root / 'local/runtime/http-token'
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        self.assertIsNone(service.poll())
                        if token_path.exists():
                            request = Request(f'http://127.0.0.1:{port}/v1/sync', data=b'{}', headers={
                                'Authorization': 'Bearer ' + token_path.read_text().strip(),
                                'Content-Type': 'application/json'})
                            try:
                                with urlopen(request, timeout=5) as response:
                                    self.assertEqual(response.status, 200)
                                break
                            except ConnectionError:
                                pass
                            except OSError:
                                if service.poll() is not None:
                                    raise
                        time.sleep(.03)
                    else:
                        self.fail('synthetic transport failed to initialize')

                    def sidecar(requests):
                        frames = ''.join(json.dumps({**obj, 'id': i}) + '\n' for i, obj in enumerate(requests))
                        result = subprocess.run([
                            sys.executable, '-m', 'dingtalk_bridge.host_channel', '--initial-cursor', '0',
                            '--account-id', 'synthetic', '--conversation-id', 'g', '--port', str(port)],
                            text=True, input=frames, capture_output=True, timeout=20, check=True,
                            cwd=root, env=env)
                        replies = [json.loads(line) for line in result.stdout.splitlines()]
                        self.assertEqual([r['id'] for r in replies], list(range(len(requests))))
                        self.assertTrue(all(r['ok'] for r in replies), replies)
                        return [r['result'] for r in replies]

                    text = '  [Agent] is host text\n原文\n'
                    artifact = b'host bytes'
                    message = {'op':'send', 'key':'text', 'text':text}
                    file = {'op':'send', 'key':'artifact', 'media':{
                        'kind':'file', 'filename':'result.txt', 'base64':base64.b64encode(artifact).decode()}}
                    received, out, result = sidecar([{'op':'poll'}, message, file])
                    part = received['message']['parts'][0]
                    self.assertEqual(part['sha256'], hashlib.sha256(b'verified').hexdigest())
                    self.assertEqual(Path(part['path']).read_bytes(), b'verified')
                    self.assertEqual([out['state'], result['state']], ['confirmed', 'confirmed'])
                    recovered = sidecar([{'op':'poll'}, {'op':'summary'}, file])
                    self.assertIsNone(recovered[0]['message'])
                    self.assertEqual(recovered[1]['dispatch'], {'unknown': 1})
                    self.assertEqual(recovered[2]['message_id'], 'sent-artifact')
                    sends = [json.loads(line) for line in (root/'sent.jsonl').read_text().splitlines()]
                    self.assertEqual(sends, [['text', text], ['artifact', artifact.decode()]])

                    (root/'submit-selector').touch()
                    with urlopen(request, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                    received, selection, original, _, idle = sidecar([
                        {'op':'poll'}, {'op':'selectFiles', 'messageId':'request'},
                        {'op':'selectedFile', 'messageId':'request', 'index':0},
                        {'op':'ack', 'messageId':'request', 'status':'done'}, {'op':'poll'}])
                    self.assertEqual(received['message']['id'], 'request')
                    self.assertEqual(selection, {'count':1, 'task':'inspect'})
                    self.assertEqual(Path(original['part']['path']).read_bytes(), b'verified')
                    self.assertIsNone(idle['message'])
                finally:
                    if service.poll() is None:
                        service.send_signal(signal.SIGTERM)
                    try:
                        service.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        service.kill()
                        service.wait()
                        self.fail('synthetic transport failed to stop')

"""Two real local HTTP routes: history-only recovery never starts an event bus."""
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
from urllib.request import Request,build_opener,ProxyHandler

ROOT=Path(__file__).resolve().parents[1]


class HistoryRecoveryModeTests(unittest.TestCase):
    def test_two_routes_receive_send_deduplicate_and_pause_without_any_event_process(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'local').mkdir();binary=root/'synthetic-dws'
            binary.write_text('#!'+sys.executable+'''\nimport json,sys
from pathlib import Path
a=sys.argv[1:]
with Path('calls').open('a') as f:f.write(json.dumps(a)+'\\n')
if 'event' in a:Path('forbidden-event-process').touch();raise SystemExit(77)
target='d' if '--open-dingtalk-id' in a else 'g'
if Path('fail').exists():
 print(json.dumps({'error':{'category':'internal','code':51,'message':'resolve access token: load access token: load from keychain: read DEK from macOS Keychain: synthetic'}}));raise SystemExit(51)
if '+conversation-info' in a:data={'result':{'conversationInfo':{'openConversationId':target}}}
elif '+chat-messages' in a:data={'complete':True,'messages':[{'messageId':'message-'+target,'conversationId':target,'senderId':'synthetic-user','text':'history-only task'}]}
elif '+messages-send' in a:data={'sendReceipt':{'openTaskId':'task-'+target}}
elif '+messages-query-send-status' in a:
 target=a[a.index('--open-task-id')+1].split('-')[-1]
 data={'result':{'sendStatus':'SUCCESS'},'messageRef':{'openConversationId':target,'openMessageId':'reply-'+target}}
else:raise SystemExit(9)
print(json.dumps(data))
''');binary.chmod(0o700)
            routes=[dict(accountId='synthetic',profile='synthetic:profile',conversationId=kind,
                conversationType='group' if kind=='g' else 'direct',peerOpenDingTalkId='synthetic-peer',
                selfSenderId='synthetic-self',binary=binary.name,receiveMode='history') for kind in ('g','d')]
            (root/'local/service-config.json').write_text(json.dumps({'routes':routes}))
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=subprocess.Popen([sys.executable,'-m','dingtalk_bridge','--port',str(port),'--poll-seconds','5'],cwd=root,
                env={**os.environ,'PYTHONPATH':str(ROOT)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            token=root/'local/runtime/http-token'
            def request(path,body=None):
                req=Request(f'http://127.0.0.1:{port}'+path,data=None if body is None else json.dumps(body).encode(),
                    headers={'Authorization':'Bearer '+token.read_text().strip(),'Content-Type':'application/json'})
                with build_opener(ProxyHandler({})).open(req,timeout=5) as response:return json.load(response)
            try:
                deadline=time.monotonic()+12
                while time.monotonic()<deadline:
                    self.assertIsNone(server.poll())
                    try:
                        health=request('/v1/health')
                        if all(r['events']==1 for r in health['routes']):break
                    except OSError:pass
                    time.sleep(.05)
                else:self.fail('Both synthetic history routes did not synchronize')
                self.assertEqual(health['stream_listeners'],[])
                for kind in ('g','d'):
                    events=request('/v1/events?account_id=synthetic&conversation_id='+kind)['events']
                    self.assertEqual(len(events),1);self.assertEqual(events[0]['content'],'history-only task')
                    body={'account_id':'synthetic','conversation_id':kind,'idempotency_key':'reply-'+kind,'text':'synthetic result'}
                    self.assertEqual(request('/v1/send',body)['state'],'confirmed')
                    self.assertTrue(request('/v1/send',body)['replayed'])
                for kind in ('g','d'):request('/v1/sync',{'account_id':'synthetic','conversation_id':kind})
                self.assertTrue(all(r['events']==1 for r in request('/v1/health')['routes']))
                (root/'fail').touch()
                with self.assertRaises(HTTPError) as failure:request('/v1/sync',{'account_id':'synthetic','conversation_id':'g'})
                self.assertEqual(failure.exception.code,502);failure.exception.close()
                self.assertEqual(request('/v1/health')['dws_access']['state'],'suspended')
                # Any already-in-flight read is bounded. Wait a full polling
                # interval, then prove additional cycles cannot launch a CLI.
                time.sleep(5.3);before=(root/'calls').read_bytes();(root/'fail').unlink()
                for kind in ('g','d'):
                    with self.assertRaises(HTTPError) as blocked:request('/v1/sync',{'account_id':'synthetic','conversation_id':kind})
                    blocked.exception.close()
                self.assertEqual((root/'calls').read_bytes(),before)
                calls=[json.loads(line) for line in before.decode().splitlines()]
                self.assertFalse(any('event' in args for args in calls));self.assertFalse((root/'forbidden-event-process').exists())
                self.assertEqual(sum('+messages-send' in args for args in calls),2)
            finally:
                server.send_signal(signal.SIGTERM)
                try:code=server.wait(timeout=8)
                except subprocess.TimeoutExpired:server.kill();server.wait();self.fail('Synthetic history server did not stop')
            self.assertEqual(code,0)


if __name__=='__main__':unittest.main()

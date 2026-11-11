import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from dingtalk_bridge.stream import StreamListener
from test_core import CFG

ROOT=Path(__file__).resolve().parents[1]


class StreamTests(unittest.TestCase):
    def test_target_commands_and_scope_filter(self):
        calls=[];s=StreamListener(ROOT,CFG,lambda:calls.append(1))
        args=s.command(10);self.assertIn('user_im_message_receive_group',args);self.assertNotIn('--force',args)
        direct=StreamListener(ROOT,{**CFG,'conversationType':'direct','peerOpenDingTalkId':'peer'},lambda:None).command(10)
        self.assertIn('user_im_message_receive_o2o',direct);self.assertNotIn('--group',direct)
        s.line('stdout','{}');s.line('stdout',json.dumps({'message_id':'m','conversation_id':'foreign'}))
        s.line('stdout','broken');self.assertEqual(calls,[])
        s.line('stderr','[event] ready event_key=fixture')
        s.line('stdout',json.dumps({'message_id':'m','conversation_id':'g','content':'not forwarded'}))
        self.assertEqual(len(calls),2);self.assertEqual(s.status()['rejected_lines'],3)
        self.assertNotIn('content',s.status());self.assertEqual(s.status()['accepted_hints'],1)

    def test_child_ready_and_graceful_cancellation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);binary=root/'dws'
            binary.write_text('#!'+sys.executable+'\nimport signal,time\nsignal.signal(signal.SIGTERM,lambda *_:exit(0))\nprint("[event] ready",file=__import__("sys").stderr,flush=True)\ntime.sleep(30)\n')
            binary.chmod(0o700);stop=threading.Event();s=StreamListener(root,CFG,stop.set)
            s.run_once(stop,duration=10)
            self.assertTrue(s.status()['ever_ready']);self.assertEqual(s.status()['state'],'stopped')
            self.assertEqual(s.status()['exit_code'],0)


class HTTPContractTests(unittest.TestCase):
    def test_public_endpoints_auth_discovery_wait_and_shutdown(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);binary=root/'dws';local=root/'local';local.mkdir()
            binary.write_text('#!'+sys.executable+'''\nimport json,sys
a=sys.argv
if '+conversation-info' in a:d={'result':{'conversationInfo':{'openConversationId':'g'}}}
elif '+chat-messages' in a:d={'messages':[],'complete':True}
elif '+chat-list' in a:d={'chats':[{'openConversationId':'g','conversationType':'group','name':'fixture'}],'complete':True,'paginationKnown':True,'hasMore':False,'nextCursor':0}
else:raise SystemExit(7)
print(json.dumps(d))
''');binary.chmod(0o700)
            (local/'service-config.json').write_text(json.dumps(CFG))
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            env={**os.environ,'PYTHONPATH':str(ROOT)}
            child=subprocess.Popen([sys.executable,'-m','dingtalk_bridge','--port',str(port),'--poll-seconds','5'],cwd=root,env=env,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                token_path=local/'runtime/http-token';deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    if child.poll() is not None:self.fail('Fixture server exited')
                    if token_path.exists():
                        try:
                            with urlopen(Request(f'http://127.0.0.1:{port}/v1/health',headers={'Authorization':'Bearer '+token_path.read_text().strip()}),timeout=.5) as r:json.load(r)
                            break
                        except OSError:pass
                    time.sleep(.03)
                else:self.fail('Fixture server did not start')
                def get(path,auth=True):
                    req=Request(f'http://127.0.0.1:{port}'+path,headers={'Authorization':'Bearer '+token_path.read_text().strip()} if auth else {})
                    with urlopen(req,timeout=3) as r:return json.load(r)
                with self.assertRaises(HTTPError) as unauthorized:get('/v1/events',False)
                self.assertEqual(unauthorized.exception.code,401)
                unauthorized.exception.close()
                d=get('/v1/discovery');self.assertTrue(d['complete']);self.assertFalse(d['routes_changed'])
                self.assertEqual(len(get('/v1/conversations')['conversations']),1)
                self.assertEqual(get('/v1/events?after=0&wait_seconds=0.03')['next_cursor'],0)
                with self.assertRaises(HTTPError) as invalid:get('/v1/events?wait_seconds=NaN')
                invalid.exception.close()
                with self.assertRaises(HTTPError) as foreign:get('/v1/events?account_id=wrong&conversation_id=g')
                foreign.exception.close()
            finally:
                child.send_signal(signal.SIGTERM)
                try:code=child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill();child.wait();self.fail('Fixture server did not gracefully stop')
            self.assertEqual(code,0)

"""Optional DWS event wakeups. History remains authoritative for message/media content."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import threading
import time
from contextlib import ExitStack
from .dws_access import DWSAccess, DWSAccessSuspended, SupervisedDWS, credential_failure


class StreamListener:
    def __init__(self,root,config,wake):
        self.root=Path(root);self.config=config;self.wake=wake;self.lock=threading.Lock()
        self.access=DWSAccess(root)
        self.state={'enabled':True,'state':'stopped','ready':False,'ever_ready':False,'accepted_hints':0,'rejected_lines':0,'connections':0}

    def status(self):
        with self.lock:return dict(self.state)

    def update(self,**values):
        with self.lock:self.state.update(values)

    def command(self,duration):
        direct=self.config.get('conversationType','group')=='direct'
        args=['event','consume','user_im_message_receive_o2o' if direct else 'user_im_message_receive_group',
              '--open-dingtalk-id' if direct else '--group',
              self.config['peerOpenDingTalkId'] if direct else self.config['group'],
              '--flatten','--format','ndjson','--duration',str(duration)+'s',
              '--profile',self.config['profile']]
        return [str((self.root/self.config['binary']).resolve()),*args]

    def line(self,stream,line):
        if stream=='stderr':
            if line.startswith('[event] ready'):
                self.update(ready=True,ever_ready=True,state='listening');self.wake()
            return
        try:
            value=json.loads(line)
            if not isinstance(value,dict) or value.get('conversation_id')!=self.config['group']:
                raise ValueError('Foreign/missing conversation')
            if not isinstance(value.get('message_id'),str) or not value['message_id']:
                raise ValueError('Missing message ID')
        except (ValueError,TypeError):
            with self.lock:self.state['rejected_lines']+=1
            return
        with self.lock:
            self.state['accepted_hints']+=1
            self.state['last_hint_at']=time.time()
        # No event body is delivered as a complete message. DWS documents media
        # event content as potentially descriptive only. Committed history dedups it.
        self.wake()

    def run_once(self,stop,duration=3600,handshake_timeout=90):
        lease_stack=ExitStack()
        lease=lease_stack.enter_context(self.access.lease(stop,operation='stream'))
        self.update(state='connecting',ready=False)
        with self.lock:self.state['connections']+=1
        owned=None;sel=selectors.DefaultSelector();buffers={};terminating=None
        captured={'stdout':b'','stderr':b''};handshake=True
        started=time.monotonic()
        def consume(stream, raw):
            nonlocal handshake
            self.line(stream, raw.decode('utf-8', errors='replace'))
            if handshake and self.status()['ready']:
                lease.complete();lease_stack.close();handshake=False
        try:
            owned=SupervisedDWS(self.command(duration),self.root,keep_stdin_open=True);process=owned.process
            for stream,pipe in [('stdout',process.stdout),('stderr',process.stderr)]:
                os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,stream);buffers[stream]=b''
            deadline=time.monotonic()+duration+30
            while sel.get_map():
                now=time.monotonic()
                suspended=self.access.status()['state']=='suspended'
                if handshake and now-started>=handshake_timeout:
                    lease.block('dws_timeout');suspended=True
                if (stop.is_set() or suspended or now>=deadline) and terminating is None:
                    owned.stop();terminating=now
                if terminating is not None and now-terminating>15:
                    lease.block('dws_cleanup_incomplete')
                    raise DWSAccessSuspended('dws_cleanup_incomplete')
                for key,_ in sel.select(.2):
                    chunk=os.read(key.fileobj.fileno(),65536);stream=key.data
                    if not chunk:
                        if buffers[stream]:consume(stream,buffers[stream])
                        buffers[stream]=b'';sel.unregister(key.fileobj);continue
                    captured[stream]=(captured[stream]+chunk)[-65536:]
                    buffers[stream]+=chunk
                    if len(buffers[stream])>1024*1024:
                        owned.stop();terminating=now;buffers[stream]=b''
                        self.update(state='oversized_event');continue
                    while b'\n' in buffers[stream]:
                        raw,buffers[stream]=buffers[stream].split(b'\n',1)
                        consume(stream,raw)
            code=process.wait(timeout=15)
            for raw in captured.values():
                # The official CLI may emit pretty-printed JSON on stderr.
                # Decode only whole objects beginning at a line boundary.
                text=raw.decode('utf-8',errors='replace')
                for offset in [0]+[i+1 for i,c in enumerate(text) if c=='\n']:
                    try:data,_=json.JSONDecoder().raw_decode(text[offset:].lstrip())
                    except ValueError:continue
                    if credential_failure(data):lease.block('credential_store_unavailable')
            if self.access.status()['state']=='suspended':
                raise DWSAccessSuspended(self.access.status()['reason'])
            if handshake:lease.complete()
            self.update(state='stopped' if stop.is_set() or code==0 else 'disconnected',ready=False,exit_code=code)
            return code
        finally:
            sel.close()
            try:
                if owned is not None:owned.close()
            except DWSAccessSuspended as exc:
                lease.block(exc.reason);raise
            finally:lease_stack.close()

    def run(self,stop):
        delay=1
        while not stop.is_set():
            started=time.monotonic()
            try:self.run_once(stop)
            except DWSAccessSuspended as exc:
                self.update(state='suspended',ready=False,error=exc.reason)
                while not stop.wait(.5):
                    if self.access.status()['state']=='ready':break
                continue
            except Exception as exc:
                if self.status()['state']=='cleanup_pending':return
                self.update(state='error',ready=False,error=type(exc).__name__)
            if stop.is_set():break
            self.update(state='reconnecting',ready=False)
            if stop.wait(delay):break
            delay=1 if time.monotonic()-started>60 else min(delay*2,60)

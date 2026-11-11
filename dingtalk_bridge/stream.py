"""Optional DWS event wakeups. History remains authoritative for message/media content."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import threading
import time


class StreamListener:
    def __init__(self,root,config,wake):
        self.root=Path(root);self.config=config;self.wake=wake;self.lock=threading.Lock()
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

    def run_once(self,stop,duration=3600):
        self.update(state='connecting',ready=False)
        with self.lock:self.state['connections']+=1
        process=subprocess.Popen(self.command(duration),cwd=self.root,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        sel=selectors.DefaultSelector();buffers={};terminating=None
        for stream,pipe in [('stdout',process.stdout),('stderr',process.stderr)]:
            os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,stream);buffers[stream]=b''
        deadline=time.monotonic()+duration+30
        try:
            while sel.get_map():
                now=time.monotonic()
                if (stop.is_set() or now>=deadline) and terminating is None:
                    if process.poll() is None:process.terminate()
                    terminating=now
                if terminating is not None and now-terminating>30 and process.poll() is None:
                    self.update(state='cleanup_pending',ready=False)
                    raise RuntimeError('DWS did not gracefully stop; no force-kill or reconnect')
                for key,_ in sel.select(.2):
                    chunk=os.read(key.fileobj.fileno(),65536);stream=key.data
                    if not chunk:
                        if buffers[stream]:self.line(stream,buffers[stream].decode('utf-8',errors='replace'))
                        buffers[stream]=b'';sel.unregister(key.fileobj);continue
                    buffers[stream]+=chunk
                    if len(buffers[stream])>1024*1024:
                        process.terminate();terminating=now;buffers[stream]=b''
                        self.update(state='oversized_event');continue
                    while b'\n' in buffers[stream]:
                        raw,buffers[stream]=buffers[stream].split(b'\n',1)
                        self.line(stream,raw.decode('utf-8',errors='replace'))
            code=process.wait(timeout=30)
            self.update(state='stopped' if stop.is_set() or code==0 else 'disconnected',ready=False,exit_code=code)
            return code
        finally:
            sel.close()
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    self.update(state='cleanup_pending',ready=False)
            for pipe in (process.stdin,process.stdout,process.stderr):pipe.close()

    def run(self,stop):
        delay=1
        while not stop.is_set():
            started=time.monotonic()
            try:self.run_once(stop)
            except Exception as exc:
                if self.status()['state']=='cleanup_pending':return
                self.update(state='error',ready=False,error=type(exc).__name__)
            if stop.is_set():break
            self.update(state='reconnecting',ready=False)
            if stop.wait(delay):break
            delay=1 if time.monotonic()-started>60 else min(delay*2,60)

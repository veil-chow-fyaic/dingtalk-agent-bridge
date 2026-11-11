#!/usr/bin/env python3
"""Bounded, read-only event capture for configured routes; raw data stays in local/."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.stream import StreamListener


def main():
    os.umask(0o077);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=int,default=300);p.add_argument('--run-id',required=True);a=p.parse_args()
    if not 10<=a.seconds<=3600 or not a.run_id.replace('-','').isalnum():p.error('Invalid capture duration/run ID')
    folder=ROOT/'local/event-captures'/a.run_id;folder.mkdir(parents=True,exist_ok=False)
    stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    listeners=[];threads=[];wakeups=[0];guard=threading.Lock()
    def wake():
        with guard:wakeups[0]+=1
    for index,(cfg,_) in enumerate(route_configs(json.loads((ROOT/'local/service-config.json').read_text()))):
        listener=StreamListener(ROOT,cfg,wake);original=listener.line
        def record(stream,line,original=original,index=index):
            with (folder/(str(index)+'.ndjson')).open('a') as f:
                f.write(json.dumps({'observedAt':time.time(),'stream':stream,'line':line},ensure_ascii=False)+'\n')
            original(stream,line)
        listener.line=record;listeners.append(listener)
        def run(listener=listener):
            try:listener.run_once(stop,a.seconds)
            except Exception as exc:listener.update(capture_error=type(exc).__name__)
        threads.append(threading.Thread(target=run))
    for t in threads:t.start()
    deadline=time.monotonic()+a.seconds+35
    while any(t.is_alive() for t in threads):
        report={'active':True,'wakeups':wakeups[0],'routes':[x.status() for x in listeners]}
        (folder/'status.json').write_text(json.dumps(report))
        if time.monotonic()>deadline:stop.set()
        for t in threads:t.join(.5)
    report={'active':False,'wakeups':wakeups[0],'routes':[x.status() for x in listeners]}
    (folder/'status.json').write_text(json.dumps(report));print(json.dumps(report))


if __name__=='__main__':main()

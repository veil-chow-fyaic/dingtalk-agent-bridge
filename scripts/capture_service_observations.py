#!/usr/bin/env python3
"""Bounded read-only service/event observation; private traces stay in local/."""
import argparse
import json
import os
from pathlib import Path
import signal
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]

def main():
    os.umask(0o077);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=int,default=600);p.add_argument('--run-id',required=True)
    p.add_argument('--interval',type=float,default=1,help='Sample period in seconds, 0.2..60; use 30 for a 24h watch')
    args=p.parse_args()
    if not 10<=args.seconds<=86400 or not .2<=args.interval<=60 or not args.run_id.replace('-','').isalnum():p.error('Invalid duration/run ID/interval')
    folder=ROOT/'local/service-observations'/args.run_id;folder.mkdir(parents=True,exist_ok=False)
    routes=json.loads((ROOT/'local/service-config.json').read_text())['routes']
    token=(ROOT/'local/runtime/http-token').read_text().strip()
    stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    def get(path):
        request=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token})
        with urlopen(request,timeout=8) as response:return json.load(response)
    def events(route,cursor):
        return get('/v1/events?'+urlencode({'account_id':route['accountId'],'conversation_id':route['conversationId'],
                                         'after':cursor,'limit':200}))
    cursors=[]
    # Establish a durable baseline without re-emitting old events.
    for route in routes:
        cursor=0
        while True:
            batch=events(route,cursor);cursor=batch['next_cursor']
            if len(batch['events'])<200:break
        cursors.append(cursor)
    (folder/'baseline.json').write_text(json.dumps({'at':time.time(),'cursors':cursors,'routes':routes,'health':get('/v1/health')}))
    started=time.monotonic();samples=failures=received=0
    status={'active':True,'pid':os.getpid(),'startedAt':time.time(),'duration_seconds':args.seconds,
            'interval_seconds':args.interval,'samples':0,'unavailable_samples':0,'new_events':0,'elapsed_seconds':0}
    def save_status():
        status['updatedAt']=time.time()
        temp=folder/'status.tmp';temp.write_text(json.dumps(status));temp.replace(folder/'status.json')
    save_status()
    with (folder/'observations.ndjson').open('a') as out:
        while not stop.is_set() and time.monotonic()-started<args.seconds:
            sample={'observedAt':time.time(),'events':[]}
            try:
                sample['health']=get('/v1/health')
                for index,route in enumerate(routes):
                    batch=events(route,cursors[index]);cursors[index]=batch['next_cursor']
                    sample['events'].extend({'route':index,'event':e,'firstObservedAt':time.time()} for e in batch['events'])
                    received+=len(batch['events'])
            except Exception as exc:
                failures+=1;sample['error']=type(exc).__name__
            samples+=1;out.write(json.dumps(sample,ensure_ascii=False)+'\n');out.flush()
            status.update(samples=samples,unavailable_samples=failures,new_events=received,
                          elapsed_seconds=round(time.monotonic()-started,2))
            save_status()
            stop.wait(min(args.interval,max(0,args.seconds-(time.monotonic()-started))))
    status.update(active=False,elapsed_seconds=round(time.monotonic()-started,2),
                  stop_reason='signal' if stop.is_set() else 'duration_reached')
    save_status();print(json.dumps(status))

if __name__=='__main__':main()

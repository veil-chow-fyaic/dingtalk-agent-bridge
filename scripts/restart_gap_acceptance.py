#!/usr/bin/env python3
"""Explicit single-message outage/catch-up probe; saves intent and never blind-retries."""
import argparse,json,subprocess,sys,time
from urllib.request import Request,urlopen
from probe_support import Probe,ROOT,unwrap

def api(path,data=None):
    token=(ROOT/'local/runtime/http-token').read_text().strip()
    req=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},data=None if data is None else json.dumps(data).encode())
    with urlopen(req,timeout=100) as r:return json.load(r)
def control(action):
    return subprocess.run([sys.executable,'scripts/service_ctl.py',action],cwd=ROOT,capture_output=True,text=True,timeout=115,check=True)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--run-id',required=True)
    a=parser.parse_args()
    if not a.execute:parser.error('--execute required')
    p=Probe(a.run_id); result=p.dir/'result.json'
    if result.exists(): print(result.read_text());return
    before=api('/v1/health');start=time.monotonic();group=p.config['group']
    try:
        control('stop')
        d=unwrap(p.call('offline-send-v2',['chat','+messages-send','--as','user','--group',group,'--text',
            '[DAB-RESTART-GAP-001] 限定服务停止期间发送，用于历史补读验收。','--idempotency-key','DAB-'+a.run_id,'--yes']))
        task=d.get('sendReceipt',{}).get('openTaskId') or d.get('result',{}).get('openTaskId')
        if not task: raise RuntimeError('Unknown task: reconcile, do not resend')
        status=unwrap(p.call('offline-status',['chat','+messages-query-send-status','--open-task-id',task]))
        assert status['result']['sendStatus']=='SUCCESS' and status['messageRef']['openConversationId']==group
        mid=status['messageRef']['openMessageId']
    finally:
        control('start')
    sync=api('/v1/sync',{})
    events=api('/v1/events?after=0&limit=200')['events']
    found=[e for e in events if e['message_id']==mid]
    assert sync['complete'] and len(found)==1 and found[0]['from_self'] is True
    again=api('/v1/sync',{})
    matches=[e for e in api('/v1/events?after=0&limit=200')['events'] if e['message_id']==mid]
    assert len(matches)==1 and again['inserted']==0
    report={'date':'2026-11-11','version':'v1.0.67','serviceStoppedBeforeSend':True,'sendDelivered':True,
        'restarted':True,'historyRecoveredMessage':True,'duplicateEvents':0,'fromSelfPreserved':True,
        'eventsBefore':before['events'],'eventsAfter':api('/v1/health')['events'],
        'elapsedSeconds':round(time.monotonic()-start,1),'limits':'one self message, bounded short outage; not Stream or long soak'}
    result.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(result.read_text())
if __name__=='__main__':main()

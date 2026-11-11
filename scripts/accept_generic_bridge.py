#!/usr/bin/env python3
"""Bounded read-only remote acceptance; only local caches/inbox/evidence are written."""
import json,subprocess,sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
def main():
    token=(ROOT/'local/runtime/http-token').read_text().strip()
    def api(path,data=None):
        req=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},data=None if data is None else json.dumps(data).encode())
        with urlopen(req,timeout=120) as r:return json.load(r)
    routes=api('/v1/conversations')['conversations']
    assert len(routes)==1,'Acceptance limited to existing single test route'
    scope={k:routes[0][k] for k in ('account_id','conversation_id')}
    batch=api('/v1/events?'+urlencode({**scope,'limit':200,'after':0}))
    assert len(batch['events'])==18 and all(e['from_self'] is True for e in batch['events'])
    try:api('/v1/events?'+urlencode({'account_id':'invalid-test-account','conversation_id':scope['conversation_id']}))
    except HTTPError as exc:assert exc.code==400
    else:raise AssertionError('Wrong account accepted')
    deep=api('/v1/sync',{**scope,'deep':True});assert deep['complete'] and deep['inserted']==0 and deep['deep']
    image=next(e for e in batch['events'] if e['content'].startswith('[DAB-V67-IMAGE-001]'))
    old=api('/v1/attachments',{**scope,'message_id':image['message_id']})
    repaired=api('/v1/attachments',{**scope,'message_id':image['message_id'],'repair':True})
    assert repaired['ok'] and old['downloads'][0]['sha256']==repaired['downloads'][0]['sha256']
    assert old['downloads'][0]['localPath']!=repaired['downloads'][0]['localPath']
    summaries=[]
    for _ in range(2):
        r=subprocess.run([sys.executable,'-m','dingtalk_bridge.consume','--hydrate-self'],cwd=ROOT,capture_output=True,text=True,check=True)
        summaries.append(json.loads(r.stdout))
    assert all(r['fetched']==0 and r['messages']==18 and r['selfFiltered']==18 and r['readyForRuntime']==0 and not r['withIssues'] for r in summaries)
    cli=subprocess.run([sys.executable,'-m','dingtalk_bridge.cli','conversations'],cwd=ROOT,capture_output=True,text=True,check=True)
    assert len(json.loads(cli.stdout)['conversations'])==1
    report={'date':'2026-11-11','newRemoteMessages':0,'remoteOfficeWrites':0,'cliConversationsPassed':True,
        'explicitRouteHTTPPassed':True,'wrongAccountRejected':True,'deepScan':{'complete':True,'inserted':0},
        'cacheRepair':{'newAttemptDirectory':True,'originalSha256Unchanged':True},'shadow':summaries[-1],
        'consumerRestartNoDuplicates':True,'runtimeRequired':False,
        'limits':['live read-only verification uses existing one-person test route','multi-account and direct send are deterministic tests, not remote acceptance']}
    evidence=ROOT/'evidence/2026-11-11/generic-bridge-acceptance.json'
    if evidence.exists():
        first=json.loads(evidence.read_text()).get('firstShadowPass')
        if first:report['firstShadowPass']=first
    evidence.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

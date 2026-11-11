#!/usr/bin/env python3
"""Read-only remote acceptance of the two recorded DAB Agent tasks; never sends or reruns a task."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dingtalk_bridge.message_model import media_parts
from dingtalk_bridge.routing import route_configs


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',action='store_true',help='Save private before-restart observation')
    p.add_argument('--compare-restart',action='store_true',help='Compare with private snapshot')
    p.add_argument('--write-evidence',action='store_true',help='Write sanitized acceptance evidence')
    args=p.parse_args()
    cfg=json.loads((ROOT/'local/agent-config.json').read_text())
    routes=list(route_configs(json.loads((ROOT/cfg['bridgeConfig']).read_text())))
    matches=[r for r,_ in routes if r['accountId']==cfg['accountId'] and r['group']==cfg['conversationId']]
    assert len(matches)==1
    route=matches[0]
    scope=json.dumps([route['accountId'],route['profile'],route['group'],route.get('conversationType','group')])
    local=ROOT/'local/agents'/hashlib.sha256(scope.encode()).hexdigest()[:24]
    db=sqlite3.connect((local/'tasks.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    jobs=[]
    for marker in ['[DAB-AGENT-TASK-001]','[DAB-AGENT-TASK-002]']:
        rows=db.execute('SELECT * FROM jobs WHERE instr(command,?)>0',(marker,)).fetchall()
        assert len(rows)==1 and rows[0]['state']=='completed',marker
        jobs.append(dict(rows[0]))
    rows=[dict(r) for j in jobs for r in db.execute('SELECT * FROM outbox WHERE job_id=? ORDER BY key',(j['id'],))]
    assert len(rows)==5 and all(r['state']=='confirmed' for r in rows)
    results=[json.loads(j['result']) for j in jobs]
    assert '青竹731' in results[1]['response']['text']
    native=[];eventlogs=[]
    for j in jobs:
        path=local/'runs'/j['id']/'events.jsonl'
        events=[json.loads(x) for x in path.read_text().splitlines()]
        native.append([e['session_id'] for e in events if e.get('type')=='session.resume_hint'][-1])
        eventlogs.append(events)
    assert native[0]==native[1]
    assert not any(e.get('tool_calls') or e.get('role')=='tool' for e in eventlogs[1])
    parts=list(media_parts(json.loads(jobs[0]['model'])))
    assert len(parts)==1 and parts[0]['name']=='dab-file-001.txt'
    assert digest(Path(parts[0]['path']))==parts[0]['sha256']
    copied=list((local/'workspaces').glob('*/inputs/'+jobs[0]['id']+'/*'))
    assert len(copied)==1 and digest(copied[0])==parts[0]['sha256']
    artifact=results[0]['artifacts'][0];staged=ROOT/artifact['file']
    assert digest(staged)==artifact['sha256']
    assert all(s in staged.read_text() for s in ['DAB-FILE-001','青竹731','ASCII'])
    token=(ROOT/'local/runtime/http-token').read_text().strip()
    def api(path,data=None):
        scope={'account_id':cfg['accountId'],'conversation_id':cfg['conversationId']}
        if data is None:path+='?'+urlencode(scope)
        else:data={**data,**scope}
        req=Request('http://127.0.0.1:18768'+path,data=None if data is None else json.dumps(data).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urlopen(req,timeout=120) as r:return json.load(r)
    # Refresh history and download the already-confirmed artifact; these do not send messages.
    api('/v1/sync',{})
    file_row=next(r for r in rows if 'file' in json.loads(r['payload']))
    downloaded=api('/v1/attachments',{'message_id':json.loads(file_row['receipt'])['message_id']})
    assert downloaded['ok'] and not downloaded.get('partial') and len(downloaded['downloads'])==1
    assert digest(ROOT/downloaded['downloads'][0]['localPath'])==artifact['sha256']
    health=api('/v1/health')
    current={'jobs':jobs,'outbox':rows,'sessions':native,
        'logs':{j['id']:digest(local/'runs'/j['id']/'events.jsonl') for j in jobs}}
    snapshot=local/'acceptance-before-restart.json'
    if args.snapshot:snapshot.write_text(json.dumps(current,ensure_ascii=False));snapshot.chmod(0o600)
    restart_verified=False
    if args.compare_restart:
        assert json.loads(snapshot.read_text())==current,'Recorded tasks, sessions or deliveries changed across restart'
        restart_verified=True
    summary={'date':'2026-11-11','scope':'original authorized single-member group; explicit owner /agent commands',
        'runtime':'kimi','runtimeVersion':eventlogs[0][0]['version'],
        'completedTasks':2,'confirmedAgentDeliveries':5,
        'observedBridgeEvents':health['events'],'bridgePollError':health['poll_error'],
        'checks':{'quotedAttachmentDownloaded':True,'inputCopyHashMatches':True,
            'realGeneratedReportHasSourceSummary':True,'returnedFileDownloadedAndHashMatches':True,
            'sameNativeSessionAcrossTurns':True,'followupRecallsCodeWithoutTools':True,
            'restartNoTaskReplayOrResend':restart_verified},
        'outputSha256':artifact['sha256'],
        'skipped':['independent sender','direct conversation live test','multi-member group','external conversation'],
        'limits':['DWS history polling','Kimi prompt auto permission is not an OS sandbox','Codex model request timed out'],
        'verificationDoesNotSendMessages':True}
    if args.write_evidence:
        assert restart_verified,'Write final evidence only with explicit restart comparison'
        (ROOT/'evidence/2026-11-11/local-agent-loop.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    db.close()


if __name__=='__main__':main()

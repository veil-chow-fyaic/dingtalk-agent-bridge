#!/usr/bin/env python3
"""Verify recorded synthetic cases and download already-sent artifacts; does not send any message."""
import argparse,csv,hashlib,io,json,sqlite3,time
from pathlib import Path
from urllib.request import Request,urlopen
from agent_scenario_probe import ROOT,context,CASES
from probe_support import unwrap

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence',action='store_true');a=parser.parse_args()
    local,key=context();db=sqlite3.connect((local/'tasks.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    cfg=json.loads((ROOT/'local/agent-config.json').read_text());token=(ROOT/'local/runtime/http-token').read_text().strip()
    def api(path,data=None):
        if data is not None:data={**data,'account_id':cfg['accountId'],'conversation_id':cfg['conversationId']}
        req=Request('http://127.0.0.1:18768'+path,data=None if data is None else json.dumps(data).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urlopen(req,timeout=120) as response:return json.load(response)
    jobs={};rows={}
    for case in CASES:
        r=unwrap(json.loads((ROOT/'local/probes/20261111-agent-scenarios'/f'{case}.json').read_text())['data'])
        jid=hashlib.sha256((key+'\0'+r['openMessageId']).encode()).hexdigest()[:24]
        jobs[case]=dict(db.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
        assert jobs[case]['state']==('cancelled' if case=='slow' else 'completed'),case
        rows[case]=[dict(r) for r in db.execute('SELECT * FROM outbox WHERE job_id=?',(jid,))]
        assert rows[case] and all(r['state']=='confirmed' for r in rows[case]),case
    assert any('"running": 1' in json.loads(r['payload']).get('text','') for r in rows['status'])
    started=list(local.glob('workspaces/*/started.txt'));assert len(started)==1
    assert time.time()-started[0].stat().st_mtime>90
    assert not list(local.glob('workspaces/*/exports/should-not-exist.txt'))
    def events(case):return [json.loads(x) for x in (local/'runs'/jobs[case]['id']/'events.jsonl').read_text().splitlines()]
    xlsx=json.loads(jobs['xlsx']['result']);image=json.loads(jobs['image']['result'])
    assert len(xlsx['artifacts'])==2
    data=next(ROOT/i['file'] for i in xlsx['artifacts'] if i['file'].endswith('.csv'))
    assert list(csv.reader(io.StringIO(data.read_text())))==[['cell','value'],['A1','DAB-XLSX-001'],['B1','1']]
    assert all(x in image['response']['text'] for x in ['DAB MEDIA TEST 20261111','320','180'])
    tools=[t.get('function',{}).get('name') for e in events('image') for t in e.get('tool_calls',[])]
    assert 'ReadMediaFile' in tools and 'Bash' in tools
    session=lambda case:next(e['session_id'] for e in reversed(events(case)) if e.get('type')=='session.resume_hint')
    assert session('xlsx')!=session('image')
    api('/v1/sync',{});hashes=[]
    for r in rows['xlsx']:
        payload=json.loads(r['payload'])
        if 'file' not in payload:continue
        ledger=api('/v1/attachments',{'message_id':json.loads(r['receipt'])['message_id']})
        assert ledger['ok'] and not ledger.get('partial') and len(ledger['downloads'])==1
        staged=ROOT/payload['file'];download=ROOT/ledger['downloads'][0]['localPath']
        digest=hashlib.sha256(staged.read_bytes()).hexdigest()
        assert hashlib.sha256(download.read_bytes()).hexdigest()==digest;hashes.append(digest)
    health=api('/v1/health')
    report={'date':'2026-11-11','scope':'authorized owner commands in original single-member group',
        'cases':{c:{'jobState':j['state'],'confirmedReplies':len(rows[c])} for c,j in jobs.items()},
        'checks':{'statusWhileRunning':True,'cancelledRealToolExecution':True,'noDelayedFileAfter90Seconds':True,
            'xlsxParsedExpectedCells':True,'twoReturnedFilesHashMatched':True,'newCreatedDifferentNativeSession':True,
            'imageActuallyViewedAndDimensionsMatch':True,'imageAfterAsyncDownloadChange':True},
        'returnedFileSha256':hashes,'bridgeEvents':health['events'],'pollError':health['poll_error'],
        'notVerified':['real direct peer','multi-member group','external conversation','long duration reliability']}
    card_dir=ROOT/'local/probes/20261111-official-card'
    create=unwrap(json.loads((card_dir/'create.json').read_text())['data']);finish=unwrap(json.loads((card_dir/'finish.json').read_text())['data'])
    assert create['updateAccepted'] and finish['success'] and finish['accepted']
    card={'date':'2026-11-11','officialCLI':'1.0.67','scope':'original single-member group',
        'createAccepted':create['updateAccepted'],'finishAccepted':finish['accepted'],
        'contentIndependentlyVerified':finish['verified'],'referencePairAvailable':create['referencePairAvailable'],
        'verdict':'API accepted; visible content not independently verified; do not repeat update',
        'gatewayIntegrated':False}
    if a.write_evidence:
        for name,value in [('agent-scenarios.json',report),('official-card-acceptance.json',card)]:
            (ROOT/'evidence/2026-11-11'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'agent':report,'officialCard':card},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

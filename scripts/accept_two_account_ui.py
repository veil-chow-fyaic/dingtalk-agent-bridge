#!/usr/bin/env python3
"""Read-only ledger/file audit of the already performed two-account UI test. Never sends or replays tasks."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.message_model import media_parts

PRIVATE=ROOT/'local/ui-two-account-20261111'


def digest(data):return hashlib.sha256(data).hexdigest()
def readonly(path):
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    return db


def audit():
    config=json.loads((ROOT/'local/service-config.json').read_text())
    agents=[json.loads((ROOT/name).read_text()) for name in ['local/agent-config.json','local/agent-direct-config.json']]
    report={'date':'2026-11-11','scope':'ledger and downloaded bytes; UI observations are separately recorded',
            'routes':{},'checks':{}};snap={};sessions={};commands={}
    expected={'group':['DAB-UI-GROUP-002'],'direct':['DAB-UI-DM-002','DAB-UI-DM-003','DAB-UI-INPUT-004']}
    downloads={'DAB-UI-GROUP-002':('0-ui-group-peer-check.txt','667'),
               'DAB-UI-DM-002':('0-ui-dm-check.txt','697'),
               'DAB-UI-INPUT-004':('0-ui-upload-summary.txt','54')}
    for route,state in route_configs(config):
        kind=route['conversationType'];setting=next(s for s in agents if s['accountId']==route['accountId'] and s['conversationId']==route['group'])
        scope=json.dumps([route['accountId'],route['profile'],route['group'],kind]);key=digest(scope.encode())[:24]
        directory=ROOT/'local/agents'/key
        with readonly(directory/'tasks.sqlite3') as db:
            jobs=[dict(x) for x in db.execute('SELECT * FROM jobs ORDER BY seq')]
            outbox=[dict(x) for x in db.execute('SELECT * FROM outbox ORDER BY key')]
            meta=[dict(x) for x in db.execute('SELECT * FROM meta ORDER BY key')]
        with readonly(ROOT/'local/runtime/routes'/state/'bridge.sqlite3') as db:
            events={r['message_id']:json.loads(r['body']) for r in db.execute('SELECT * FROM events WHERE seq>?',(setting['initialCursor'],))}
        checks={};models=[json.loads(j['model']) for j in jobs]
        checks['only_authorized_peer_tasks']=bool(models) and all(m['senderId'] in setting['allowedSenderIds'] and m['fromSelf'] is False for m in models)
        checks['all_jobs_completed']=bool(jobs) and all(j['state']=='completed' for j in jobs)
        checks['all_replies_confirmed']=bool(outbox) and all(o['state']=='confirmed' for o in outbox)
        checks['replies_from_bound_account']=all((e:=events.get(json.loads(o['receipt']).get('message_id'))) and e['sender_id']==route['selfSenderId'] and e['from_self'] is True for o in outbox)
        checks['self_commands_disabled']=setting['allowSelfCommands'] is False
        checks['baseline_not_executed']=all(j['seq']>setting['initialCursor'] for j in jobs)
        files=[]
        for marker in expected[kind]:
            matches=[j for j in jobs if marker in j['command']];checks[marker+'_once']=len(matches)==1
            if len(matches)!=1:continue
            result=json.loads(matches[0]['result']);response=result['response']['text']
            if marker=='DAB-UI-DM-003':checks['native_followup_memory']='蓝鲸482' in response
            if marker=='DAB-UI-GROUP-002':checks['group_does_not_contain_dm_code']='蓝鲸482' not in response and '不知道私聊暗号' in response
            if marker in downloads:
                name,answer=downloads[marker];download=PRIVATE/name;data=download.read_bytes()
                staged=next(a for a in result['artifacts'] if Path(a['file']).name==name)
                checks[marker+'_client_download_matches']=digest(data)==staged['sha256']==digest((ROOT/staged['file']).read_bytes())
                checks[marker+'_content']=marker in data.decode() and answer in data.decode()
                files.append({'name':name,'bytes':len(data),'sha256':digest(data)})
        if kind=='group':
            checks['ordinary_group_message_received']=any('DAB-UI-IGNORE-001' in e['content'] for e in events.values())
            checks['ordinary_group_message_not_executed']=not any('DAB-UI-IGNORE-001' in j['command'] for j in jobs)
        else:
            parts=[p for m in models for p in media_parts(m) if p.get('name')=='dab-ui-input.csv']
            checks['ui_uploaded_csv_received_intact']=len(parts)==1 and Path(parts[0]['path']).read_bytes()==(ROOT/'fixtures/dab-ui-input.csv').read_bytes()
        sessions[kind]=next(x['value'] for x in meta if x['key']=='session_id')
        logs={str(p.relative_to(directory)):digest(p.read_bytes()) for p in (directory/'runs').rglob('*') if p.is_file()}
        snap[kind]=digest(json.dumps([jobs,outbox,meta,logs],sort_keys=True).encode())
        report['routes'][kind]={'jobs':len(jobs),'confirmed_replies':len(outbox),'checks':checks,'downloaded_files':files}
        commands[kind]=[j['command'] for j in jobs]
    report['checks']['group_and_direct_native_sessions_differ']=sessions['group']!=sessions['direct']
    report['ok']=all(report['checks'].values()) and all(all(r['checks'].values()) for r in report['routes'].values())
    return report,snap


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true')
    p.add_argument('--snapshot',action='store_true');p.add_argument('--compare-restart',action='store_true');a=p.parse_args()
    report,snap=audit();snapshot=PRIVATE/'restart-before.json'
    if a.snapshot:snapshot.write_text(json.dumps(snap));snapshot.chmod(0o600)
    if a.compare_restart:
        report['checks']['restart_preserved_tasks_outbox_sessions_and_execution_logs']=snap==json.loads(snapshot.read_text())
        report['ok']=report['ok'] and all(report['checks'].values())
    if a.write_evidence:(ROOT/'evidence/2026-11-11/two-account-ui-ledger.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)


if __name__=='__main__':main()

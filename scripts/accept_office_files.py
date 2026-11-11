#!/usr/bin/env python3
"""Read-only DOCX four-direction audit. Captures are frozen; never sends/replays."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.message_model import normalize,materialize,media_parts

def read(path):return json.loads(path.read_text())
def digest(data):return hashlib.sha256(data).hexdigest()
def rows(path,query):
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;return [dict(x) for x in db.execute(query)]

def audit():
    private=ROOT/'local/office-ui-20261111';original=(ROOT/'fixtures/dab-office-001.docx').read_bytes()
    report={'date':'2026-11-11','scope':'four DOCX directions plus actual direct task and client-downloaded original/result; UI separately observed',
            'cases':[],'checks':{},'fixture':{'bytes':len(original),'sha256':digest(original)}}
    for cfg,state in route_configs(read(ROOT/'local/service-config.json')):
        route=cfg['conversationType'];cache=ROOT/'local/runtime/routes'/state
        events={x['message_id']:json.loads(x['body']) for x in rows(cache/'bridge.sqlite3','SELECT message_id,body FROM events')}
        key=digest(json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],route]).encode())[:24]
        directory=ROOT/'local/agents'/key;db=directory/'tasks.sqlite3'
        jobs=rows(db,'SELECT * FROM jobs');outbox=rows(db,'SELECT * FROM outbox')
        for direction in ('in','out'):
            saved=read(private/(route+'-docx-'+direction+'-ledger.json'));event=saved['event'];ledger=saved['ledger']
            model=materialize(normalize(event,cfg),ledger,ROOT,cache/'downloads')
            checks={'committed_event_matches':events.get(event['message_id'])==event,
                'correct_direction':event['from_self'] is (direction=='out'),
                'one_resource':len(ledger['downloads'])==1,
                'downloaded_original_intact':bool(ledger['downloads']) and all((ROOT/p['localPath']).read_bytes()==original for p in ledger['downloads']),
                'one_file_without_issues':not model['issues'] and len(list(media_parts(model)))==1}
            if direction=='out':
                receipt=read(ROOT/'local/probes/media-matrix-20261111'/(route+'-docx.json'))['receipt']
                checks['durable_send_confirmed']=receipt['state']=='confirmed' and receipt['message_id']==event['message_id']
                checks['client_download_intact']=(private/(route+'-received.docx')).read_bytes()==original
            else:
                matched=[j for j in jobs if json.loads(j['model'])['id']==event['message_id']]
                if route=='group':checks['unprefixed_file_did_not_execute']=not matched
                else:
                    checks['one_actual_task']=len(matched)==1
                    if len(matched)==1:
                        task=matched[0];result=json.loads(task['result'] or '{}')
                        checks['completed_with_file_content']=task['state']=='completed' and 'DAB-DOCX-001 synthetic attachment' in result.get('response',{}).get('text','')
                        replies=[o for o in outbox if o['job_id']==task['id']]
                        checks['ack_answer_and_file_confirmed']=len(replies)==3 and all(o['state']=='confirmed' for o in replies)
                        checks['replies_from_bound_account']=bool(replies) and all((e:=events.get(json.loads(o['receipt'] or '{}').get('message_id'))) and e['from_self'] and e['sender_id']==cfg['selfSenderId'] for o in replies)
                        artifacts=result.get('artifacts',[])
                        checks['one_result_file']=len(artifacts)==1
                        if len(artifacts)==1:
                            artifact=artifacts[0];client=private/Path(artifact['file']).name
                            checks['result_client_download_intact']=client.exists() and digest(client.read_bytes())==artifact['sha256']==digest((ROOT/artifact['file']).read_bytes())
                            checks['result_file_content_correct']=client.exists() and 'DAB-DOCX-001 synthetic attachment' in client.read_text()
            report['cases'].append({'case':route+'-docx-'+direction,'checks':checks})
    report['ok']=all(all(x['checks'].values()) for x in report['cases'])
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args();report=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-11/docx-ui-ledger.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)

if __name__=='__main__':main()

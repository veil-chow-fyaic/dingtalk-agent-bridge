#!/usr/bin/env python3
"""Read-only audit of the performed PNG/PDF two-account experiment. Never sends."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.message_model import normalize,materialize,media_parts

def digest(data):return hashlib.sha256(data).hexdigest()

def audit():
    private=ROOT/'local/ui-matrix-20261111'
    report={'date':'2026-11-11','scope':'transport bytes, real event capture and actual runtime; UI observations remain separate',
            'cases':[],'stream':[],'tasks':{},'checks':{}}
    for index,(cfg,state) in enumerate(route_configs(json.loads((ROOT/'local/service-config.json').read_text()))):
        route=cfg['conversationType']; cache=ROOT/'local/runtime/routes'/state
        with sqlite3.connect((cache/'bridge.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            events={r[0]:json.loads(r[1]) for r in db.execute('SELECT message_id,body FROM events')}
        for kind in ('png','pdf'):
            original=(ROOT/'fixtures'/('dab-image-001.png' if kind=='png' else 'dab-document-001.pdf')).read_bytes()
            for direction in ('in','out'):
                case=f'{route}-{kind}-{direction}'
                saved=json.loads((private/(case+'-ledger.json')).read_text());event=saved['event']
                model=materialize(normalize(event,cfg),saved['ledger'],ROOT,cache/'downloads')
                checks={'committed_event_matches':events.get(event['message_id'])==event,
                        'sender_direction_correct':event['from_self'] is (direction=='out'),
                        'all_resource_bytes_match_fixture':all((ROOT/p['localPath']).read_bytes()==original for p in saved['ledger']['downloads']),
                        'one_positioned_media':len(list(media_parts(model)))==1,'normalized_without_issues':not model['issues']}
                report['cases'].append({'case':case,'resources':len(saved['ledger']['downloads']),
                    'bytes':len(original),'sha256':digest(original),'checks':checks})
        captures=[]
        for line in (ROOT/f'local/event-captures/ui-matrix-20261111/{index}.ndjson').read_text().splitlines():
            record=json.loads(line)
            if record['stream']!='stdout':continue
            event=json.loads(record['line'])
            assert event['conversation_id']==cfg['group']
            captures.append((event,record['observedAt']))
        delays=[round(observed-event['event_time']/1000,3) for event,observed in captures]
        report['stream'].append({'route':route,'events':len(captures),
            'all_in_committed_history':all(e['message_id'] in events for e,_ in captures),
            'unique_message_ids':len({e['message_id'] for e,_ in captures}),
            'event_clock_to_local_seconds':{'min':min(delays),'max':max(delays)},
            'schema':sorted(captures[0][0])})
        key=digest(json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],route]).encode())[:24]
        with sqlite3.connect((ROOT/'local/agents'/key/'tasks.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row;jobs=[dict(x) for x in db.execute('SELECT * FROM jobs')]
        marker='DAB-MATRIX-IMAGE-GROUP-002' if route=='group' else 'DAB-MATRIX-IMAGE-FIX-001'
        matches=[j for j in jobs if marker in j['command']]
        ok=False;aliases=False
        if len(matches)==1 and matches[0]['state']=='completed':
            result=json.loads(matches[0]['result']);text=result['response']['text']
            ok=all(x in text for x in ('DAB MEDIA TEST 20261111','320','180'))
            model=json.loads(matches[0]['model'])
            aliases=all(a.get('verified') is True for a in model.get('imageAliasCandidates',[]))
        report['tasks'][route]={'marker':marker,'completed_once_with_correct_answer':ok,
                               'aliases_verified_when_present':aliases,
                               'image_alias_candidates':len(json.loads(matches[0]['model']).get('imageAliasCandidates',[])) if len(matches)==1 else None,
                               'historical_blocked_jobs':sum(j['state']=='blocked' for j in jobs)}
        if route=='group':report['checks']['ordinary_group_event_not_executed']=not any('DAB-MATRIX-EVENT-GROUP-001' in j['command'] for j in jobs)
        else:
            fixed=json.loads((private/'pure-image-fix-job.json').read_text())
            pure=next(j for j in jobs if j['id']==fixed['id'] and j['seq']==fixed['seq'])
            model=json.loads(pure['model']);candidates=model.get('imageAliasCandidates',[])
            image_hash=digest((ROOT/'fixtures/dab-image-001.png').read_bytes())
            report['checks']['pure_native_image_retest_completed_with_verified_alias']=pure['state']=='completed' and len(candidates)==1 and candidates[0].get('verified') is True and candidates[0]['sha256']==image_hash
            answer=json.loads(pure['result'])['response']['text'] if pure['result'] else ''
            report['checks']['pure_native_image_retest_correct_answer']=all(x in answer for x in ('DAB MEDIA TEST 20261111','320','180'))
    received=private/'direct-received.pdf'
    report['checks']['direct_client_download_matches_pdf']=received.exists() and received.read_bytes()==(ROOT/'fixtures/dab-document-001.pdf').read_bytes()
    report['ok']=all(all(x['checks'].values()) for x in report['cases']) and all(report['checks'].values()) and all(
        s['all_in_committed_history'] and s['events']==s['unique_message_ids'] for s in report['stream']) and all(
        t['completed_once_with_correct_answer'] and t['aliases_verified_when_present'] for t in report['tasks'].values())
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args()
    report=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-11/media-matrix-ledger.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)

if __name__=='__main__':main()

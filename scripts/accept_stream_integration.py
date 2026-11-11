#!/usr/bin/env python3
"""Read-only audit of frozen UI Stream/recovery experiments. Never sends or restarts."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dingtalk_bridge.routing import route_configs

PRIVATE=ROOT/'local/stream-integration-20261111'
WATCH=ROOT/'local/service-observations/stream-ui-20261111'

def read(path):return json.loads(path.read_text())
def digest(data):return hashlib.sha256(data).hexdigest()
def rows(path,query):
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        return [dict(x) for x in db.execute(query)]
def epoch(timestamp):
    return datetime.strptime(timestamp,'%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()

def audit():
    samples=[json.loads(line) for line in (WATCH/'observations.ndjson').read_text().splitlines()]
    seen=[(sample,event) for sample in samples for event in sample.get('events',[])]
    baseline=read(PRIVATE/'offline-before.json')
    stopped=read(PRIVATE/'offline-confirmed.json')['at']
    restart=read(PRIVATE/'offline-restart.json')['restartRequestedAt']
    reconnect=read(PRIVATE/'reconnect-ready.json')
    before_reconnect=read(PRIVATE/'reconnect-before.json')
    report={'date':'2026-11-11','scope':'five UI-originated messages, committed history, runtime/outbox, short service outage and one owned subscriber restart',
        'cases':[],'routes':{},'checks':{},'observation':read(WATCH/'status.json'),
        'limitations':['UI screenshots are separately observed and retained locally',
            'Message timestamps have second precision; first-observed delay includes the 1-second sampling interval and uncalibrated clocks',
            'Controlled graceful process interruption is not a real network partition, token expiry or 24-hour reliability result']}
    cases={'group':[('LIVE-GROUP',None),('OFFLINE-GROUP','离线群聊已补回。'),('RECONNECT-GROUP',None)],
           'direct':[('LIVE-DM','实时私聊已收到。'),('OFFLINE-DM','离线私聊已补回。')]}
    sessions={}
    for index,(cfg,state) in enumerate(route_configs(read(ROOT/'local/service-config.json'))):
        route=cfg['conversationType']
        events=[{'seq':x['seq'],**json.loads(x['body'])} for x in rows(ROOT/'local/runtime/routes'/state/'bridge.sqlite3','SELECT seq,body FROM events')]
        key=digest(json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],route]).encode())[:24]
        directory=ROOT/'local/agents'/key;db=directory/'tasks.sqlite3'
        jobs=rows(db,'SELECT * FROM jobs');outbox=rows(db,'SELECT * FROM outbox');meta=rows(db,'SELECT * FROM meta')
        prior=baseline['routes'][route]
        route_checks={'old_jobs_unchanged':all(x in jobs for x in prior['jobs']),
            'old_outbox_unchanged':all(x in outbox for x in prior['outbox']),
            'binding_generation_and_session_unchanged':all(x in meta for x in prior['meta']),
            'old_execution_logs_unchanged':bool(prior['logs']) and all((directory/p).exists() and digest((directory/p).read_bytes())==h for p,h in prior['logs'].items())}
        sessions[route]=next(x['value'] for x in meta if x['key']=='session_id')
        report['routes'][route]={'checks':route_checks,'historical_jobs_preserved':len(prior['jobs']),
            'historical_outbox_preserved':len(prior['outbox']),'historical_run_files_preserved':len(prior['logs'])}
        for suffix,answer in cases[route]:
            marker='DAB-STREAM-'+suffix+'-001'
            matches=[e for e in events if not e['from_self'] and marker in e['content']]
            observed=[(s,e) for s,e in seen if e['route']==index and marker in e['event']['content'] and not e['event']['from_self']]
            tasks=[j for j in jobs if marker in j['command']]
            checks={'committed_once':len(matches)==1,'observed_once':len(observed)==1,'expected_task_count':len(tasks)==(1 if answer else 0)}
            details={}
            if len(matches)==len(observed)==1:
                event=matches[0];sample,ob=observed[0]
                checks['committed_body_matches_observation']=event==ob['event']
                details['first_observed_delay_seconds']=round(ob['firstObservedAt']-epoch(event['timestamp']),3)
                details['poll_trigger_at_observation']=sample['health']['poll_scheduler']['last_trigger']
                if suffix.startswith('OFFLINE'):
                    checks['sent_while_confirmed_offline']=stopped<=epoch(event['timestamp'])<restart
                    checks['observed_after_restart']=ob['firstObservedAt']>restart
                else:
                    listener=next(x for x in sample['health']['stream_listeners'] if x['conversation_id']==cfg['group'])
                    checks['business_hint_seen']=listener['accepted_hints']>0 and epoch(event['timestamp'])<=listener['last_hint_at']<=ob['firstObservedAt']
                    checks['history_polled_by_stream_hint']=details['poll_trigger_at_observation']=='stream_hint'
                    if suffix.startswith('RECONNECT'):
                        checks['observed_after_reconnect']=ob['firstObservedAt']>reconnect['at']
                        checks['subscriber_connected_again']=listener['connections']>=2 and listener['ready']
            if answer and len(tasks)==1:
                task=tasks[0];model=json.loads(task['model'])
                settings=read(ROOT/('local/agent-config.json' if route=='group' else 'local/agent-direct-config.json'))
                checks['authorized_peer_task']=model['senderId'] in settings['allowedSenderIds'] and model['fromSelf'] is False
                checks['completed_with_expected_answer']=task['state']=='completed' and json.loads(task['result'] or '{}').get('response',{}).get('text','').strip()==answer
                replies=[o for o in outbox if o['job_id']==task['id']]
                checks['ack_and_result_confirmed_once']=len(replies)==2 and all(o['state']=='confirmed' for o in replies)
                checks['final_reply_once']=sum(json.loads(o['payload']).get('text','').strip()=='[Agent] '+answer for o in replies)==1
                by_id={e['message_id']:e for e in events}
                checks['replies_from_bound_account']=bool(replies) and all((e:=by_id.get(json.loads(o['receipt'] or '{}').get('message_id'))) and e['from_self'] and e['sender_id']==cfg['selfSenderId'] for o in replies)
            report['cases'].append({'case':marker,'route':route,'checks':checks,**details})
    retained=read(PRIVATE/'reconnect-parent-retained.json')
    report['checks']={'separate_native_sessions':sessions['group']!=sessions['direct'],
        'all_observed_event_ids_unique':len({(e['route'],e['event']['message_id']) for _,e in seen})==len(seen),
        'offline_window_confirmed':read(PRIVATE/'offline-confirmed.json')['http_connection_refused'] and read(PRIVATE/'offline-restart.json')['stillOfflineAfterBothSent'],
        'outage_observed_by_independent_reader':any('error' in s and stopped<s['observedAt']<restart for s in samples),
        'subscriber_reconnected_without_service_restart':retained['ownedCommandValidated'] and retained['servicePid']==before_reconnect['servicePid'] and before_reconnect['health']['poll_scheduler']['cycles']<=reconnect['health']['poll_scheduler']['cycles'] and
            any(s['connections']>=2 and s['ready'] for s in reconnect['health']['stream_listeners'])}
    report['ok']=all(report['checks'].values()) and all(all(c['checks'].values()) for c in report['cases']) and all(all(r['checks'].values()) for r in report['routes'].values())
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args()
    report=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-11/stream-integration-ledger.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)

if __name__=='__main__':main()

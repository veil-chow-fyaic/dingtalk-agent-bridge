#!/usr/bin/env python3
"""Read-only quoted-source preservation audit; no inbound UI success claim."""
import argparse
import json
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.message_model import normalize
from dingtalk_bridge.routing import route_configs


def audit():
    f=ROOT/'local/quote-identity-20261112'
    before,after,projections=(read(f/n) for n in ('before.json','after-deploy.json','offline-projections.json'))
    checks={};count=0
    for cfg,state in route_configs(read(ROOT/'local/service-config.json')):
        kind=cfg['conversationType'];old,end=before['routes'][kind],after['routes'][kind]
        key=digest(json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],kind]).encode())[:24]
        agent=ROOT/'local/agents'/key;transport=ROOT/'local/runtime/routes'/state/'bridge.sqlite3'
        for table,db,identity in [('jobs',agent/'tasks.sqlite3','id'),('outbox',agent/'tasks.sqlite3','key'),('deliveries',transport,'key')]:
            live={r[identity]:r for r in rows(db,table)}
            checks[kind+'_'+table+'_preserved']=bool(old[table]) and all(live.get(r[identity])==r for r in old[table])
        checks[kind+'_no_tasks_or_messages_at_deploy']=all(old[t]==end[t] for t in ('jobs','outbox','meta','deliveries','events'))
        checks[kind+'_old_logs_preserved']=all((ROOT/p).is_file() and digest((ROOT/p).read_bytes())==sha for p,sha in old['runtimeFiles'].items())
        part=next(x for x in projections if x['kind']==kind)
        originals=[{**json.loads(r['body']),'seq':r['seq']} for r in old['events'] if json.loads(r['body']).get('raw',{}).get('quotedMessage')]
        checks[kind+'_exact_existing_official_events']=bool(originals) and part['batch']==originals
        checks[kind+'_exact_models_and_ids']=len(part['models'])==len(originals) and all(m==normalize(e,cfg) and m['quote']['id']==e['raw']['quotedMessage']['messageId'] and m['quote']['conversationId']==cfg['group'] and m['quote']['senderName']==e['raw']['quotedMessage']['sender'] and m['quote']['senderId'] is None for m,e in zip(part['models'],originals))
        db=f/'offline-consumer/local/consumers'/('quote-'+kind)/'inbox.sqlite3'
        checks[kind+'_durable_shadow_models']=part['restart_unchanged'] and [json.loads(r['model']) for r in rows(db,'inbox')]==part['models']
        count+=len(originals)
    old,new=(read(f/n) for n in ('manager-before.json','manager-after.json'))
    pids=lambda s:{c['component']:c['pid'] for c in s['components']}
    checks['transport_pid_preserved']=pids(old)['transport']==pids(new)['transport']
    checks['two_agents_restarted_and_running']=new['all_running'] and all(pids(old)[n]!=pids(new)[n] for n in ('agent-1','agent-2'))
    checks['observer_origin_preserved']=before['observer']['startedAt']==after['observer']['startedAt']
    checks['doctor_passed']=read(f/'doctor.json')['ok']
    install=read(ROOT/'evidence/2026-11-12/quote-identity-install.json')
    checks['installed_modules_match_frozen_source']=install['ok'] and all(digest((f/'clean-source/dingtalk_bridge'/name).read_bytes())==sha for name,sha in install['codeSha256'].items())
    checks['154_regressions_passed']='Ran 154 tests' in (f/'regression.log').read_text() and (f/'regression.log').read_text().strip().endswith('OK')
    checks['pre_fix_missing_metadata_reproduced']="KeyError: 'id'" in (f/'before-fix.log').read_text() and 'FAILED (errors=3)' in (f/'before-fix.log').read_text()
    return {'date':'2026-11-12','checks':checks,'passed':all(checks.values()),'existing_quote_samples':count,
            'inbound_quote_ui_passed':False,'limits':['Offline replay of existing official events; no new inbound native quote',
            'Historical live inbox/job models are not rewritten','Display names are not sender IDs or authorization']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args();r=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-12/quote-identity-ledger.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['passed'] else 1)

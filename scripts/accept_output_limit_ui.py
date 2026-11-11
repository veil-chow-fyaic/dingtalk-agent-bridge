#!/usr/bin/env python3
"""Read-only native UI output-limit failure and new compressed delivery audit."""
import argparse
import json
import zipfile
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    f=ROOT/'local/output-limit-ui-20261112'
    before,final,cases=(read(f/n) for n in ('before.json','final.json','cases.json'))
    checks={}
    for cfg,state in route_configs(read(ROOT/'local/service-config.json')):
        kind=cfg['conversationType'];old,end=before['routes'][kind],final['routes'][kind]
        key=digest(json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],kind]).encode())[:24]
        agent=ROOT/'local/agents'/key;transport=ROOT/'local/runtime/routes'/state/'bridge.sqlite3'
        for table,db,identity in [('jobs',agent/'tasks.sqlite3','id'),('outbox',agent/'tasks.sqlite3','key'),('deliveries',transport,'key')]:
            current={r[identity]:r for r in rows(db,table)}
            checks[kind+'_'+table+'_preserved']=bool(old[table]) and all(current.get(r[identity])==r for r in old[table])
        checks[kind+'_old_logs_preserved']=all((ROOT/p).is_file() and digest((ROOT/p).read_bytes())==sha for p,sha in old['runtimeFiles'].items())
        if kind=='group':checks['group_unchanged']=all(old[t]==end[t] for t in ('jobs','outbox','meta','deliveries','events'))
        else:
            direct=cfg;workspace=agent/'workspaces/1'
            jobs,outbox=rows(agent/'tasks.sqlite3','jobs'),rows(agent/'tasks.sqlite3','outbox')
            events={r['message_id']:json.loads(r['body']) for r in rows(transport,'events')}
    tools=[]
    for i,c in enumerate(cases):
        model=json.loads(c['job']['model']);intent=read(f/('intent.json' if i==0 else 'recovery-intent.json'))
        checks[f'case_{i}_immutable_job_and_exact_input']=c['job'] in jobs and events.get(model['id'])==c['event'] and c['event']['from_self'] is False and c['event']['sender_id'] in read(ROOT/'local/agent-direct-config.json')['allowedSenderIds'] and model['parts'][0]['text'].strip()==intent['prompt']
        checks[f'case_{i}_confirmed_replies']=len(c['outbox'])==(2 if i==0 else 3) and all(r in outbox and r['state']=='confirmed' for r in c['outbox'])
        checks[f'case_{i}_self_replies_no_echo']=len(c['replyEvents'])==len(c['outbox']) and all(events.get(e['message_id'])==e and e['from_self'] is True and e['sender_id']==direct['selfSenderId'] and not any(json.loads(j['model'])['id']==e['message_id'] for j in jobs) for e in c['replyEvents'])
        log=ROOT/c['runLog'];logs=[json.loads(s) for s in log.read_text().splitlines()]
        checks[f'case_{i}_immutable_actual_python_tool']=digest(log.read_bytes())==c['runLogSha256'] and any(call['function']['name']=='Bash' and 'python3' in call['function']['arguments'] for e in logs for call in e.get('tool_calls',[]))
        tools.append(logs)
        checks[f'case_{i}_one_native_send']=read(f/('send-attempt.json' if i==0 else 'recovery-send-attempt.json'))['attempts']==1
    failed,recovered=cases
    checks['original_terminal_failure_preserved']=failed['job']['state']=='failed' and failed['job']['error']=='ArtifactTooLarge' and failed['job']['result'] is None
    payloads=[json.loads(r['payload']) for r in failed['outbox']]
    checks['no_oversized_or_partial_result_sent']=all(set(p)=={'text'} for p in payloads) and not (ROOT/'local/outbox/agent'/failed['job']['id']).exists()
    notice=next((p['text'] for p in payloads if '20 MiB' in p.get('text','')),'')
    checks['actionable_limit_notice_visible']=bool(notice) and '未发送结果文件' in notice and '压缩或拆分' in notice and notice in (f/'failure.ax.txt').read_text()
    source=read(f/'source-before-recovery.json');data=(ROOT/source['path']).read_bytes()
    checks['actual_21mib_source_generated_and_preserved']=len(data)==21*1024*1024 and data==b'L'*(21*1024*1024) and digest(data)==source['sha256'] and (ROOT/source['path']).stat().st_mtime_ns==source['mtime_ns'] and any(e.get('role')=='tool' and e.get('content','').strip()==str(len(data)) for e in tools[0])
    checks['runtime_requested_oversized_export']=any(e.get('role')=='assistant' and e.get('content') and json.loads(e['content']).get('files')==['exports/dab-limit-21m.bin'] for e in tools[0] if e.get('content','').startswith('{'))
    result=json.loads(recovered['job']['result']);artifact=result['artifacts'][0];client=(f/'0-dab-limit-recovered.zip').read_bytes()
    checks['new_compressed_task_completed']=recovered['job']['state']=='completed' and recovered['job']['seq']>failed['job']['seq'] and result['response']['files']==['exports/dab-limit-recovered.zip'] and len(result['artifacts'])==1
    checks['client_export_stage_exact']=len(client)==21550 and client==(ROOT/artifact['file']).read_bytes()==(workspace/'exports/dab-limit-recovered.zip').read_bytes() and digest(client)==artifact['sha256']
    resources=read(f/'resources.json')
    checks['official_resource_exact']=resources['ok'] and bool(resources['downloads']) and all((ROOT/r['localPath']).read_bytes()==client for r in resources['downloads'])
    with zipfile.ZipFile(f/'0-dab-limit-recovered.zip') as z:
        checks['zip_exact_single_original']=z.namelist()==['dab-limit-21m.bin'] and z.read('dab-limit-21m.bin')==data
    checks['native_unpacked_original_exact']=(f/'dab-limit-21m.bin').read_bytes()==data and 'dab-limit-21m.bin' in (f/'zip-opened-loaded.ax.txt').read_text()
    checks['compression_tool_and_counts']=any('ZIP_DEFLATED' in c['function']['arguments'] and 'zf.write(src' in c['function']['arguments'] for e in tools[1] for c in e.get('tool_calls',[])) and all(str(n) in result['response']['text'] for n in (len(data),len(client)))
    checks['recovery_reply_and_file_native_ui']=result['response']['text'] in (f/'recovery-reply.ax.txt').read_text() and '下载 0-dab-limit-recovered.zip' in (f/'recovery-reply.ax.txt').read_text() and '打开 打开文件夹 0-dab-limit-recovered.zip' in (f/'downloaded.ax.txt').read_text()
    old,end=before['routes']['direct'],final['routes']['direct']
    checks['exact_two_new_jobs_five_replies']={j['id'] for j in end['jobs']}-{j['id'] for j in old['jobs']}=={c['job']['id'] for c in cases} and {r['key'] for r in end['outbox']}-{r['key'] for r in old['outbox']}=={r['key'] for c in cases for r in c['outbox']}
    checks['same_native_session']=bool(old['meta']) and old['meta']==end['meta']
    frames=read(f/'ui-observations.json')['frames']
    checks['reviewed_ui_frames_intact']=set(frames)=={'sent.png','failure.png','recovery-reply.png','unpacked.png'} and all(v['reviewed'] and digest((f/p).read_bytes())==v['sha256'] for p,v in frames.items())
    checks['156_regressions_passed']='Ran 156 tests' in (f/'regression.log').read_text() and (f/'regression.log').read_text().strip().endswith('OK')
    install=read(ROOT/'evidence/2026-11-12/output-limit-install.json')
    checks['clean_install_matches_frozen_source']=install['ok'] and all(digest((f/'clean-source/dingtalk_bridge'/n).read_bytes())==sha for n,sha in install['codeSha256'].items())
    old,new=(read(f/n) for n in ('manager-before.json','manager-after.json'))
    pids=lambda s:{c['component']:c['pid'] for c in s['components']}
    checks['agents_reloaded_transport_preserved']=new['all_running'] and pids(old)['transport']==pids(new)['transport'] and all(pids(old)[n]!=pids(new)[n] for n in ('agent-1','agent-2'))
    checks['observer_origin_preserved']=before['observer']['startedAt']==final['observer']['startedAt']
    return {'date':'2026-11-12','checks':checks,'passed':all(checks.values()),'sourceBytes':len(data),'sourceSha256':digest(data),'clientZipBytes':len(client),'clientZipSha256':digest(client),'limits':['20 MiB is the bridge output limit, not a claim about the platform maximum','Original task remains failed; explicit new compression request completes','Single direct synthetic archive; no arbitrary archive safety or group claim']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args();r=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-12/output-limit-ui-ledger.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['passed'] else 1)

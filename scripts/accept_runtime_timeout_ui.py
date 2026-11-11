#!/usr/bin/env python3
"""Read-only audit of real runtime timeout, native failure feedback and next task."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from frozen_install import frozen_install_matches, module_sources_match
from dingtalk_bridge.routing import route_configs


def timeout_checks(before, after, proof, deadline, cleanup, limit, restored):
    chain=proof['ancestry'];dm=next(r for r in before['components'] if r['name']=='agent-2')
    return {
        'owned_guard_cli_tool_ancestry': len(chain)>=5 and chain[0]['pid']==proof['marker']['pid'] and chain[-1]['pid']==dm['pid'] and chain[-1]['identity']==dm['identity'] and all(a['ppid']==b['pid'] for a,b in zip(chain,chain[1:])) and 'runtime_guard.py' in chain[-2]['identity'],
        'actual_150_second_tool': all(x in chain[1]['identity'] for x in ('time.sleep(150)','dab-timeout-started.json','dab-timeout-late.txt')),
        'measured_runtime_timeout': 90 <= cleanup['at']-proof['runtimeLogCreatedAt'] < 110 and cleanup['at'] < proof['marker']['startedAt']+150,
        'automatic_cleanup_no_test_signals': cleanup['allToolProcessesGone'] and cleanup['descendantSignalsFromTest']==0 and all(r['current'] is None for r in cleanup['ancestryAfter'][:-1]),
        'gateway_survived_timeout_and_followup': cleanup['gatewayUnchanged'] and cleanup['ancestryAfter'][-1]['current']==dm['identity'] and before==after,
        'past_original_deadline_without_late_write': deadline['at']>proof['marker']['startedAt']+155 and deadline['lateExists'] is False and deadline['started']==proof['marker'],
        'config_limit_restored_exactly': limit['originalSeconds']==600 and limit['testSeconds']==90 and limit['changedOnlyTimeoutSeconds'] and restored['sha256']==limit['beforeSha256'] and restored['seconds']==600,
    }


def audit():
    f = ROOT / 'local/runtime-timeout-ui-20261112'
    before, final, cases, intent, obs = (read(f / n) for n in ('before.json', 'final.json', 'cases.json', 'intent.json', 'ui-observations.json'))
    proof, deadline, cleanup, limit, restored = (read(f / n) for n in ('running-proof.json','deadline.json','automatic-timeout.json','temporary-limit.json','restored-config.json'))
    checks=timeout_checks(read(f/'manager-before-task.json'),read(f/'manager-after-followup.json'),proof,deadline,cleanup,limit,restored)
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key; transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key'), ('events', transport, 'message_id')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct_cfg, direct_folder = cfg, agent
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_two_new_tasks'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {c['job']['id'] for c in cases.values()}
    checks['exact_four_confirmed_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for c in cases.values() for r in c['outbox']} and sum(len(c['outbox']) for c in cases.values()) == 4
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    for label, case in cases.items():
        job = case['job']; model = json.loads(job['model']); event = case['event']
        checks[label + '_authorized_input'] = job in jobs and events.get(model['id']) == event and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
        checks[label + '_bound_confirmed_replies'] = all(r in outbox and r['state'] == 'confirmed' and set(json.loads(r['payload'])) == {'text'} for r in case['outbox']) and len(case['replyEvents']) == len(case['outbox']) and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
        checks[label + '_no_self_echo'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
        log = ROOT / case['runLog']; checks[label + '_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    failed_job = cases['timeout']['job']; follow = cases['followup']['job']
    checks['running_became_failed_timeout_without_result'] = proof['job']['id']==failed_job['id'] and proof['job']['state']=='running' and failed_job['state']=='failed' and failed_job['error']=='RuntimeStopped' and failed_job['result'] is None and cleanup['job']==failed_job
    notices=[json.loads(r['payload'])['text'] for r in cases['timeout']['outbox'] if '执行超时' in json.loads(r['payload'])['text']]
    checks['one_accurate_timeout_notice'] = len(notices)==1 and all(x in notices[0] for x in ('90秒','未自动重做','未发送结果文件','已产生的文件或外部变更可能仍存在'))
    checks['original_task_not_replayed'] = sum(j['command']==intent['prompt'] for j in jobs)==1 and follow['command']==intent['followup']
    checks['followup_after_cleanup_and_deadline'] = read(f/'followup-send-attempt.json')['at']>max(cleanup['at'],deadline['at'])
    result = json.loads(follow['result']); text = result['response']['text']
    entries = [json.loads(x) for x in (ROOT / cases['followup']['runLog']).read_text().splitlines()]
    calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
    outputs = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
    checks['followup_real_read_tools'] = any(fn['name'] == 'Bash' and all(x in fn['arguments'] for x in ('read_text', 'dab-timeout-started.json', 'dab-timeout-late.txt')) and cid in outputs and json.loads(outputs[cid]) == {'started_exists': True, 'late_exists': False, 'marker': intent['marker'], 'calculation': 703} for cid, fn in calls.items())
    checks['followup_completed_no_files'] = follow['state'] == 'completed' and not result['response']['files'] and not result['artifacts']
    checks['native_timeout_feedback'] = len(notices) == 1 and notices[0] in (f / 'timeout-reply.ax.txt').read_text()
    checks['native_full_followup'] = '[Agent] ' + text in (f / 'followup-reply.ax.txt').read_text() and '不存在' in text and intent['marker'] in text and '703' in text
    checks['exact_two_ui_send_attempts'] = all(read(f / name)['attempts'] == 1 for name in ('send-attempt.json', 'followup-send-attempt.json'))
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 3 and all(v['reviewed'] and digest((f / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    workspace = Path(intent['workspace'])
    checks['started_preserved_no_late_after_followup'] = read(workspace/'exports/dab-timeout-started.json')==proof['marker'] and not (workspace/'exports/dab-timeout-late.txt').exists()
    original_log=ROOT/cases['timeout']['runLog']; guard_log=original_log.with_name('stderr.log')
    checks['guard_observed_parent_pipe_and_cleanup'] = any(e.get('runtime_guard')=='gateway_pipe_closed' and e.get('cleanup_complete') is True for e in (json.loads(line) for line in guard_log.read_text().splitlines() if line.startswith('{')))
    install = read(ROOT / 'evidence/2026-11-12/runtime-timeout-install.json')
    checks['frozen_tested_install_matches'] = frozen_install_matches(install, f)
    return {'currentWorkspaceCodeMatchesTestedWheel': module_sources_match(install, ROOT / 'dingtalk_bridge'), 'date': '2026-11-12', 'ok': all(checks.values()), 'checks': checks, 'counts': {k: {t: len(v[t]) for t in ('jobs','outbox','deliveries','events')} for k,v in final['routes'].items()},
            'scope': 'Real native DM 90-second runtime timeout during 150-second Python wait; no operator process signals, gateway/session survive, no late write past deadline, actual read-only next task and native replies. Config restored byte-exactly to 600 seconds; not side-effect rollback.'}



if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: (ROOT / args.output).write_text(data)
    print(data); raise SystemExit(0 if report['ok'] else 1)

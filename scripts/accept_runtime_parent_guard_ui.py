#!/usr/bin/env python3
"""Read-only audit of controlled gateway crash, uncertainty notice and real follow-up."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from frozen_install import frozen_install_matches, module_sources_match
from dingtalk_bridge.routing import route_configs


def recovery_checks(before, crashed, restarted, proof, deadline, cleanup):
    old={r['name']:r for r in before['components']};new={r['name']:r for r in restarted['state']['components']};chain=proof['ancestry']
    return {
        'only_dm_replaced_by_crash': all(old[n]==new[n] for n in ('transport','agent-1')) and old['agent-2']['pid']!=new['agent-2']['pid'],
        'owned_guard_cli_tool_ancestry': len(chain)>=5 and chain[0]['pid']==proof['marker']['pid'] and chain[-1]['pid']==old['agent-2']['pid'] and chain[-1]['identity']==old['agent-2']['identity'] and all(a['ppid']==b['pid'] for a,b in zip(chain,chain[1:])) and 'runtime_guard.py' in chain[-2]['identity'],
        'actual_75_second_tool': all(x in chain[1]['identity'] for x in ('time.sleep(75)','dab-guard-started.json','dab-guard-late.txt')),
        'gateway_crashed_early': crashed['ancestryAfter'][-1]['current'] is None and proof['marker']['startedAt']<crashed['at']<proof['marker']['startedAt']+75,
        'automatic_cleanup_no_test_signals': cleanup['allOriginalProcessesGone'] and cleanup['descendantSignalsFromTest']==0 and all(r['current'] is None for r in cleanup['ancestryAfter']) and cleanup['at']<proof['marker']['startedAt']+75,
        'cleanup_before_restart': cleanup['at']<restarted['at'] and restarted['status']['all_running'],
        'past_original_deadline_without_late_write': deadline['at']>proof['marker']['startedAt']+80 and deadline['lateExists'] is False and deadline['started']==proof['marker'],
    }


def audit():
    f = ROOT / 'local/runtime-parent-guard-20261112'
    before, final, cases, intent, obs = (read(f / n) for n in ('before.json', 'final.json', 'cases.json', 'intent.json', 'ui-observations.json'))
    proof, crashed, restarted, late, cleanup = (read(f / n) for n in ('running-proof.json', 'crashed.json', 'restarted.json', 'deadline.json', 'automatic-cleanup.json'))
    checks = recovery_checks(read(f / 'manager-before-crash.json'), crashed, restarted, proof, late, cleanup)
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
    crashed_job = cases['interrupted']['job']; follow = cases['followup']['job']
    checks['running_became_interrupted_without_result'] = proof['job']['id'] == crashed_job['id'] and proof['job']['state'] == 'running' and crashed_job['state'] == 'interrupted' and crashed_job['error'] == 'process_restart' and crashed_job['result'] is None
    notices = [json.loads(r['payload'])['text'] for r in cases['interrupted']['outbox'] if '未自动重做' in json.loads(r['payload'])['text']]
    checks['one_accurate_uncertainty_notice'] = len(notices) == 1 and all(x in notices[0] for x in ('执行结果未确认','工具可能仍在执行或已产生结果')) and '中断而停止' not in notices[0]
    checks['original_task_not_replayed'] = sum(j['command'] == intent['prompt'] for j in jobs) == 1 and follow['command'] == intent['followup']
    checks['followup_after_cleanup_and_restart'] = read(f / 'followup-send-attempt.json')['at'] > max(restarted['at'], late['at'])
    result = json.loads(follow['result']); text = result['response']['text']
    entries = [json.loads(x) for x in (ROOT / cases['followup']['runLog']).read_text().splitlines()]
    calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
    outputs = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
    checks['followup_real_read_tools'] = any(fn['name'] == 'Bash' and all(x in fn['arguments'] for x in ('read_text', 'dab-guard-started.json', 'dab-guard-late.txt')) and cid in outputs and json.loads(outputs[cid]) == {'started_exists': True, 'late_exists': False, 'marker': intent['marker']} for cid, fn in calls.items())
    checks['followup_completed_no_files'] = follow['state'] == 'completed' and not result['response']['files'] and not result['artifacts']
    checks['native_uncertainty_feedback'] = len(notices) == 1 and notices[0] in (f / 'recovery-reply.ax.txt').read_text()
    checks['native_full_followup'] = '[Agent] ' + text in (f / 'followup-reply.ax.txt').read_text() and '不存在' in text and intent['marker'] in text
    checks['exact_two_ui_send_attempts'] = all(read(f / name)['attempts'] == 1 for name in ('send-attempt.json', 'followup-send-attempt.json'))
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 3 and all(v['reviewed'] and digest((f / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    workspace = Path(intent['workspace'])
    checks['started_preserved_no_late_after_followup'] = read(workspace/'exports/dab-guard-started.json')==proof['marker'] and not (workspace/'exports/dab-guard-late.txt').exists()
    original_log=ROOT/cases['interrupted']['runLog']; guard_log=original_log.with_name('stderr.log')
    checks['guard_observed_parent_pipe_and_cleanup'] = any(e.get('runtime_guard')=='gateway_pipe_closed' and e.get('cleanup_complete') is True for e in (json.loads(line) for line in guard_log.read_text().splitlines() if line.startswith('{')))
    install = read(ROOT / 'evidence/2026-11-12/runtime-parent-guard-install.json')
    checks['frozen_tested_install_matches'] = frozen_install_matches(install, f)
    return {'currentWorkspaceCodeMatchesTestedWheel': module_sources_match(install, ROOT / 'dingtalk_bridge'), 'date': '2026-11-12', 'ok': all(checks.values()), 'checks': checks, 'counts': {k: {t: len(v[t]) for t in ('jobs','outbox','deliveries','events')} for k,v in final['routes'].items()},
            'automatic_descendant_cleanup_after_gateway_sigkill': True,
            'scope': 'One real native DM gateway SIGKILL; independent guard cleans owned CLI/tools with zero test-side descendant signals, no late write beyond deadline; interrupted/no replay, native notice and read-only follow-up. Not OS sandbox or guard SIGKILL coverage.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: (ROOT / args.output).write_text(data)
    print(data); raise SystemExit(0 if report['ok'] else 1)

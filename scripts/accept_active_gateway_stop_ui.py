#!/usr/bin/env python3
"""Read-only audit of the native DM task stopped during a real Python tool."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def recovery_checks(before, stopped, restarted, proof, deadline):
    old = {r['name']: r for r in before['components']}
    new = {r['name']: r for r in restarted['state']['components']}
    chain = proof['ancestry']; shell = chain[1]['identity']
    return {
        'only_direct_gateway_replaced': all(old[n] == new[n] for n in ('transport', 'agent-1')) and old['agent-2']['pid'] != new['agent-2']['pid'],
        'owned_tool_ancestry': len(chain) >= 3 and chain[0]['pid'] == proof['marker']['pid'] and chain[-1]['pid'] == old['agent-2']['pid'] and chain[-1]['identity'] == old['agent-2']['identity'] and all(a['ppid'] == b['pid'] for a, b in zip(chain, chain[1:])),
        'actual_sleep_and_late_write_command': all(s in shell for s in ('python3 -', 'time.sleep(90)', 'exports/dab-stop-started.json', 'exports/dab-stop-late.txt', 'os.getpid()')),
        'all_original_processes_gone': [r['pid'] for r in stopped['ancestryAfter']] == [r['pid'] for r in chain] and all(r['current'] is None for r in stopped['ancestryAfter']),
        'stopped_before_original_deadline': proof['marker']['startedAt'] < stopped['at'] < proof['marker']['startedAt'] + 90,
        'restarted_healthy': restarted['status']['all_running'],
        'checked_after_wait_deadline': deadline['at'] > proof['marker']['startedAt'] + 95,
        'start_file_unchanged_late_file_absent': deadline['started'] == proof['marker'] and deadline['lateExists'] is False,
    }


def audit():
    f = ROOT / 'local/active-stop-ui-20261112'
    before, final, cases, intent, obs = (read(f / n) for n in ('before.json', 'final.json', 'cases.json', 'intent.json', 'ui-observations.json'))
    proof, stopped, restarted, deadline = (read(f / n) for n in ('running-proof.json', 'manager-stopped.json', 'manager-restarted.json', 'deadline.json'))
    checks = recovery_checks(read(f / 'manager-before.json'), stopped, restarted, proof, deadline)
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
    cancelled = cases['cancelled']['job']; follow = cases['followup']['job']
    checks['running_became_cancelled_without_result'] = proof['job']['id'] == cancelled['id'] and proof['job']['state'] == 'running' and cancelled['state'] == 'cancelled' and cancelled['error'] == 'RuntimeStopped' and cancelled['result'] is None
    checks['one_cancellation_feedback'] = sum(json.loads(r['payload']).get('text') == '[Agent] 任务已停止。' for r in cases['cancelled']['outbox']) == 1
    checks['original_task_not_replayed'] = sum(j['command'] == intent['prompt'] for j in jobs) == 1 and follow['command'] == intent['followup']
    checks['followup_after_deadline'] = read(f / 'followup-send-attempt.json')['at'] > deadline['at']
    result = json.loads(follow['result']); text = result['response']['text']
    entries = [json.loads(x) for x in (ROOT / cases['followup']['runLog']).read_text().splitlines()]
    calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
    outputs = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
    checks['followup_real_read_and_calculate'] = any(fn['name'] == 'Bash' and all(x in fn['arguments'] for x in ('exists()', 'read_text', '37', '19', 'dab-stop-started.json', 'dab-stop-late.txt')) and cid in outputs and json.loads(outputs[cid]) == {'started_exists': True, 'late_exists': False, 'marker': intent['marker'], 'result': 703} for cid, fn in calls.items())
    checks['followup_completed_no_files'] = follow['state'] == 'completed' and not result['response']['files'] and not result['artifacts']
    checks['native_cancel_feedback'] = '[Agent] 任务已停止。' in (f / 'task-sent.ax.txt').read_text()
    checks['native_full_followup'] = '[Agent] ' + text in (f / 'followup-reply.ax.txt').read_text() and all(x in text for x in (intent['marker'], '703', 'dab-stop-started.json', 'dab-stop-late.txt'))
    checks['exact_two_ui_send_attempts'] = all(read(f / name)['attempts'] == 1 for name in ('task-send-attempt.json', 'followup-send-attempt.json'))
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 2 and all(v['reviewed'] and digest((f / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    workspace = Path(intent['workspace'])
    checks['still_no_late_write'] = not (workspace / 'exports/dab-stop-late.txt').exists() and read(workspace / 'exports/dab-stop-started.json') == proof['marker']
    return {'date': '2026-11-12', 'checks': checks, 'ok': all(checks.values()), 'counts': {k: {t: len(v[t]) for t in ('jobs', 'outbox', 'deliveries', 'events')} for k, v in final['routes'].items()}, 'scope': 'Native DM task, actual Python/shell ancestry, managed gateway SIGTERM, one cancellation, restart and real read-only follow-up. Not SIGKILL, OS sandbox, group controls or unrelated process control.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: (ROOT / args.output).write_text(data)
    print(data); raise SystemExit(0 if report['ok'] else 1)

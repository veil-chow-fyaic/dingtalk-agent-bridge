#!/usr/bin/env python3
"""Read-only audit of real UI status/cancel/new cases, including a fixed failure."""
import argparse
from contextlib import closing
import json
import sqlite3

from accept_office_files import ROOT, read, digest
from dingtalk_bridge.routing import route_configs


def rows(path, table):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute('SELECT * FROM '+table)]


def audit():
    folder = ROOT / 'local/task-controls-20261111'
    before, final, cases = (read(folder/name) for name in ('before-ledgers.json', 'final-ledgers.json', 'cases.json'))
    expected = {'status-before-fix': 1, 'status-after-fix': 1, 'status-running': 1,
                'cancel-task': 2, 'next-task': 2, 'cancel': 1, 'seed': 2, 'new': 2, 'new-check': 2}
    if set(cases) != set(expected):
        return {'ok': False, 'error': 'incomplete_case_coverage'}
    checks = {}
    for cfg, state in route_configs(read(ROOT/'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT/'local/agents'/key
        transport = ROOT/'local/runtime/routes'/state/'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, path, identity in [('jobs', agent/'tasks.sqlite3', 'id'),
                                      ('outbox', agent/'tasks.sqlite3', 'key'),
                                      ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(path, table)}
            checks[kind+'_'+table+'_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        if kind == 'group':
            checks['group_unchanged_during_experiment'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'runFiles'))
        else:
            direct_folder = agent
            direct_cfg = cfg
            jobs = rows(agent/'tasks.sqlite3', 'jobs')
            outbox = rows(agent/'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    allowed = read(ROOT/'local/agent-direct-config.json')['allowedSenderIds']
    job_by_id, reply_by_key = {j['id']: j for j in jobs}, {r['key']: r for r in outbox}
    real_runtime = {'cancel-task', 'next-task', 'seed', 'new-check'}
    reports = []
    for name, case in cases.items():
        job, event, replies = case['job'], case['event'], case['outbox']
        actual = case['replyEvents']
        check = {
            'immutable_job': job_by_id.get(job['id']) == job,
            'input_committed': events.get(event['message_id']) == event,
            'authorized_nonself_input': event['from_self'] is False and event['sender_id'] in allowed,
            'expected_final_state': job['state'] == ('cancelled' if name == 'cancel-task' else 'completed'),
            'exact_confirmed_replies': len(replies) == expected[name] and all(
                r['state'] == 'confirmed' and reply_by_key.get(r['key']) == r for r in replies),
            'bound_reply_identity': len(actual) == len(replies) and all(
                events.get(e['message_id']) == e and e['from_self'] is True and
                e['sender_id'] == direct_cfg['selfSenderId'] for e in actual),
            'no_reply_echo_task': all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in actual),
        }
        log = case.get('runLog')
        check['runtime_only_for_real_tasks'] = bool(log) is (name in real_runtime)
        if log:
            path = ROOT/log
            check['runtime_log_preserved'] = path.is_file() and digest(path.read_bytes()) == case['runLogSha256']
        reports.append({'case': name, 'checks': check})

    def text(name):
        return '\n'.join(e['content'] for e in cases[name]['replyEvents'])

    old_query = read(folder/'status-before-fix.json')
    old_summary = json.loads(text('status-before-fix').split('任务状态：', 1)[1])
    checks['pre_fix_phantom_queue_reproduced'] = old_summary['jobs'].get('queued') == 1 and not any(
        j['state'] == 'queued' for j in old_query['jobsAfter'])
    checks['idle_status_fixed'] = '执行中 0，排队 0，等待附件 0' in text('status-after-fix')
    checks['real_running_and_queued_counts'] = '执行中 1，排队 1，等待附件 0' in text('status-running')
    status_events = [cases[n]['event'] for n in ('status-before-fix', 'status-after-fix', 'status-running')]
    checks['same_body_distinct_messages_processed_once'] = (len({e['message_id'] for e in status_events}) == 3 and
        {e['content'] for e in status_events} == {'/agent status'})
    checks['cancel_request_and_stopped_result'] = '已请求停止当前任务' in text('cancel') and '任务已停止' in text('cancel-task')
    checks['queued_task_followed_cancel'] = (cases['cancel-task']['job']['seq'] < cases['next-task']['job']['seq'] < cases['cancel']['job']['seq']
        and '队列继续437' in text('next-task'))
    running = read(folder/'cancel-task-running.json')
    stopped = read(folder/'cancel-processes-stopped.json')
    deadline = read(folder/'cancel-after-deadline.json')
    log_events = [json.loads(line) for line in (ROOT/cases['cancel-task']['runLog']).read_text().splitlines()]
    checks['actual_sleep_tool_called'] = running['job']['state'] == 'running' and bool(running['children']) and any(
        t.get('function', {}).get('name') == 'Bash' and 'time.sleep(120)' in t.get('function', {}).get('arguments', '')
        for e in log_events for t in e.get('tool_calls', []))
    checks['owned_processes_ended'] = stopped['allObservedChildrenGone'] is True and bool(stopped['perChildGone']) and all(stopped['perChildGone'])
    checks['cancelled_output_absent_after_deadline'] = (deadline['at'] - running['at'] > 120 and deadline['outputAbsent'] is True
        and not any(direct_folder.rglob('dab-cancel-should-not-exist.txt')))
    checks['cancelled_job_has_no_artifacts'] = not json.loads(cases['cancel-task']['job']['result'] or '{}').get('artifacts')
    checks['seed_visible_then_new_context_answer'] = '已记住琥珀719' in text('seed') and '新会话无旧口令' in text('new-check') and '琥珀719' not in text('new-check')
    checks['new_acknowledged_in_chat'] = '已开始新会话' in text('new')
    old_meta, empty_meta, new_meta = ({m['key']: m['value'] for m in read(folder/name)['meta']} for name in
                                     ('before-new-session.json', 'after-new-before-runtime.json', 'after-new-runtime.json'))
    checks['generation_advanced_once'] = int(empty_meta['generation']) == int(old_meta['generation']) + 1 == int(new_meta['generation'])
    checks['native_binding_cleared_then_replaced'] = 'session_id' not in empty_meta and new_meta['session_id'] != old_meta['session_id']
    checks['new_workspace_separate'] = (direct_folder/'workspaces'/old_meta['generation']).is_dir() and (direct_folder/'workspaces'/new_meta['generation']).is_dir()
    old = before['routes']['direct']; end = final['routes']['direct']
    checks['exact_nine_new_requests'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {c['job']['id'] for c in cases.values()}
    checks['exact_four_new_runtime_runs'] = set(end['runFiles']) - set(old['runFiles']) == {cases[n]['runLog'] for n in real_runtime}
    return {'date': '2026-11-11', 'checks': checks, 'cases': reports,
            'requests': 9, 'confirmedReplies': 14, 'realRuntimeCalls': 4,
            'knownPreFixFailure': 'Status counted its own request as queued; original request/response retained',
            'uiEvidence': 'Native veil input, liev status/stop/next/new-context replies captured privately',
            'limits': ['Direct-chat controls only; group controls not newly sent',
                       'New-session isolation is not an OS security sandbox',
                       'Cancellation does not undo actions already completed by a task'],
            'ok': all(checks.values()) and all(all(c['checks'].values()) for c in reports)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT/'evidence/2026-11-11/task-controls-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

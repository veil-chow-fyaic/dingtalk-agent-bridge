#!/usr/bin/env python3
"""Read-only audit of a real child HTTP outage, UI task and history recovery."""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/network-recovery-20261112'
    before, fault, recovered, final = (read(folder / (n + '.json')) for n in
                                     ('ready', 'during-fault', 'after-recovery', 'final'))
    case, intent = read(folder / 'case.json'), read(folder / 'intent.json')
    start, restored = read(folder / 'offline-start.json'), read(folder / 'restored-network.json')
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'),
                                    ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_old_rows_preserved'] = bool(old[table]) and all(
                current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_runtime_logs_preserved'] = bool(old['runtimeFiles']) and all(
            (ROOT / n).is_file() and digest((ROOT / n).read_bytes()) == sha
            for n, sha in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged_through_experiment'] = all(
                old[t] == snapshot['routes'][kind][t]
                for snapshot in (fault, recovered, final)
                for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events', 'runtimeFiles'))
            checks['group_history_sync_continued_during_outage'] = old['transportMeta'] != fault['routes'][kind]['transportMeta']
        else:
            direct = cfg
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
            checks['direct_no_ledger_or_watermark_progress_during_outage'] = old == fault['routes'][kind]
            checks['exact_one_new_job'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {case['job']['id']}
            expected = {r['key'] for r in case['outbox']}
            checks['exact_three_new_outbox_and_transport_replies'] = len(expected) == 3 and all(
                {r['key'] for r in end[t]} - {r['key'] for r in old[t]} == expected for t in ('outbox', 'deliveries'))
            checks['session_binding_unchanged'] = old['meta'] == end['meta']
            checks['no_further_jobs_or_replies_after_recovery_and_cleanup'] = all(
                recovered['routes'][kind][t] == end[t] for t in ('jobs', 'outbox', 'deliveries', 'runtimeFiles'))
    def health(snapshot, kind):
        return next(r for r in snapshot['health']['routes'] if r['conversation_type'] == kind)
    checks['direct_failed_group_healthy'] = health(fault, 'direct')['poll_error'] == 'BridgeError' and not health(fault, 'group')['poll_error']
    checks['healthy_before_and_after'] = all(not snapshot['health']['poll_error'] for snapshot in (before, recovered, final))
    checks['fault_window_and_manual_recovery'] = before['at'] < start['startedAt'] < fault['at'] < restored['at'] < start['expiresAt'] and restored['manualRemovalBeforeExpiry'] is True
    preflight = read(folder / 'proxy-readonly-preflight.json')
    error = json.loads(preflight['stderr'])['error']
    checks['official_cli_real_proxy_io_failure'] = preflight['exitCode'] == 1 and error['reason'] == 'io_timeout' and 'proxyconnect tcp' in error['cause']
    trace = read(folder / 'official-fault-trace.json')
    failed = {r['execution_id'] for r in trace if r.get('msg') == 'command_end' and r.get('success') is False and r.get('error_reason') == 'io_timeout'}
    checks['live_official_history_commands_failed'] = len(failed) >= 1 and all(any(
        r.get('msg') == 'command_start' and r.get('execution_id') == execution and r.get('product') == 'chat' and r.get('tool') == 'list_individual_chat_message'
        for r in trace) for execution in failed)
    calls = [json.loads(line) for line in (folder / 'wrapper-calls.ndjson').read_text().splitlines()]
    checks['blocked_official_history_children_during_window'] = any(
        start['startedAt'] <= r['at'] < restored['at'] and r['blocked'] and r['socketBound'] and r['operation'] == ['chat', '+chat-messages'] for r in calls)
    checks['same_processes_across_network_recovery'] = {
        r['component']: r['pid'] for r in read(folder / 'setup-start.json')['components']
    } == {r['name']: r['pid'] for r in read(folder / 'manager-before-cleanup.json')['components']} and all(
        r['startedAt'] < start['startedAt'] for r in read(folder / 'manager-before-cleanup.json')['components'])
    server, event = read(folder / 'server-message.json'), case['event']
    server_read = read(folder / 'independent-server-during-fault.json')
    checks['independent_server_read_during_fault_contains_exact_message'] = server_read['exitCode'] == 0 and start['startedAt'] < server_read['at'] < restored['at'] and json.loads(server_read['stdout'])['messages'].count(server) == 1
    checks['server_received_task_while_bridge_had_not'] = server['messageId'] == event['message_id'] and server['text'] == intent['task'] and not any(r['message_id'] == server['messageId'] for r in fault['routes']['direct']['events']) and all(read(folder / 'during-fault-checks.json').values())
    checks['one_authorized_native_input_recovered'] = event == events.get(event['message_id']) and event['content'] == intent['task'] and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds'] and sum(json.loads(j['model'])['id'] == event['message_id'] for j in jobs) == 1
    checks['completed_job_preserved'] = case['job']['state'] == 'completed' and case['job'] in jobs
    checks['three_confirmed_replies_preserved'] = len(case['outbox']) == 3 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['three_bound_liev_reply_events'] = len(case['replyEvents']) == 3 and all(e == events.get(e['message_id']) and e['from_self'] is True and e['sender_id'] == direct['selfSenderId'] for e in case['replyEvents'])
    checks['reply_events_do_not_create_jobs'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    checks['runtime_logs_unchanged'] = len(case['runFiles']) == 3 and all(digest((ROOT / p).read_bytes()) == sha for p, sha in case['runFiles'].items())
    logs = [ROOT / p for p in case['runFiles'] if p.endswith('/events.jsonl')]
    records = [json.loads(line) for p in logs for line in p.read_text().splitlines()]
    tools = [t['function'] for r in records for t in r.get('tool_calls', [])]
    checks['real_python_computation_without_office_calls'] = len(logs) == 1 and len(tools) == 1 and tools[0]['name'] == 'Bash' and 'result = 37 * 43' in tools[0]['arguments'] and any(r.get('role') == 'tool' and r.get('content') == '1591\n' for r in records)
    artifacts = json.loads(case['job']['result'])['artifacts']
    checks['one_result_artifact'] = len(artifacts) == 1
    if len(artifacts) != 1:
        return {'ok': False, 'checks': checks}
    artifact = artifacts[0]
    data = (folder / Path(artifact['file']).name).read_bytes()
    checks['client_download_exact_expected_and_generated_bytes'] = data == b'DAB-NETWORK-20261112\n37 * 43 = 1591\n' and data == (ROOT / artifact['file']).read_bytes() and digest(data) == artifact['sha256']
    checks['native_sent_input_and_visible_ack'] = intent['task'] in (folder / '02-sent.ax.txt').read_text() and '已接收任务' in (folder / '03-after-network-restore.ax.txt').read_text()
    checks['native_file_card_visible'] = '0-dab-network-001.txt' in (folder / '04-result.ax.txt').read_text()
    opened = (folder / '06-client-open.full.ax.txt').read_text()
    checks['download_opened_in_native_quicklook'] = '窗口 快速查看' in opened and '0-dab-network-001.txt' in opened and data.decode() in opened
    observation = read(folder / 'observations.json')
    checks['four_reviewed_ui_frames_unchanged'] = set(observation['frames']) == {'02-sent.png', '03-after-network-restore.png', '04-result.png', '06-client-open.png'} and all(r['observed'] and digest((folder / f).read_bytes()) == r['sha256'] for f, r in observation['frames'].items())
    cleanup = read(folder / 'cleanup.json')
    test_config = read(folder / 'service-config-before.json')
    for route in test_config['routes']:
        if route['conversationType'] == 'direct':
            route['binary'] = 'local/network-recovery-20261112/dws-network-gate'
    recorded_transport = next(r for r in read(folder / 'manager-before-cleanup.json')['components'] if r['name'] == 'transport')
    checks['only_direct_binary_changed_and_original_restored'] = recorded_transport['configSha256'] == digest((json.dumps(test_config, ensure_ascii=False, indent=2) + '\n').encode()) and cleanup['configExactRestored'] and cleanup['contextOfficialBinaryRestored'] and digest((ROOT / 'local/service-config.json').read_bytes()) == intent['configBeforeSha256'] and digest((ROOT / direct['binary']).read_bytes()) == intent['officialBinarySha256']
    checks['fault_removed_and_wrapper_unchanged'] = cleanup['noActiveFault'] and not (folder / 'offline.json').exists() and digest((folder / 'dws-network-gate').read_bytes()) == intent['wrapperSha256']
    checks['cleanup_manager_and_doctor_healthy'] = cleanup['manager']['all_running'] and read(folder / 'doctor-after-cleanup.json')['ok']
    checks['observer_identity_and_start_preserved'] = before['observer']['pid'] == final['observer']['pid'] and before['observer']['startedAt'] == final['observer']['startedAt'] and final['observer']['samples'] > before['observer']['samples']
    checks['post_recovery_observation_over_one_minute'] = final['at'] - recovered['at'] > 60
    return {'date': '2026-11-12', 'checks': checks, 'runtimeTasks': 1, 'confirmedReplies': 3,
            'faultDurationSeconds': round(restored['at'] - start['startedAt'], 3),
            'officialIoTimeoutsInWindow': len(failed), 'downloadBytes': len(data),
            'limits': ['Only direct-route child HTTP history calls were isolated; not a full host or existing Stream socket outage',
                       'No expired or revoked credential tested', 'Short reply text was not separately observed in the chat viewport',
                       'Setup/cleanup required recorded maintenance; recovery itself required no process restart or resend',
                       'Original reliability observer is under 24h; maintenance unavailable samples retained'],
            'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/history-network-recovery-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

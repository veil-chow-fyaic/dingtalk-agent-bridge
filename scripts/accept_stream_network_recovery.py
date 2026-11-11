#!/usr/bin/env python3
"""Read-only audit: real Stream tunnel loss, history fallback, recovery and UI."""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/stream-network-20261112'
    before, ready, fault, recovered, final = (read(folder / (n + '.json')) for n in
        ('before', 'ready', 'fault-progress', 'before-cleanup', 'final'))
    cases, intent = read(folder / 'cases.json'), read(folder / 'intent.json')
    if set(cases) != {'A', 'B'}:
        return {'ok': False, 'error': 'incomplete_cases'}
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_old_rows_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_runtime_logs_preserved'] = bool(old['runtimeFiles']) and all((ROOT / f).is_file() and digest((ROOT / f).read_bytes()) == sha for f, sha in old['runtimeFiles'].items())
        checks[kind + '_setup_no_new_work'] = all(old[t] == ready['routes'][kind][t] for t in ('jobs', 'outbox', 'deliveries', 'events', 'runtimeFiles'))
        if kind == 'group':
            checks['group_no_new_messages_or_jobs'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'deliveries', 'events', 'runtimeFiles'))
        else:
            direct, workspace = cfg, agent / 'workspaces/1'
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
            checks['exact_two_new_jobs_no_invented_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {c['job']['id'] for c in cases.values()}
            expected = {r['key'] for c in cases.values() for r in c['outbox']}
            checks['exact_five_new_outbox_and_transport_replies'] = len(expected) == 5 and all({r['key'] for r in end[t]} - {r['key'] for r in old[t]} == expected for t in ('outbox', 'deliveries'))
            checks['session_binding_unchanged'] = old['meta'] == end['meta']
            checks['no_replay_after_cleanup'] = all(recovered['routes'][kind][t] == end[t] for t in ('jobs', 'outbox', 'deliveries', 'runtimeFiles'))
    start, restored = read(folder / 'offline-start.json'), read(folder / 'network-restored.json')
    trace = [json.loads(line) for line in (folder / 'proxy.ndjson').read_text().splitlines()]
    opened = {r['connection']: r for r in trace if r['event'] == 'opened'}
    cut = [r for r in trace if r['event'] == 'closed_on_fault' and opened.get(r['connection'], {}).get('host') == 'wss-open-connection.dingtalk.com']
    checks['established_websocket_tunnel_actually_cut'] = len(cut) == 1 and opened[cut[0]['connection']]['at'] < start['startedAt'] <= cut[0]['at'] < fault['at']
    checks['no_new_tunnels_while_fault_active'] = not any(start['startedAt'] <= r['at'] < restored['at'] for r in opened.values()) and any(r['event'] == 'denied_offline' and start['startedAt'] <= r['at'] < restored['at'] for r in trace)
    checks['manual_bounded_fault_recovery'] = start['startedAt'] < fault['at'] < restored['at'] < start['expiresAt'] and restored['manualBeforeExpiry']
    checks['new_websocket_tunnel_after_recovery'] = any(r['host'] == 'wss-open-connection.dingtalk.com' and restored['at'] < r['at'] < recovered['at'] for r in opened.values())
    statuses = {n: read(folder / ('status-' + n + '.json')) for n in ('ready', 'during-fault', 'restored', 'before-cleanup')}
    states = {n: d['bus']['live']['source_state'] for n, d in statuses.items()}
    checks['official_reconnecting_and_reconnect_counter'] = states['during-fault']['state'] == 'reconnecting' and states['during-fault']['reconnect_count'] > states['ready']['reconnect_count']
    checks['same_bus_and_consumers_across_fault'] = len({d['bus']['entry']['holder_pid'] for d in statuses.values()}) == 1 and all({c['pid'] for c in d['bus']['live']['consumers']} == {c['pid'] for c in statuses['ready']['bus']['live']['consumers']} and len(d['bus']['live']['consumers']) == 2 for d in statuses.values())
    checks['source_reconnected_before_cleanup'] = states['restored']['state'] == 'connected' and states['before-cleanup'].get('last_event_at_ms', 0) > restored['at'] * 1000
    checks['same_bridge_processes_across_fault'] = {r['component']: r['pid'] for r in read(folder / 'setup-start.json')['components']} == {r['name']: r['pid'] for r in read(folder / 'manager-before-cleanup.json')['components']}
    def direct_hints(snapshot):
        return next(r['accepted_hints'] for r in snapshot['health']['stream_listeners'] if r['conversation_id'] == direct['group'])
    checks['no_stream_hints_while_history_task_executed'] = direct_hints(ready) == direct_hints(fault) == 0 and cases['A']['job'] in fault['routes']['direct']['jobs']
    checks['seven_hints_received_after_recovery'] = direct_hints(recovered) == 7
    checks['history_healthy_during_and_after_fault'] = all(not s['health']['poll_error'] for s in (ready, fault, recovered, final))
    for label, case in cases.items():
        prefix = label + '_'
        job, event = case['job'], case['event']
        task = read(folder / ('task-' + label + '.json'))
        checks[prefix + 'exact_authorized_ui_input_once'] = event == events.get(event['message_id']) and event['content'] == task['input'] and not event['from_self'] and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds'] and sum(json.loads(j['model'])['id'] == event['message_id'] for j in jobs) == 1
        checks[prefix + 'job_and_replies_preserved'] = job in jobs and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
        checks[prefix + 'liev_replies_without_echo_jobs'] = len(case['replyEvents']) == (2 if label == 'A' else 3) and all(e == events.get(e['message_id']) and e['from_self'] and e['sender_id'] == direct['selfSenderId'] and not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
        checks[prefix + 'runtime_logs_preserved'] = bool(case['runFiles']) and all(digest((ROOT / f).read_bytes()) == sha for f, sha in case['runFiles'].items())
        records = [json.loads(line) for f in case['runFiles'] if f.endswith('events.jsonl') for line in (ROOT / f).read_text().splitlines()]
        tools = [t['function'] for r in records for t in r.get('tool_calls', [])]
        formula = '41 * 47' if label == 'A' else '53 * 59'
        checks[prefix + 'one_actual_python_tool'] = len(tools) == 1 and tools[0]['name'] == 'Bash' and formula in tools[0]['arguments']
        checks[prefix + 'native_input_observed'] = task['input'] in (folder / (label + '-sent.ax.txt')).read_text()
        if label == 'A':
            final_text = [r['content'] for r in records if r.get('role') == 'assistant' and isinstance(r.get('content'), str)][-1]
            try:
                json.loads(final_text); invalid = False
            except ValueError:
                invalid = True
            checks['A_invalid_response_kept_failed_not_delivered'] = invalid and job['state'] == 'failed' and job['error'] == 'JSONDecodeError' and len(case['outbox']) == 2 and not any(Path(f).name == 'validated-response.json' for f in case['runFiles'])
            checks['A_partial_artifact_preserved_not_staged'] = (workspace / 'exports/dab-stream-a-001.txt').read_text() == task['expected'] and not (ROOT / 'local/outbox/agent' / job['id']).exists()
            checks['A_visible_failure_feedback'] = '本次任务未完成，已保留记录' in (folder / 'A-failed.ax.txt').read_text()
        else:
            artifacts = json.loads(job['result'])['artifacts']
            checks['B_completed_one_file'] = job['state'] == 'completed' and len(artifacts) == 1
            if len(artifacts) != 1:
                return {'ok': False, 'checks': checks}
            data = (folder / Path(artifacts[0]['file']).name).read_bytes()
            checks['B_download_matches_expected_generated_and_digest'] = data == task['expected'].encode() and data == (ROOT / artifacts[0]['file']).read_bytes() and digest(data) == artifacts[0]['sha256']
            ax = (folder / 'B-opened.ax.txt').read_text()
            checks['B_native_card_download_and_open'] = '0-dab-stream-b-001.txt' in (folder / 'B-result.ax.txt').read_text() and '下载完成' in (folder / 'B-saved.ax.txt').read_text() and '窗口 快速查看' in ax and data.decode() in ax
    observation = read(folder / 'ui-observations.json')
    checks['five_reviewed_ui_frames_unchanged'] = set(observation['frames']) == {'A-sent.png', 'A-failed.png', 'B-sent.png', 'B-result.png', 'B-opened.png'} and all(r['observed'] and digest((folder / f).read_bytes()) == r['sha256'] for f, r in observation['frames'].items())
    cleanup = read(folder / 'cleanup.json')
    checks['original_configuration_and_context_restored'] = cleanup['configExactRestored'] and cleanup['contextOfficialRestored'] and digest((ROOT / 'local/service-config.json').read_bytes()) == intent['configBeforeSha256']
    checks['temporary_fault_and_proxy_removed'] = cleanup['noActiveFault'] and cleanup['proxiedBusExited'] and observation['proxyExited'] and not (folder / 'offline.json').exists() and trace[-1]['event'] == 'proxy_stopped'
    checks['cleanup_manager_and_doctor_healthy'] = cleanup['manager']['all_running'] and read(folder / 'doctor-final.json')['ok']
    checks['observer_not_reset'] = before['observer']['pid'] == final['observer']['pid'] and before['observer']['startedAt'] == final['observer']['startedAt'] and final['observer']['samples'] > before['observer']['samples']
    checks['proxy_matches_validated_code'] = digest((ROOT / 'scripts/network_fault_proxy.py').read_bytes()) == intent['proxyCodeSha256']
    return {'date': '2026-11-12', 'checks': checks, 'streamFaultSeconds': round(restored['at'] - start['startedAt'], 3),
            'runtimeTasks': 2, 'completedTasks': 1, 'failedTasksRetained': 1, 'confirmedReplies': 5,
            'limits': ['A computed locally but emitted invalid final text; it remains failed and its file was not delivered',
                       'Stream network recovery passed; not a simultaneous whole-host/history outage or expired credential test',
                       'Seven accepted Stream hints counted; individual raw Stream payloads were not captured in this run',
                       'Only B file/card/download/open observed; short result bubble not separately observed',
                       'Setup/cleanup maintenance recorded; original 24h observer not yet complete'],
            'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args(); report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/stream-network-recovery-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

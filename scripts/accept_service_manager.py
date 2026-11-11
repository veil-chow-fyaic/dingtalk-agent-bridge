#!/usr/bin/env python3
"""Read-only audit of lifecycle migration and a native-UI Kimi file task."""
import argparse
import json
from pathlib import Path
import zipfile

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/service-manager-20261111'
    before, final, case, intent = (read(folder / n) for n in
        ('before-ledgers.json', 'final-ledgers.json', 'case.json', 'ui-intent.json'))
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
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(
                current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_runtime_files_unchanged'] = bool(old['runtimeFiles']) and all(
            (ROOT / name).is_file() and digest((ROOT / name).read_bytes()) == item['sha256']
            for name, item in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'runtimeFiles'))
        else:
            direct_cfg = cfg
            jobs, replies = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
            checks['one_new_job_only'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {case['job']['id']}
            checks['three_new_outbox_only'] = {o['key'] for o in end['outbox']} - {o['key'] for o in old['outbox']} == {o['key'] for o in case['outbox']}
            checks['three_new_transport_deliveries_only'] = {d['key'] for d in end['deliveries']} - {d['key'] for d in old['deliveries']} == {o['key'] for o in case['outbox']}
            checks['native_binding_preserved'] = old['meta'] == end['meta']
            added = set(end['runtimeFiles']) - set(old['runtimeFiles'])
            checks['only_new_task_runtime_files'] = bool(added) and added == set(case['runFiles']) and all(case['job']['id'] in p for p in added)
    job, event = case['job'], case['event']
    checks['completed_job_unchanged'] = job['state'] == 'completed' and next((j for j in jobs if j['id'] == job['id']), None) == job
    checks['exact_authorized_ui_input'] = events.get(event['message_id']) == event and event['content'] == intent['input'] and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    checks['one_job_for_input'] = sum(json.loads(j['model'])['id'] == event['message_id'] for j in jobs) == 1
    by_key = {r['key']: r for r in replies}
    checks['three_confirmed_unchanged_replies'] = len(case['outbox']) == 3 and all(r['state'] == 'confirmed' and by_key.get(r['key']) == r for r in case['outbox'])
    checks['three_liev_reply_events'] = len(case['replyEvents']) == 3 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
    checks['no_reply_echo_jobs'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    result = json.loads(job['result'])
    checks['correct_runtime_response'] = result['response']['text'] == '管理器恢复验收：589'
    artifacts = result.get('artifacts', [])
    checks['one_result_artifact'] = len(artifacts) == 1
    if len(artifacts) == 1:
        artifact = artifacts[0]
        client = folder / Path(artifact['file']).name
        data = client.read_bytes() if client.is_file() else b''
        checks['client_download_equals_staged_artifact'] = bool(data) and data == (ROOT / artifact['file']).read_bytes() and digest(data) == artifact['sha256']
        checks['exact_two_line_result'] = data == intent['expectedFile'].encode()
    log_paths = [ROOT / p for p in case['runFiles'] if p.endswith('/events.jsonl')]
    tools = [t['function'] for p in log_paths for line in p.read_text().splitlines()
             for t in json.loads(line).get('tool_calls', [])]
    checks['actual_kimi_write'] = len(log_paths) == 1 and any(t['name'] == 'Write' and
        Path(json.loads(t['arguments']).get('path', '')).name == 'dab-manager-001.txt' for t in tools)
    start, same, stop, restart = (read(folder / (n + '.json')) for n in
        ('managed-start', 'idempotent-start', 'managed-stop', 'managed-restart'))
    checks['three_ready_managed_components'] = start['all_running'] and len(start['components']) == 3
    checks['idempotent_start_same_pids'] = same['components'] == start['components']
    checks['stop_ended_all_three'] = len(stop['components']) == 3 and all(c['status'] == 'stopped' for c in stop['components'])
    checks['restart_new_pids_all_running'] = restart['all_running'] and len(restart['components']) == 3 and not (
        {c['pid'] for c in restart['components']} & {c['pid'] for c in start['components']})
    journal = [json.loads(line) for line in (folder / 'manager-events.ndjson').read_text().splitlines()]
    checks['startup_reverse_stop_restart_order'] = [(j['event'], j['component']) for j in journal] == (
        [('started', n) for n in ('transport', 'agent-1', 'agent-2')] +
        [('stopped', n) for n in ('agent-2', 'agent-1', 'transport')] +
        [('started', n) for n in ('transport', 'agent-1', 'agent-2')])
    refusal = read(folder / 'unmanaged-port-refusal.json')
    checks['unmanaged_listener_refused'] = refusal['exitCode'] == 1 and 'unmanaged' in refusal['result']['error']
    checks['restart_preserved_before_ui'] = read(folder / 'post-restart-preservation.json')['ok']
    installed = read(folder / 'install-validation.json')
    checks['installed_wheel_validation'] = installed['ok'] and len(installed['entrypoints']) == 6
    # This is a frozen historical deployment, not a claim about later upgrades.
    wheel = folder / 'wheels-final/dingtalk_agent_bridge-0.1.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as archive:
        checks['frozen_wheel_export_and_deployment_source_match'] = (
            digest(wheel.read_bytes()) == installed['wheelSha256'] and
            read(folder / 'migration-intent.json')['codeSha256'] == installed['codeSha256'] and
            all(digest(archive.read('dingtalk_bridge/' + name)) == sha and
                digest((folder / 'source/dingtalk_bridge' / name).read_bytes()) == sha
                for name, sha in installed['codeSha256'].items()))
    checks['same_original_observer'] = before['observer']['pid'] == final['observer']['pid'] and before['observer']['startedAt'] == final['observer']['startedAt'] and final['observer']['samples'] > before['observer']['samples']
    checks['ui_input_observed'] = intent['input'] in (folder / '01-task-input.ax.txt').read_text()
    checks['ui_file_card_observed'] = '下载 编辑 0-dab-manager-001.txt 35 B' in (folder / '02-result-visible.ax.txt').read_text()
    opened = (folder / '04-client-open.ax.txt').read_text()
    checks['client_quicklook_two_line_result_observed'] = all(x in opened for x in ('窗口 快速查看', '0-dab-manager-001.txt', intent['expectedFile']))
    checks['private_ui_captures_present'] = all((folder / n).is_file() and (folder / n).stat().st_size > 1000 for n in
        ('01-task-input.png', '02-result-visible.png', '04-client-open.png'))
    current_matches = all(digest((ROOT / 'dingtalk_bridge' / name).read_bytes()) == sha for name, sha in installed['codeSha256'].items())
    return {'date': '2026-11-11', 'checks': checks, 'newRuntimeTasks': 1, 'newConfirmedReplies': 3,
            'currentWorkspaceCodeMatchesTestedWheel': current_matches,
            'limits': ['macOS/Python 3.14 tested; other POSIX environments unverified',
                       'No boot service, automatic supervision, crash-atomic spawn or forced kill',
                       'UI saw file card and downloaded/opened result; text bubble not separately visible',
                       'Controlled graceful restart, not network partition or expired credentials',
                       '24h original observation continues with recorded maintenance, not yet passed'],
            'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/service-manager-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

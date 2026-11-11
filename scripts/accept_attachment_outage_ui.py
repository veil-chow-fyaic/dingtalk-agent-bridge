#!/usr/bin/env python3
"""Read-only E055: real DWS attachment outage, responsive status, recovery and client file."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs
from frozen_install import frozen_install_matches


def fault_checks(start, restored, attempts, case, pending):
    mid = case['inputEvent']['message_id']
    relevant = [r for r in attempts if '--msg-ids' in r['args'] and r['args'][r['args'].index('--msg-ids') + 1] == mid]
    blocked = [r for r in relevant if r['blocked']]
    success = [r for r in relevant if r['exitCode'] == 0]
    return {
        'bounded_fault_removed_before_expiry': 0 < restored['at'] - start['startedAt'] < start['expiresAt'] - start['startedAt'] <= 180 and restored['manualRemovalBeforeExpiry'],
        'official_input_mget_network_errors': bool(blocked) and all(r['exitCode'] == 1 and r['operation'] == ['chat', '+messages-mget'] and r['socketBound'] and r['error'].get('reason') in {'io_timeout', 'request_timeout'} for r in blocked),
        'official_proxy_failure_cause_present': any('proxyconnect tcp' in r['error'].get('cause', '') for r in blocked),
        'blocked_attempts_bound_to_fault_window': bool(blocked) and all(start['startedAt'] <= r['startedAt'] < restored['at'] for r in blocked),
        'single_successful_original_input_download_after_restore': len(success) == 1 and not success[0]['blocked'] and success[0]['startedAt'] >= restored['at'],
        'durable_media_failure_retains_original_message': pending['message_id'] == mid and pending['state'] == 'media_failed' and pending['attempts'] >= 1,
        'runtime_starts_only_after_network_restore': case['runtimeStartedAt'] > restored['at'],
    }


def content_checks(intent, case, input_bytes, output_bytes, records, status_ax, reply_ax, opened_ax):
    calls = {t['id']: t['function'] for e in records for t in e.get('tool_calls', [])}
    outputs = {e['tool_call_id']: e['content'] for e in records if e.get('role') == 'tool'}
    actual = []
    for cid, fn in calls.items():
        try:
            command = json.loads(fn['arguments'])['command']
            output = json.loads(outputs[cid])
            actual.append(fn['name'] == 'Bash' and all(s in command for s in (
                'python3', 'csv.DictReader', 'Decimal', 'hashlib.sha256(raw)',
                'quantity * unit_price', 'write_text', intent['filename'])) and output == intent['expected'])
        except (ValueError, KeyError, TypeError):
            actual.append(False)
    try:
        correct = len(output_bytes) == 4 and all(json.loads(b) == intent['expected'] for b in output_bytes)
    except (ValueError, UnicodeError):
        correct = False
    response = json.loads(case['job']['result'])['response']
    status = next(json.loads(r['payload'])['text'] for r in case['outbox'] if r['job_id'] == case['statusJob']['id'])
    return {
        'input_fixture_download_runtime_copy_identical': len(input_bytes) == 3 and len({digest(b) for b in input_bytes}) == 1 and digest(input_bytes[0]) == intent['fixtureSha256'],
        'one_actual_python_csv_decimal_sha_tool': len(calls) == 1 and actual == [True],
        'four_result_originals_identical': len(output_bytes) == 4 and len({digest(b) for b in output_bytes}) == 1,
        'all_json_results_correct': correct,
        'complete_waiting_status_visible_in_native_ui': status in status_ax and '执行中 0，排队 0，等待附件 1' in status,
        'complete_result_visible_in_native_ui': '[Agent] ' + response['text'] in reply_ax and all(s in response['text'] for s in ('3', '18', '77.59')),
        'downloaded_json_fully_open_in_quick_look': '快速查看' in opened_ax and bool(output_bytes) and output_bytes[-1].decode().strip() in opened_ax,
    }


def audit():
    f = ROOT / 'local/attachment-outage-20261112'
    before, fault, recovered, final, case, intent, obs = (read(f / n) for n in (
        'ready.json', 'status-during-fault.json', 'after-recovery.json', 'final.json', 'case.json', 'intent.json', 'ui-observations.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key; transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key'), ('events', transport, 'message_id')]:
            live = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_old_rows_preserved'] = all(live.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_runtime_logs_preserved'] = all((ROOT / n).is_file() and digest((ROOT / n).read_bytes()) == sha for n, sha in old['runtimeFiles'].items())
        checks[kind + '_native_session_preserved'] = old['meta'] == end['meta']
        checks[kind + '_history_continued_during_download_outage'] = old['transportMeta'] != fault['routes'][kind]['transportMeta']
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == snapshot['routes'][kind][t] for snapshot in (fault, recovered, final)
                                            for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events', 'runtimeFiles'))
        else:
            direct_cfg = cfg
            jobs, outbox, deliveries = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox'), rows(transport, 'deliveries')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    new_jobs = [case[n] for n in ('prepJob', 'job', 'statusJob')]
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_three_new_completed_jobs'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {j['id'] for j in new_jobs} and all(j in jobs and j['state'] == 'completed' for j in new_jobs)
    checks['authorized_native_inputs'] = all(case[n] == events[case[n]['message_id']] and case[n]['from_self'] is False and case[n]['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds'] for n in ('prepEvent', 'inputEvent', 'statusEvent'))
    checks['preparation_and_status_exact_commands'] = case['prepEvent']['content'] == case['prepJob']['command'] == intent['prompt'] and case['statusEvent']['content'] == '/agent status' and case['statusJob']['command'] == 'status'
    checks['preparation_did_not_process_old_files'] = json.loads(case['prepJob']['result'])['response'] == {'text': '等待该CSV', 'files': []}
    pending = next(j for j in fault['routes']['direct']['jobs'] if j['id'] == case['job']['id'])
    checks['original_file_waited_without_runtime_or_result'] = pending['state'] == 'waiting_media' and pending['result'] is None and not any('/' + pending['id'] + '/' in name for name in fault['routes']['direct']['runtimeFiles'])
    checks['status_completed_while_file_waited'] = case['statusJob'] in fault['routes']['direct']['jobs'] and any(r['job_id'] == case['statusJob']['id'] and r['state'] == 'confirmed' for r in fault['routes']['direct']['outbox'])
    reply_keys = {r['key'] for r in case['outbox']}
    checks['exact_six_confirmed_replies'] = len(reply_keys) == 6 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox']) and all({r['key'] for r in end[t]} - {r['key'] for r in old[t]} == reply_keys for t in ('outbox', 'deliveries'))
    checks['receipts_match_bound_liev_reply_events'] = len(case['deliveries']) == len(case['replyEvents']) == 6 and all(d in deliveries and d['state'] == 'confirmed' for d in case['deliveries']) and all(
        e == events[e['message_id']] and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents']) and all(any(
        d['key'] == r['key'] and d['task_id'] == json.loads(r['receipt'])['task_id'] and d['message_id'] == json.loads(r['receipt'])['message_id'] and d['message_id'] in {e['message_id'] for e in case['replyEvents']} for d in case['deliveries']) for r in case['outbox'])
    checks['no_echo_tasks_or_late_replay'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents']) and all(recovered['routes']['direct'][t] == end[t] for t in ('jobs', 'outbox', 'deliveries', 'events', 'runtimeFiles')) and final['at'] - recovered['at'] > 60
    attempts = []
    for p in (f / 'attempts').glob('*/result.json'):
        r = read(p); r['error'] = json.loads((p.parent / 'stderr').read_bytes() or b'{}').get('error', {})
        attempts.append(r)
    start, restored = read(f / 'offline-start.json'), read(f / 'restored-network.json')
    checks.update(fault_checks(start, restored, attempts, case, read(f / 'inbox-during-fault.json')))
    checks['input_hydrated_without_replacement'] = read(f / 'inbox-after-recovery.json')['state'] == 'normalized' and read(f / 'inbox-after-recovery.json')['message_id'] == case['inputEvent']['message_id']
    checks['same_processes_through_fault_and_recovery'] = read(f / 'setup-start.json')['state'] == read(f / 'manager-before-cleanup.json')['state'] and read(f / 'manager-before-cleanup.json')['status']['all_running']
    checks['healthy_history_during_fault_and_after'] = all(not snapshot['health']['poll_error'] for snapshot in (before, fault, recovered, final))
    checks['run_logs_preserved'] = all(digest((ROOT / n).read_bytes()) == sha for n, sha in case['runFiles'].items())
    model = json.loads(case['job']['model']); workspace = Path(case['workspace']); fixture = ROOT / 'fixtures/dab-download-outage-055.csv'
    inputs = [p.read_bytes() for p in (fixture, Path(model['parts'][0]['path']), workspace / 'inputs' / case['job']['id'] / ('0-' + fixture.name))]
    result = json.loads(case['job']['result']); artifact = result['artifacts'][0]; ledger = read(f / 'result-resources.json')
    checks['one_expected_artifact_and_complete_official_resource'] = result['response']['files'] == ['exports/' + intent['filename']] and len(result['artifacts']) == 1 and ledger['ok'] and not ledger.get('partial') and not ledger.get('failedCount') and len(ledger['downloads']) == 1
    outputs = [p.read_bytes() for p in (workspace / 'exports' / intent['filename'], ROOT / artifact['file'], ROOT / ledger['downloads'][0]['localPath'], f / obs['clientFile'])]
    checks['artifact_digest_matches_bytes'] = artifact['sha256'] == ledger['downloads'][0]['sha256'] == digest(outputs[0])
    records = [json.loads(line) for line in (ROOT / case['runLog']).read_text().splitlines()]
    checks.update(content_checks(intent, case, inputs, outputs, records, (f / 'status-reply.ax.txt').read_text(), (f / 'recovery-reply-attempt1.ax.txt').read_text(), (f / 'opened.ax.txt').read_text()))
    checks['three_native_inputs_attempted_once'] = all(read(f / name)['attempts'] == 1 for name in ('prep-send-attempt.json', 'upload-attempt.json', 'status-send-attempt.json'))
    checks['native_uploaded_file_and_download_complete'] = fixture.name in (f / 'upload-sent.ax.txt').read_text() and '65 B' in (f / 'upload-sent.ax.txt').read_text() and obs['clientFile'] in (f / 'saved.ax.txt').read_text() and '下载完成' in (f / 'saved.ax.txt').read_text() and read(f / 'save-attempt.json')['attempts'] == 1
    checks['six_reviewed_frames_preserved'] = len(obs['frames']) == 6 and all(v['reviewed'] and digest((f / name).read_bytes()) == v['sha256'] for name, v in obs['frames'].items())
    cleanup = read(f / 'cleanup.json'); original = (f / 'service-config-before.json').read_bytes()
    changed = json.loads(original)
    for route in changed['routes']:
        if route['conversationType'] == 'direct': route['binary'] = 'local/attachment-outage-20261112/dws-download-gate'
    checks['only_direct_binary_changed_and_exact_config_restored'] = next(r['configSha256'] for r in read(f / 'setup-start.json')['state']['components'] if r['name'] == 'transport') == digest((json.dumps(changed, ensure_ascii=False, indent=2) + '\n').encode()) and cleanup['configExactRestored'] and digest(original) == intent['configBeforeSha256'] == digest((ROOT / 'local/service-config.json').read_bytes())
    checks['official_binary_unchanged_and_fault_removed'] = digest((ROOT / direct_cfg['binary']).read_bytes()) == intent['officialBinarySha256'] and digest((f / 'dws-download-gate').read_bytes()) == intent['wrapperSha256'] and cleanup['noActiveFault'] and not (f / 'offline.json').exists()
    checks['official_context_and_healthy_services_restored'] = cleanup['contextOfficialBinaryRestored'] and cleanup['manager']['all_running'] and read(f / 'doctor-after-cleanup.json')['ok']
    install = read(ROOT / 'evidence/2026-11-12/download-cache-install.json')
    checks['product_remained_frozen_e054_version'] = cleanup['codeSha256'] == install['codeSha256'] and frozen_install_matches(install, ROOT / 'local/download-cache-20261112')
    checks['original_observer_preserved'] = before['observer']['pid'] == final['observer']['pid'] == 97881 and before['observer']['startedAt'] == final['observer']['startedAt'] and final['observer']['active'] and final['observer']['samples'] > before['observer']['samples']
    return {'date': '2026-11-12', 'evidence': 'E055', 'ok': all(checks.values()), 'checks': checks,
            'faultSeconds': round(restored['at'] - start['startedAt'], 3), 'officialFailedInputDownloads': sum(r['blocked'] for r in attempts),
            'newJobs': 3, 'confirmedReplies': 6, 'clientBytes': len(outputs[-1]),
            'limits': ['Only direct-route official messages-mget child HTTP failed; history, Stream and native client remained online',
                       'No expired credential or partial CDN transfer claimed', 'Setup and cleanup restarted services; recovery itself did not',
                       'Preparation and file were separate native messages; not single-message multi-attachment acceptance',
                       'Original observer remains below 24h; unavailable samples and maintenance retained']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--write-evidence', action='store_true'); args = parser.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.write_evidence: (ROOT / 'evidence/2026-11-12/attachment-outage-ui-ledger.json').write_text(data)
    print(data); raise SystemExit(0 if report['ok'] else 1)

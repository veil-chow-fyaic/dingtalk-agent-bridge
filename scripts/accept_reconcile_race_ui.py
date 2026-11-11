#!/usr/bin/env python3
"""Read-only audit of E052 deployment and its new native DM file task."""
import argparse
import hashlib
import json
from pathlib import Path

from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs
from frozen_install import frozen_install_matches


def content_checks(intent, case, contents, entries, reply_ax, opened_ax):
    expected = intent['expected']
    result = json.loads(case['job']['result'])
    calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
    outputs = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
    tools = []
    for cid, fn in calls.items():
        try:
            command = json.loads(fn['arguments'])['command']
            output = json.loads(outputs[cid])
        except (ValueError, KeyError, TypeError):
            continue
        tools.append(fn['name'] == 'Bash' and all(s in command for s in (
            'python3', 'values = [11, 13, 17]', 'x * x for x in values',
            'sum(squares)', 'write_text', intent['filename'])) and output == expected)
    try:
        correct = len(contents) == 4 and all(json.loads(b) == expected for b in contents)
    except (ValueError, UnicodeError):
        correct = False
    return {
        'actual_python_computation_and_write': any(tools),
        'generated_staged_official_client_bytes_equal': len(contents) == 4 and len({digest(b) for b in contents}) == 1,
        'all_four_json_contents_correct': correct,
        'one_expected_runtime_artifact': result['response']['files'] == ['exports/' + intent['filename']] and len(result['artifacts']) == 1,
        'complete_reply_visible_in_native_ui': '[Agent] ' + result['response']['text'] in reply_ax and all(s in result['response']['text'] for s in ('121', '169', '289', '579')),
        'client_file_fully_opened_in_quick_look': '快速查看' in opened_ax and bool(contents) and contents[-1].decode().strip() in opened_ax,
    }


def audit():
    f = ROOT / 'local/reconcile-race-20261112'
    before, final, case, intent, obs = (read(f / n) for n in ('before.json', 'final.json', 'case.json', 'intent.json', 'ui-observations.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key'), ('events', transport, 'message_id')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_runtime_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        checks[kind + '_native_session_unchanged'] = old['meta'] == end['meta']
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct_cfg = cfg
            jobs, outbox, deliveries = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox'), rows(transport, 'deliveries')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    old, end = before['routes']['direct'], final['routes']['direct']
    job = case['job']; model = json.loads(job['model']); result = json.loads(job['result'])
    checks['exactly_one_new_completed_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']} and job in jobs and job['state'] == 'completed' and job['error'] is None
    checks['authorized_native_input_matches_intent'] = job['command'] == intent['prompt'] and case['event'] == events[model['id']] and case['event']['content'] == intent['prompt'] and case['event']['from_self'] is False and case['event']['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    checks['exact_three_new_confirmed_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']} and len(case['outbox']) == 3 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['exact_three_new_confirmed_deliveries'] = {r['key'] for r in end['deliveries']} - {r['key'] for r in old['deliveries']} == {r['key'] for r in case['outbox']} and len(case['deliveries']) == 3 and all(r in deliveries and r['state'] == 'confirmed' and r['task_id'] and r['message_id'] for r in case['deliveries'])
    checks['replies_bound_to_liev_and_same_route'] = len(case['replyEvents']) == 3 and all(events[e['message_id']] == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] and e['conversation_id'] == direct_cfg['group'] for e in case['replyEvents'])
    checks['receipts_match_delivery_rows_and_history'] = all(any(d['key'] == r['key'] and d['task_id'] == json.loads(r['receipt'])['task_id'] and d['message_id'] == json.loads(r['receipt'])['message_id'] and d['message_id'] in {e['message_id'] for e in case['replyEvents']} for d in case['deliveries']) for r in case['outbox'])
    checks['no_reply_echo_or_task_replay'] = sum(j['command'] == intent['prompt'] for j in jobs) == 1 and all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    log = ROOT / case['runLog']
    checks['runtime_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    generated = Path(intent['workspace']) / 'exports' / intent['filename']
    artifact = result['artifacts'][0]; staged = ROOT / artifact['file']
    resources = read(f / 'json-resources.json')
    checks['official_download_complete'] = resources['ok'] is True and not resources.get('partial') and not resources.get('failedCount') and len(resources['downloads']) == 1
    resource = ROOT / resources['downloads'][0]['localPath']; client = f / obs['clientFile']
    contents = [p.read_bytes() for p in (generated, staged, resource, client)]
    checks['artifact_and_resource_digests_match_bytes'] = artifact['sha256'] == resources['downloads'][0]['sha256'] == digest(contents[0])
    checks['file_payload_matches_runtime_artifact'] = [json.loads(r['payload'])['file'] for r in case['outbox'] if 'file' in json.loads(r['payload'])] == [artifact['file']]
    entries = [json.loads(l) for l in log.read_text().splitlines()]
    checks.update(content_checks(intent, case, contents, entries, (f / 'reply-attempt1.ax.txt').read_text(), (f / 'opened.ax.txt').read_text()))
    checks['single_native_send_attempt'] = read(f / 'send-attempt.json')['attempts'] == 1 and intent['prompt'] in (f / 'sent.ax.txt').read_text()
    checks['native_client_download_complete'] = obs['clientFile'] in (f / 'saved.ax.txt').read_text() and '下载完成' in (f / 'saved.ax.txt').read_text() and str(client.stat().st_size) + ' B' in (f / 'reply-attempt1.ax.txt').read_text()
    checks['reviewed_ui_frames_preserved'] = len(obs['frames']) == 3 and all(v['reviewed'] and digest((f / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    loaded, current = read(f / 'manager-loaded.json'), read(f / 'manager-after-task.json')
    checks['same_loaded_processes_through_ui_task'] = loaded['state'] == current['state'] and current['status']['all_running']
    checks['frozen_tested_install_matches'] = frozen_install_matches(read(ROOT / 'evidence/2026-11-12/reconcile-race-install.json'), f)
    checks['observer_start_and_identity_preserved'] = before['observer']['pid'] == final['observer']['pid'] == 97881 and before['observer']['startedAt'] == final['observer']['startedAt'] and final['observer']['active']
    return {'date': '2026-11-12', 'ok': all(checks.values()), 'checks': checks, 'counts': {k: {t: len(v[t]) for t in ('jobs', 'outbox', 'deliveries', 'events')} for k, v in final['routes'].items()}, 'clientBytes': len(contents[-1]), 'fileSha256': digest(contents[-1]), 'scope': 'New native veil-to-liev DM deployment task, real Python calculation/write, visible reply, client download and Quick Look open. Concurrent race and authorization errors were isolated synthetic tests, not a live DingTalk fault or expired credential test.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output'); a = p.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if a.output:
        (ROOT / a.output).write_text(data)
    print(data)
    raise SystemExit(0 if report['ok'] else 1)

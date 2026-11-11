#!/usr/bin/env python3
"""Read-only audit of the real Kimi task after process-group cleanup deployment."""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/runtime-orphan-20261112'
    before, final, case, intent, obs = (read(folder / n) for n in (
        'before.json', 'final.json', 'case.json', 'intent.json', 'ui-observations.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'),
                                    ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key'), ('events', transport, 'message_id')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct_cfg, direct_folder = cfg, agent
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    job, event = case['job'], case['event']
    model, result = json.loads(job['model']), json.loads(job['result'])
    checks['immutable_completed_job'] = job in jobs and job['state'] == 'completed'
    checks['exact_one_native_text_input'] = len(model['parts']) == 1 and model['parts'][0]['type'] == 'text' and model['parts'][0]['text'].strip() == intent['prompt'] and not model['issues']
    checks['authorized_native_input'] = events.get(model['id']) == event and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    checks['one_send_attempt'] = read(folder / 'send-attempt.json')['attempts'] == 1
    log = ROOT / case['runLog']
    entries = [json.loads(x) for x in log.read_text().splitlines()]
    calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
    results = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
    checks['runtime_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    checks['actual_python_calculation_and_file_write'] = any(fn['name'] == 'Bash' and 'result = 419 * 23' in fn['arguments'] and 'write_text' in fn['arguments'] and results.get(cid) == '9637\n' for cid, fn in calls.items())
    checks['correct_requested_response'] = result['response'] == {'text': '运行器重载验收：419 × 23 = 9637', 'files': ['exports/dab-runtime-cleanup-check.txt']}
    artifacts = result['artifacts']
    data = (folder / obs['clientFile']).read_bytes()
    checks['client_export_staged_exact'] = len(artifacts) == 1 and data == b'419 * 23 = 9637\n' == (ROOT / artifacts[0]['file']).read_bytes() == (direct_folder / 'workspaces/1/exports/dab-runtime-cleanup-check.txt').read_bytes() and digest(data) == artifacts[0]['sha256']
    resource = read(folder / 'file-resources.json')
    checks['official_resource_exact'] = resource['ok'] and resource['failedCount'] == 0 and bool(resource['downloads']) and all((ROOT / r['localPath']).read_bytes() == data for r in resource['downloads'])
    checks['three_confirmed_replies'] = len(case['outbox']) == 3 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['bound_liev_reply_identity'] = len(case['replyEvents']) == 3 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
    checks['no_self_echo_task'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_one_new_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']}
    checks['exact_three_new_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']}
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    checks['full_reply_visible'] = '[Agent] ' + result['response']['text'] in (folder / 'text-reply.ax.txt').read_text()
    checks['client_download_completed'] = '0-dab-runtime-cleanup-check.txt 下载完成' in (folder / 'saved.ax.txt').read_text()
    opened = (folder / 'opened.ax.txt').read_text()
    checks['download_opened_full_text'] = all(s in opened for s in ('快速查看', obs['clientFile'], '419 * 23 = 9637'))
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 4 and all(v['reviewed'] and digest((folder / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    start, deployed = (read(folder / n)['components'] for n in ('manager-before.json', 'manager-after.json'))
    checks['only_agents_reloaded'] = all(a['component'] == b['component'] and a['status'] == b['status'] == 'running' and ((a['pid'] == b['pid']) == (a['component'] == 'transport')) for a, b in zip(start, deployed)) and len(start) == len(deployed) == 3
    checks['observer_same_original_run'] = before['observer']['pid'] == final['observer']['pid'] == read(folder / 'observer-process.json')['pid'] and before['observer']['startedAt'] == final['observer']['startedAt'] and final['observer']['samples'] > before['observer']['samples']
    install = read(ROOT / 'evidence/2026-11-12/runtime-group-install.json')
    checks['tested_installed_modules_match'] = install['ok'] and all(digest((ROOT / 'dingtalk_bridge' / n).read_bytes()) == sha for n, sha in install['codeSha256'].items())
    return {'date': '2026-11-12', 'checks': checks, 'ok': all(checks.values()),
            'clientBytes': len(data), 'clientSha256': digest(data),
            'latestFullSuite': {'tests': 160, 'errors': 2, 'area': 'Existing manager during-shutdown identity protection; unresolved'},
            'scope': 'Real native DM after initial cleanup reload. Later macOS Python <3.13 compatibility path tested with 17 real-process tests and redeployed; no repeated UI task. No live fault injection or OS sandbox claim.',
            'counts': {k: {t: len(v[t]) for t in ('jobs', 'outbox', 'deliveries', 'events')} for k, v in final['routes'].items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: Path(args.output).write_text(encoded)
    print(encoded); raise SystemExit(0 if report['ok'] else 1)

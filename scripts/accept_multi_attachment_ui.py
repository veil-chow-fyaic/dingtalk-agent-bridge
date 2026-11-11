#!/usr/bin/env python3
"""Read-only audit of two native file uploads and a following combined task.

The client split one two-file selection into two messages. This is not proof
of a single message containing multiple attachments. Never sends or replays.
"""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.message_model import media_parts
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/multi-attachment-ui-20261111'
    before, final, cases = (read(folder / n) for n in
                            ('before-ledgers.json', 'final-ledgers.json', 'cases.json'))
    if set(cases) != {'a', 'b', 'join'}:
        return {'ok': False, 'error': 'incomplete_case_coverage'}
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
        if kind == 'group':
            checks['group_unchanged_during_experiment'] = all(
                old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries'))
        else:
            direct_cfg, direct_folder = cfg, agent
            jobs = rows(agent / 'tasks.sqlite3', 'jobs')
            replies = rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    allowed = read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    by_id, by_key = {j['id']: j for j in jobs}, {r['key']: r for r in replies}
    reports, tools = [], {}
    for name, case in cases.items():
        job, event, out = case['job'], case['event'], case['outbox']
        actual = case['replyEvents']
        model, result = json.loads(job['model']), json.loads(job['result'] or '{}')
        log = ROOT / case['runLog']
        log_events = [json.loads(line) for line in log.read_text().splitlines()]
        tools[name] = [t['function'] for e in log_events for t in e.get('tool_calls', [])]
        check = {
            'immutable_completed_job': by_id.get(job['id']) == job and job['state'] == 'completed',
            'authorized_input_committed': events.get(event['message_id']) == event and
                event['from_self'] is False and event['sender_id'] in allowed,
            'one_job_for_input': sum(json.loads(j['model'])['id'] == event['message_id'] for j in jobs) == 1,
            'confirmed_replies': len(out) == (3 if name == 'join' else 2) and all(
                r['state'] == 'confirmed' and by_key.get(r['key']) == r for r in out),
            'bound_reply_identity': len(actual) == len(out) and all(
                events.get(e['message_id']) == e and e['from_self'] is True and
                e['sender_id'] == direct_cfg['selfSenderId'] for e in actual),
            'no_reply_echo_task': all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs)
                                      for e in actual),
            'runtime_log_preserved': digest(log.read_bytes()) == case['runLogSha256'],
        }
        if name in {'a', 'b'}:
            filename = 'dab-batch-a.txt' if name == 'a' else 'dab-batch-b.csv'
            original = (ROOT / 'fixtures' / filename).read_bytes()
            parts = list(media_parts(model))
            check['one_valid_file_per_message'] = len(parts) == 1 and not model.get('issues')
            check['downloaded_original_intact'] = len(parts) == 1 and all(
                p['name'] == filename and Path(p['path']).read_bytes() == original and
                p['sha256'] == digest(original) for p in parts)
            check['staged_input_intact'] = (direct_folder / 'workspaces/1/inputs' / job['id'] /
                                            ('0-' + filename)).read_bytes() == original
            check['actual_runtime_read'] = any(t['name'] == 'Read' and
                Path(json.loads(t['arguments']).get('path', '')).name == '0-' + filename for t in tools[name])
            expected = ('DAB-BATCH-A-20261111', '合成Alpha', '17') if name == 'a' else (
                'DAB-BATCH-B-20261111', 'Beta', '23')
            check['read_content_correct'] = all(m in result.get('response', {}).get('text', '') for m in expected)
            check['no_unrequested_artifact'] = not result.get('artifacts')
        else:
            check['text_followup_without_new_attachment'] = not list(media_parts(model))
            artifacts = result.get('artifacts', [])
            check['one_result_artifact'] = len(artifacts) == 1
            if len(artifacts) == 1:
                artifact = artifacts[0]
                client = folder / Path(artifact['file']).name
                data = client.read_bytes() if client.is_file() else b''
                check['client_download_matches_staged_artifact'] = bool(data) and data == (
                    ROOT / artifact['file']).read_bytes() and digest(data) == artifact['sha256']
                check['combined_report_correct'] = all(m in data.decode('utf-8') for m in (
                    'dab-batch-a.txt', 'dab-batch-b.csv', 'DAB-BATCH-A-20261111',
                    'DAB-BATCH-B-20261111', '合成Alpha', 'Beta', '金额：17', '金额：23', '总额：40'))
                check['actual_runtime_write'] = any(t['name'] == 'Write' and
                    json.loads(t['arguments']).get('path') == 'exports/dab-batch-summary.txt' for t in tools[name])
        reports.append({'case': name, 'checks': check})
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_three_new_jobs'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {
        c['job']['id'] for c in cases.values()}
    checks['exact_seven_new_replies'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {
        r['key'] for c in cases.values() for r in c['outbox']}
    checks['distinct_ordered_messages'] = len({c['event']['message_id'] for c in cases.values()}) == 3 and (
        cases['a']['job']['seq'] < cases['b']['job']['seq'] < cases['join']['job']['seq'])
    checks['same_native_session_and_generation'] = old['meta'] == end['meta'] and bool(old['meta'])
    checks['no_amounts_supplied_in_followup'] = all(n not in cases['join']['job']['command'] for n in ('17', '23', '40'))
    return {'date': '2026-11-11', 'checks': checks, 'cases': reports,
            'runtimeCalls': 3, 'confirmedReplies': 7,
            'clientBehavior': 'One two-file Finder selection/paste became two separate native messages and two tasks',
            'combinedTaskBehavior': 'Two earlier tasks read originals; following task used retained context and wrote report',
            'joinTaskReopenedFiles': any(t['name'] == 'Read' for t in tools['join']),
            'limits': ['Not a single message with multiple attachments',
                       'No automatic debounce or batch coalescing',
                       'Join reused prior read context; not proof that it reopened source files',
                       'Only two small synthetic files in one authorized direct session'],
            'ok': all(checks.values()) and all(all(c['checks'].values()) for c in reports)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/multi-attachment-ledger.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

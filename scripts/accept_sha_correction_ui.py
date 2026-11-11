#!/usr/bin/env python3
"""Read-only audit of an incorrect model conclusion and explicit-source correction."""
import argparse
import json
import re
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/sha-correction-ui-20261112'
    before, final, cases = (read(folder / n) for n in ('before.json', 'final.json', 'cases.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
            direct = cfg
    oldcase = read(folder / 'original-case.json')
    original = json.loads(oldcase['job']['result'])['response']['text']
    exports = read(folder / 'exports-before.json')
    checks['no_export_content_or_mtime_change'] = len(exports) == 15 and exports == read(folder / 'exports-after.json') and all(
        (ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == v['sha256'] and (ROOT / p).stat().st_size == v['size'] and (ROOT / p).stat().st_mtime_ns == v['mtime_ns'] for p, v in exports.items())
    data = (ROOT / next(p for p in exports if p.endswith('/dab-large-png.png'))).read_bytes()
    sha, size = digest(data), len(data)
    prefix = re.search(r'SHA256为([a-f0-9]+)\.\.\.', original).group(1)
    checks['original_wrong_prefix_preserved'] = not sha.startswith(prefix) and oldcase['job'] in jobs and all(r in outbox for r in oldcase['outbox'])
    checks['two_distinct_cases'] = len(cases) == 2 and len({c['job']['id'] for c in cases}) == 2
    texts = []
    for i, c in enumerate(cases):
        job = c['job']; result = json.loads(job['result']); model = json.loads(job['model'])
        intent = read(folder / ('intent.json' if i == 0 else 'comparison-intent.json'))
        text = result['response']['text']; texts.append(text)
        checks[f'case_{i}_immutable_completed_job'] = job in jobs and job['state'] == 'completed'
        checks[f'case_{i}_exact_authorized_input'] = events.get(model['id']) == c['event'] and c['event']['from_self'] is False and c['event']['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds'] and model['parts'][0]['text'].strip() == intent['prompt']
        checks[f'case_{i}_no_file_delivery'] = result['response']['files'] == [] and result['artifacts'] == [] and all('file' not in json.loads(r['payload']) and 'image' not in json.loads(r['payload']) for r in c['outbox'])
        checks[f'case_{i}_two_confirmed_replies'] = len(c['outbox']) == 2 and all(r in outbox and r['state'] == 'confirmed' for r in c['outbox'])
        checks[f'case_{i}_self_replies_no_echo'] = len(c['replyEvents']) == 2 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct['selfSenderId'] and not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in c['replyEvents'])
        log = ROOT / c['runLog']; logs = [json.loads(s) for s in log.read_text().splitlines()]
        tools = [x for x in logs if x.get('role') == 'tool']; calls = [x['function'] for e in logs for x in e.get('tool_calls', [])]
        checks[f'case_{i}_actual_hash_tool_and_immutable_log'] = digest(log.read_bytes()) == c['runLogSha256'] and any(x['name'] == 'Bash' and 'hashlib.sha256' in x['arguments'] for x in calls) and any(sha in x['content'] and str(size) in x['content'] for x in tools)
        checks[f'case_{i}_full_correct_sha_in_reply'] = re.findall(r'[a-f0-9]{64}', text) == [sha] and str(size) in text
        ui = (folder / ('first-reply.ax.txt' if i == 0 else 'correction-reply.ax.txt')).read_text()
        checks[f'case_{i}_complete_reply_in_native_ui'] = '[Agent] ' + text in ui and '通过AI发送' in ui
        checks[f'case_{i}_one_ui_send'] = read(folder / ('send-attempt.json' if i == 0 else 'comparison-send-attempt.json'))['attempts'] == 1
        if i == 1:
            checks['explicit_original_text_supplied'] = intent['original_text'] == original and original in model['parts'][0]['text']
            checks['tool_detects_bad_prefix_good_report'] = any(all(v in x['content'] for v in ('prefix=' + prefix, 'prefix_match=False', 'report_sha_match=True', 'report_bytes_match=True', 'actual_sha256=' + sha)) for x in tools) and any('startswith(prefix)' in x['arguments'] for x in calls)
    checks['first_semantic_failure_preserved'] = '只读核验一致，无需更正' in texts[0] and not sha.startswith(prefix)
    checks['final_correction_explicit'] = '之前“无需更正”不正确' in texts[1] and '不匹配' in texts[1] and 'startswith=False' in texts[1]
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_two_tasks_four_replies'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {c['job']['id'] for c in cases} and {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for c in cases for r in c['outbox']}
    checks['same_native_session'] = bool(old['meta']) and old['meta'] == end['meta']
    frames = read(folder / 'ui-observations.json')['frames']
    checks['reviewed_ui_frames_intact'] = set(frames) == {'sent.png', 'first-reply.png', 'correction-reply.png'} and all(v['reviewed'] and digest((folder / p).read_bytes()) == v['sha256'] for p, v in frames.items())
    return {'date': '2026-11-12', 'checks': checks, 'passed': all(checks.values()),
            'original_task_fully_correct': False, 'first_followup_semantically_correct': False,
            'explicit_source_correction_passed': all(checks.values()),
            'bytes': size, 'sha256': sha,
            'limits': ['Original wrong SHA and first false no-correction conclusion remain unchanged',
                       'Successful explicit-source comparison is not a general guarantee of model truthfulness',
                       'No files regenerated or sent; direct conversation only']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write-evidence', action='store_true'); a = p.parse_args()
    r = audit()
    if a.write_evidence:
        (ROOT / 'evidence/2026-11-12/sha-correction-ui-ledger.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(r, ensure_ascii=False, indent=2)); raise SystemExit(0 if r['passed'] else 1)

#!/usr/bin/env python3
"""Read-only audit of one native direct message containing two distinct images."""
import argparse
import base64
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/multi-image-ui-20261112'
    before, final, case, intent = (read(folder / n) for n in ('before.json', 'final.json', 'case.json', 'intent.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_runtime_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct_cfg, direct_folder = cfg, agent
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    job, event = case['job'], case['event']
    model, result = json.loads(job['model']), json.loads(job['result'])
    checks['immutable_completed_job'] = job in jobs and job['state'] == 'completed'
    checks['one_job_for_input'] = sum(json.loads(j['model'])['id'] == model['id'] for j in jobs) == 1
    checks['authorized_native_input'] = events.get(model['id']) == event and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    checks['exact_text_then_two_images'] = [p['type'] for p in model['parts']] == ['text', 'image', 'image'] and not model['issues']
    checks['prompt_preserved_no_answer_leak'] = model['parts'][0]['text'].strip() == intent['prompt'] and all(s not in job['command'] for s in ('31', '46', '77', '橙色', '蓝色'))
    media = [p for p in model['parts'] if p['type'] == 'image']
    fixtures = intent['fixtures']
    checks['two_distinct_images'] = len(media) == len(fixtures) == 2 and len({p['sha256'] for p in media}) == 2
    log = ROOT / case['runLog']
    log_events = [json.loads(line) for line in log.read_text().splitlines()]
    calls = {t['id']: t['function'] for e in log_events for t in e.get('tool_calls', [])}
    tool_outputs = {e['tool_call_id']: e['content'] for e in log_events if e.get('role') == 'tool'}
    checks['runtime_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    for index, fixture in enumerate(fixtures):
        original = (ROOT / fixture['file']).read_bytes()
        part = media[index] if index < len(media) else {}
        checks[f'image{index}_original_order_and_bytes'] = bool(part) and digest(original) == fixture['sha256'] == part['sha256'] and Path(part['path']).read_bytes() == original
        media_calls = [(cid, json.loads(fn['arguments'])['path']) for cid, fn in calls.items() if fn['name'] == 'ReadMediaFile' and Path(json.loads(fn['arguments'])['path']).name.startswith(str(index) + '-')]
        checks[f'image{index}_actual_media_read_once'] = len(media_calls) == 1
        if len(media_calls) == 1:
            cid, path = media_calls[0]
            staged = direct_folder / 'workspaces/1' / path
            checks[f'image{index}_staged_intact'] = staged.read_bytes() == original
            output = tool_outputs.get(cid, '[]')
            output = json.loads(output) if isinstance(output, str) else output
            urls = [p['imageUrl']['url'] for p in output if p.get('type') == 'image_url']
            checks[f'image{index}_runtime_received_image_bytes'] = len(urls) == 1 and urls[0].startswith('data:image/png;base64,') and base64.b64decode(urls[0].split(',', 1)[1]) == original
    checks['initial_text_read_errors_retained'] = sum(fn['name'] == 'Read' and 'Only text files can be read' in str(tool_outputs.get(cid)) for cid, fn in calls.items()) == 2
    checks['actual_pixel_measurements'] = any(fn['name'] == 'Bash' and all(s in str(tool_outputs.get(cid)) for s in ('(320, 180)', '(240, 200)', '(237, 114, 36)', '(38, 106, 220)')) for cid, fn in calls.items())
    artifact = result['artifacts'][0]
    client = folder / '0-dab-multi-image-report.txt'
    data = client.read_bytes()
    checks['one_report_downloaded_intact'] = len(result['artifacts']) == 1 and len(data) == 420 and data == (ROOT / artifact['file']).read_bytes() and digest(data) == artifact['sha256']
    checks['actual_report_write'] = any(fn['name'] == 'Write' and 'Wrote 420 bytes' in str(tool_outputs.get(cid)) for cid, fn in calls.items())
    checks['report_correct_order_content'] = all(s in data.decode() for s in ('DAB-MULTIIMG-A', 'DAB-MULTIIMG-B', '橙色', '蓝色', '矩形', '圆形', '320 × 180', '240 × 200', '31 + 46 = 77')) and data.index(b'DAB-MULTIIMG-A') < data.index(b'DAB-MULTIIMG-B')
    checks['three_confirmed_replies'] = len(case['outbox']) == 3 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['bound_reply_identity'] = len(case['replyEvents']) == 3 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
    checks['no_reply_echo_task'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_one_new_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']}
    checks['exact_three_new_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']}
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    observations = read(folder / 'ui-observations.json')
    checks['reviewed_frames_preserved'] = set(observations['frames']) == {'composed.png', 'composed-top.png', 'sent.png', 'result-card.png', 'opened.png'} and all(v['reviewed'] and digest((folder / p).read_bytes()) == v['sha256'] for p, v in observations['frames'].items())
    checks['native_draft_and_sent_contain_two_images'] = all((folder / p).read_text().count('[附带的图像]') >= 2 for p in ('composed.ax.txt', 'sent.ax.txt'))
    checks['native_report_open_content'] = data.decode().strip() in (folder / 'opened.ax.txt').read_text()
    return {'date': '2026-11-12', 'checks': checks, 'runtimeCalls': 1, 'confirmedReplies': 3,
            'clientReportBytes': len(data), 'clientReportSha256': digest(data),
            'limits': ['Direct single-message two PNG images only; not multiple arbitrary files', 'Two initial Read calls rejected images; corrected ReadMediaFile calls and Bash succeeded', 'Short text reply not separately viewed; file card and downloaded report opened', 'No group/quote/native voice coverage'], 'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args(); report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/multi-image-ui-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

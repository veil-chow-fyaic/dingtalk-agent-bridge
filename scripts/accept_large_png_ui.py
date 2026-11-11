#!/usr/bin/env python3
"""Read-only >2MiB PNG file-delivery audit; model short-SHA error stays a failure."""
import argparse
import json
import random
import re
from PIL import Image
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    f = ROOT / 'local/large-png-ui-20261112'
    before, final, case, intent = (read(f / n) for n in ('before.json', 'final.json', 'case.json', 'intent.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key; transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group': checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct, workspace = cfg, agent / 'workspaces/1'
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
            uploads = rows(transport, 'image_uploads')
    job = case['job']; model, result = json.loads(job['model']), json.loads(job['result'])
    checks['immutable_completed_job'] = job in jobs and job['state'] == 'completed'
    checks['exact_authorized_input'] = events.get(model['id']) == case['event'] and case['event']['from_self'] is False and case['event']['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds'] and model['parts'][0]['text'].strip() == intent['prompt']
    log = ROOT / case['runLog']; logs = [json.loads(s) for s in log.read_text().splitlines()]
    calls = [c['function'] for e in logs for c in e.get('tool_calls', [])]
    checks['actual_python_tool_and_log_preserved'] = len(calls) == 1 and calls[0]['name'] == 'Bash' and all(s in calls[0]['arguments'] for s in ('random.Random(29)', 'compress_level=0', 'hashlib.sha256')) and digest(log.read_bytes()) == case['runLogSha256']
    artifacts = result['artifacts']; data = (f / 'large-png-received.png').read_bytes(); report = (f / '1-dab-large-png-report.txt').read_bytes()
    checks['over_2mib_file_boundary'] = len(data) == 3147861 and len(data) > 2 * 1024 * 1024
    with Image.open(f / 'large-png-received.png') as im:
        checks['exact_generated_pixels'] = im.format == 'PNG' and im.size == (1024, 1024) and im.mode == 'RGB' and im.tobytes() == random.Random(29).randbytes(1024 * 1024 * 3)
    checks['two_files_not_native_image_upload'] = len(artifacts) == 2 and sum('file' in json.loads(r['payload']) for r in case['outbox']) == 2 and not any('image' in json.loads(r['payload']) for r in case['outbox']) and not any(u['key'] in {r['key'] for r in case['outbox']} for u in uploads)
    for i, content in enumerate((data, report)):
        checks[f'artifact_{i}_export_stage_client_exact'] = content == (ROOT / artifacts[i]['file']).read_bytes() == (workspace / result['response']['files'][i]).read_bytes() and digest(content) == artifacts[i]['sha256']
        resources = read(f / f'resources-{i}.json')
        checks[f'artifact_{i}_official_resource_exact'] = resources['ok'] and bool(resources['downloads']) and all((ROOT / r['localPath']).read_bytes() == content for r in resources['downloads'])
    checks['report_metadata_correct'] = len(report) == 198 and all(s in report.decode() for s in ('PNG', '1024 × 1024', str(len(data)), digest(data)))
    checks['four_confirmed_replies'] = len(case['outbox']) == 4 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['bound_self_replies_no_echo'] = len(case['replyEvents']) == 4 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct['selfSenderId'] and not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['one_new_task_four_outbox'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']} and {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']}
    checks['same_native_session'] = bool(old['meta']) and old['meta'] == end['meta']
    ui = read(f / 'ui-observations.json')
    checks['reviewed_ui_frames_intact'] = set(ui['frames']) == {'sent.png','report-opened.png','file-card.png','viewer.png','image-opened.png'} and all(v['reviewed'] and digest((f / p).read_bytes()) == v['sha256'] for p, v in ui['frames'].items())
    checks['report_opened_ui'] = report.decode().strip() in (f / 'report-loaded.ax.txt').read_text()
    checks['png_opened_ui'] = 'large-png-received.png' in (f / 'image-opened.ax.txt').read_text() and '文本 文件' in (f / 'file-card.ax.txt').read_text()
    checks['one_ui_send_attempt'] = read(f / 'send-attempt.json')['attempts'] == 1
    claimed = re.findall(r'[a-f0-9]{32,64}', result['response']['text'])
    short_correct = bool(claimed) and all(digest(data).startswith(s) for s in claimed)
    return {'date':'2026-11-12','checks':checks,'file_delivery_passed':all(checks.values()),
            'task_fully_correct':all(checks.values()) and short_correct,
            'model_short_sha_correct':short_correct,'model_short_sha_error_preserved':not short_correct,
            'clientPng':{'bytes':len(data),'sha256':digest(data),'dimensions':[1024,1024]},
            'clientReport':{'bytes':len(report),'sha256':digest(report)},
            'limits':['Original model short response contains incorrect truncated SHA; full downloaded report is correct',
                      'File protocol with client image preview; not >2MiB native image protocol support',
                      'Direct outbound sample only; no group or upload claim']}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args();r=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-12/large-png-ui-ledger.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['file_delivery_passed'] else 1)

#!/usr/bin/env python3
"""Read-only audit of native JPEG input, real rotation, and client downloads."""
import argparse
import base64
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def rotation_errors(source, output):
    """Decoded-image errors; JPEG re-encoding is lossy, transport must be exact."""
    with Image.open(source) as src, Image.open(output) as out:
        rgb, actual = src.convert('RGB'), out.convert('RGB')
        if actual.size != (rgb.height, rgb.width):
            return None
        return {name: sum(ImageStat.Stat(ImageChops.difference(rgb.transpose(turn), actual)).mean) / 3
                for name, turn in [('clockwise', Image.Transpose.ROTATE_270), ('counterclockwise', Image.Transpose.ROTATE_90)]}


def audit():
    folder = ROOT / 'local/jpeg-ui-20261112'
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
            uploads = rows(transport, 'image_uploads')
    job, event = case['job'], case['event']
    model, result = json.loads(job['model']), json.loads(job['result'])
    checks['immutable_completed_job'] = job in jobs and job['state'] == 'completed'
    checks['one_job_for_input'] = sum(json.loads(j['model'])['id'] == model['id'] for j in jobs) == 1
    checks['authorized_native_input'] = events.get(model['id']) == event and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    checks['one_text_plus_jpeg'] = [p['type'] for p in model['parts']] == ['text', 'image'] and not model['issues']
    checks['exact_prompt_no_answer_leak'] = model['parts'][0]['text'].strip() == intent['prompt'] and all(s not in job['command'] for s in ('58', '400', '240', 'DAB-JPEG-029'))
    part = model['parts'][1]
    fixture = ROOT / intent['fixture']; original = fixture.read_bytes()
    checks['source_original_bytes'] = len(original) == intent['bytes'] == 16061 and digest(original) == intent['sha256'] == part['sha256'] and Path(part['path']).read_bytes() == original
    with Image.open(fixture) as im:
        checks['source_jpeg_dimensions'] = im.format == 'JPEG' and im.size == (400, 240)
    log = ROOT / case['runLog']; log_events = [json.loads(line) for line in log.read_text().splitlines()]
    calls = {t['id']: t['function'] for e in log_events for t in e.get('tool_calls', [])}
    outputs = {e['tool_call_id']: e['content'] for e in log_events if e.get('role') == 'tool'}
    checks['runtime_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    media_calls = [(cid, json.loads(fn['arguments'])['path']) for cid, fn in calls.items() if fn['name'] == 'ReadMediaFile' and json.loads(fn['arguments'])['path'].startswith('inputs/')]
    checks['actual_source_media_read_once'] = len(media_calls) == 1
    if len(media_calls) == 1:
        cid, path = media_calls[0]
        checks['runtime_staged_source_intact'] = (direct_folder / 'workspaces/1' / path).read_bytes() == original
        parts = outputs.get(cid, '[]'); parts = json.loads(parts) if isinstance(parts, str) else parts
        urls = [p['imageUrl']['url'] for p in parts if p.get('type') == 'image_url']
        checks['runtime_received_source_jpeg_bytes'] = len(urls) == 1 and urls[0].startswith('data:image/jpeg;base64,') and base64.b64decode(urls[0].split(',', 1)[1]) == original
    checks['initial_text_read_error_retained'] = sum(fn['name'] == 'Read' and 'Only text files can be read' in str(outputs.get(cid)) for cid, fn in calls.items()) == 1
    checks['actual_rotation_tool'] = any(fn['name'] == 'Bash' and 'Image.Transpose.ROTATE_270' in fn['arguments'] and "'JPEG'" in str(outputs.get(cid)) and '(240, 400)' in str(outputs.get(cid)) for cid, fn in calls.items())
    artifacts = result['artifacts']; image_file = ROOT / artifacts[0]['file']; image_bytes = image_file.read_bytes()
    observations = read(folder / 'ui-observations.json'); client = folder / observations['clientImage']
    checks['two_artifacts'] = len(artifacts) == 2 and result['response']['files'] == ['exports/dab-jpeg-rotated.jpg', 'exports/dab-jpeg-report.txt']
    checks['output_staged_export_exact'] = (direct_folder / 'workspaces/1/exports/dab-jpeg-rotated.jpg').read_bytes() == image_bytes and digest(image_bytes) == artifacts[0]['sha256']
    checks['client_image_exact'] = len(image_bytes) == 8234 and client.read_bytes() == image_bytes
    with Image.open(client) as im:
        checks['client_content_is_jpeg_despite_png_suffix'] = im.format == 'JPEG' and im.size == (240, 400) and client.name.endswith('.jpg.png')
    errors = rotation_errors(fixture, client)
    checks['independent_clockwise_rotation'] = errors is not None and errors['clockwise'] < 3 and errors['counterclockwise'] > 50
    report = (folder / '1-dab-jpeg-report.txt').read_bytes()
    checks['client_report_exact'] = len(report) == 295 and report == (ROOT / artifacts[1]['file']).read_bytes() and digest(report) == artifacts[1]['sha256']
    checks['actual_report_write'] = any(fn['name'] == 'Write' and 'Wrote 295 bytes' in str(outputs.get(cid)) for cid, fn in calls.items())
    checks['report_correct'] = all(s in report.decode() for s in ('400 × 240', '240 × 400', 'DAB-JPEG-029', '58', '顺时针旋转90度', 'JPEG'))
    for kind, data in [('image', image_bytes), ('file', report)]:
        resources = read(folder / (kind + '-resources.json'))
        checks[kind + '_official_resources_intact'] = resources['ok'] and bool(resources['downloads']) and resources['failedCount'] == 0 and all((ROOT / r['localPath']).read_bytes() == data for r in resources['downloads'])
    image_rows = [r for r in case['outbox'] if 'image' in json.loads(r['payload'])]
    checks['one_native_image_delivery'] = len(image_rows) == 1 and any(u['key'] == image_rows[0]['key'] and u['state'] == 'uploaded' and u['media_id'].startswith('$') for u in uploads)
    checks['four_confirmed_replies'] = len(case['outbox']) == 4 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['bound_reply_identity'] = len(case['replyEvents']) == 4 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
    checks['no_reply_echo_task'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_one_new_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']}
    checks['exact_four_new_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']}
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    checks['one_send_attempt'] = read(folder / 'send-attempt.json')['attempts'] == 1
    checks['reviewed_frames_preserved'] = set(observations['frames']) == {'composed.png', 'composed-top.png', 'sent.png', 'report-opened.png', 'image-search.png', 'viewer.png', 'image-opened.png'} and all(v['reviewed'] and digest((folder / p).read_bytes()) == v['sha256'] for p, v in observations['frames'].items())
    checks['report_opened_ui'] = report.decode().strip() in (folder / 'report-opened.ax.txt').read_text()
    checks['image_opened_ui'] = 'rotated-received.jpg.png' in (folder / 'image-opened.ax.txt').read_text() and 'DAB-JPEG-029' in (folder / 'image-opened.ax.txt').read_text()
    return {'date': '2026-11-12', 'checks': checks, 'runtimeCalls': 1, 'confirmedReplies': 4,
            'source': {'bytes': len(original), 'sha256': digest(original), 'format': 'JPEG', 'dimensions': [400, 240]},
            'clientImage': {'bytes': len(image_bytes), 'sha256': digest(image_bytes), 'format': 'JPEG', 'dimensions': [240, 400], 'savedSuffix': '.jpg.png'},
            'clientReport': {'bytes': len(report), 'sha256': digest(report)}, 'decodedRotationMAE': errors,
            'limits': ['Direct chat only; group scope confirmation pending', 'Short text reply not separately viewed', 'Client forced PNG suffix; bytes remain exact JPEG', 'Lossy re-encoding by runtime; no transport compression observed', 'Not arbitrary multi-attachment/native voice/EXIF orientation coverage'], 'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args(); report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/jpeg-ui-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

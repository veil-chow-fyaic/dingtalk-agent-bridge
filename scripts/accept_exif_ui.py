#!/usr/bin/env python3
"""Read-only audit of native EXIF-6 JPEG input and upright PNG delivery."""
import argparse
import base64
import json
from pathlib import Path

from PIL import Image, ImageChops
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def image_checks(source, output):
    # Independent from runtime's ImageOps.exif_transpose: explicit EXIF-6 transpose.
    with Image.open(source) as src, Image.open(output) as out:
        expected = src.convert('RGB').transpose(Image.Transpose.ROTATE_270)
        actual = out.convert('RGB')
        return {
            'source_exif6_only': src.format == 'JPEG' and src.size == (460, 300) and dict(src.getexif()) == {274: 6},
            'output_png_upright_size': out.format == 'PNG' and out.size == (300, 460),
            'output_orientation_removed': out.getexif().get(274) is None,
            'independent_pixels_exact': expected.size == actual.size and ImageChops.difference(expected, actual).getbbox() is None,
        }


def audit():
    folder = ROOT / 'local/exif-ui-20261112'
    before, final, case, intent, obs = (read(folder / n) for n in ('before.json', 'final.json', 'case.json', 'intent.json', 'ui-observations.json'))
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
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
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
    checks['single_text_and_jpeg'] = [p['type'] for p in model['parts']] == ['text', 'image'] and not model['issues']
    checks['exact_prompt_without_answers'] = model['parts'][0]['text'].strip() == intent['prompt'] and all(x not in job['command'] for x in ('460', '300', '73', 'EXIF-037', 'Orientation=6'))
    source = ROOT / intent['fixture']; original = source.read_bytes(); part = model['parts'][1]
    checks['source_original_bytes'] = len(original) == intent['bytes'] == 23810 and digest(original) == intent['sha256'] == part['sha256'] and Path(part['path']).read_bytes() == original
    log = ROOT / case['runLog']; entries = [json.loads(x) for x in log.read_text().splitlines()]
    calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
    results = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
    checks['runtime_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    media = [(cid, json.loads(fn['arguments'])['path']) for cid, fn in calls.items() if fn['name'] == 'ReadMediaFile' and json.loads(fn['arguments'])['path'].startswith('inputs/')]
    checks['actual_input_media_read_once'] = len(media) == 1
    if len(media) == 1:
        cid, path = media[0]
        checks['runtime_staged_input_exact'] = (direct_folder / 'workspaces/1' / path).read_bytes() == original
        content = results.get(cid, '[]'); content = json.loads(content) if isinstance(content, str) else content
        urls = [p['imageUrl']['url'] for p in content if p.get('type') == 'image_url']
        checks['runtime_received_original_jpeg'] = len(urls) == 1 and urls[0].startswith('data:image/jpeg;base64,') and base64.b64decode(urls[0].split(',', 1)[1]) == original
    checks['initial_read_error_retained'] = sum(fn['name'] == 'Read' and 'Only text files can be read' in str(results.get(cid)) for cid, fn in calls.items()) == 1
    checks['actual_exif_metadata_read'] = any(fn['name'] == 'Bash' and 'getexif' in fn['arguments'] and 'orientation 6' in str(results.get(cid)) and 'encoded_size (460, 300)' in str(results.get(cid)) for cid, fn in calls.items())
    checks['actual_exif_transpose_and_verification'] = any(fn['name'] == 'Bash' and 'ImageOps.exif_transpose' in fn['arguments'] and "'upright_size': (300, 460)" in str(results.get(cid)) and "'output_orientation': None" in str(results.get(cid)) for cid, fn in calls.items())
    artifacts = result['artifacts']; image_file = ROOT / artifacts[0]['file']; image_bytes = image_file.read_bytes(); client = folder / obs['clientImage']
    checks['two_requested_artifacts'] = len(artifacts) == 2 and result['response']['files'] == ['exports/dab-exif-upright.png', 'exports/dab-exif-report.txt']
    checks['export_and_staged_exact'] = (direct_folder / 'workspaces/1/exports/dab-exif-upright.png').read_bytes() == image_bytes and digest(image_bytes) == artifacts[0]['sha256']
    checks['client_image_exact'] = client.read_bytes() == image_bytes and len(image_bytes) == 30666
    checks.update(image_checks(source, client))
    report = (folder / obs['clientReport']).read_bytes()
    checks['client_report_exact'] = len(report) == 462 and report == (ROOT / artifacts[1]['file']).read_bytes() and digest(report) == artifacts[1]['sha256']
    checks['actual_report_write'] = any(fn['name'] == 'Write' and 'Wrote 462 bytes' in str(results.get(cid)) for cid, fn in calls.items())
    checks['report_correct'] = all(x in report.decode() for x in ('编码像素尺寸：460 × 300', 'Orientation：6', '按方向显示后的尺寸：300 × 460', 'EXIF-037', '数值：73', 'PNG未携带Orientation'))
    text = result['response']['text']
    checks['short_reply_correct'] = all(x in text for x in ('460×300', 'Orientation=6', '300×460', 'EXIF-037', '数值73'))
    for kind, data in [('image', image_bytes), ('file', report)]:
        resources = read(folder / (kind + '-resources.json'))
        checks[kind + '_official_resources_exact'] = resources['ok'] and bool(resources['downloads']) and resources['failedCount'] == 0 and all((ROOT / r['localPath']).read_bytes() == data for r in resources['downloads'])
    image_rows = [r for r in case['outbox'] if 'image' in json.loads(r['payload'])]
    checks['native_image_uploaded_and_delivered'] = len(image_rows) == 1 and any(u['key'] == image_rows[0]['key'] and u['state'] == 'uploaded' and u['media_id'].startswith('$') for u in uploads)
    checks['four_confirmed_replies'] = len(case['outbox']) == 4 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['bound_liev_reply_identity'] = len(case['replyEvents']) == 4 and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
    checks['no_self_echo_task'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_one_new_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']}
    checks['exact_four_new_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']}
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    checks['one_send_attempt'] = read(folder / 'send-attempt.json')['attempts'] == 1
    frames = {'composed.png', 'sent.png', 'input-scroll.png', 'output-bubble.png', 'viewer.png', 'image-opened.png', 'report-opened.png', 'text-reply.png'}
    checks['reviewed_frames_preserved'] = set(obs['frames']) == frames and all(v['reviewed'] and digest((folder / p).read_bytes()) == v['sha256'] for p, v in obs['frames'].items())
    checks['report_opened_ui_full_text'] = report.decode().strip() in (folder / 'report-opened.ax.txt').read_text()
    checks['image_opened_ui'] = 'Image Preview: exif-upright-received.png' in (folder / 'image-opened.ax.txt').read_text()
    checks['short_reply_full_ui'] = '[Agent] ' + text in (folder / 'text-reply.ax.txt').read_text()
    return {'date': '2026-11-12', 'checks': checks, 'runtimeCalls': 1, 'confirmedReplies': 4,
            'source': {'bytes': len(original), 'sha256': digest(original), 'format': 'JPEG', 'encodedSize': [460, 300], 'orientation': 6},
            'clientImage': {'bytes': len(image_bytes), 'sha256': digest(image_bytes), 'format': 'PNG', 'size': [300, 460], 'orientation': None},
            'clientReport': {'bytes': len(report), 'sha256': digest(report)},
            'limits': ['Direct chat; one synthetic EXIF orientation (6)', 'Not mirrored orientations 2/4/5/7, other metadata, HEIC, animation, group or all platforms', 'Initial runtime Read error preserved; recovered with actual image tools', 'Native input chat top/bottom viewports observed; input viewer not opened'], 'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args(); report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/exif-ui-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

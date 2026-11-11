#!/usr/bin/env python3
"""Read-only audit of WAV/MP4 direct-chat originals and two real Kimi tasks.

Never sends, replays, or modifies runtime ledgers. Native UI observations are
separate evidence; file protocol types are not inferred from playable previews.
"""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_native_image_bridge import rows, same_file
from accept_wav_direct import audit as wav_out_audit
from dingtalk_bridge.message_model import materialize, media_parts, normalize
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/audio-video-ui-20261111'
    before = read(folder / 'inbound-baseline.json')['routes']
    configs = list(route_configs(read(ROOT / 'local/service-config.json')))
    preserved = {}
    for cfg, state in configs:
        route = cfg['conversationType']
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        scope = json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], route])
        agent = ROOT / 'local/agents' / digest(scope.encode())[:24] / 'tasks.sqlite3'
        for name, db, identity in [('deliveries', transport, 'key'),
                                   ('jobs', agent, 'id'), ('outbox', agent, 'key')]:
            current = {r[identity]: r for r in rows(db, 'SELECT * FROM '+name)}
            old = before[route][name]
            preserved[f'{route}_{name}_unchanged'] = bool(old) and all(
                current.get(r[identity]) == r for r in old)
    cfg, state = next((c, s) for c, s in configs if c['conversationType'] == 'direct')
    cache = ROOT / 'local/runtime/routes' / state
    events = {r['message_id']: json.loads(r['body']) for r in
              rows(cache / 'bridge.sqlite3', 'SELECT message_id,body FROM events')}
    scope = json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], 'direct'])
    agent = ROOT / 'local/agents' / digest(scope.encode())[:24] / 'tasks.sqlite3'
    jobs, outbox = rows(agent, 'SELECT * FROM jobs'), rows(agent, 'SELECT * FROM outbox')
    allowed = read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    cases = [{'case': 'direct-wav-out', 'checks': wav_out_audit()['checks']}]
    fixtures = {'wav': ROOT / 'fixtures/dab-audio-001.wav',
                'mp4': ROOT / 'fixtures/dab-video-001.mp4'}
    markers = {'wav': ('16000', '1.000', '440', '单声道'),
               'mp4': ('H.264', '320×180', '10', '1', '蓝色', '无音频')}
    artifacts = {}
    for kind, direction in [('wav', 'in'), ('mp4', 'out'), ('mp4', 'in')]:
        case = f'direct-{kind}-{direction}'
        saved = read(folder / (case + '-ledger.json'))
        event, ledger = saved['event'], saved['ledger']
        original = fixtures[kind].read_bytes()
        checks = {
            'committed_event_matches': events.get(event['message_id']) == event,
            'correct_direction': event['from_self'] is (direction == 'out'),
            'file_projection': event['content'].startswith('[文件]'),
            'one_original_resource': len(ledger['downloads']) == 1 and all(
                same_file(ROOT / p['localPath'], original) for p in ledger['downloads']),
        }
        try:
            model = materialize(normalize(event, cfg), ledger, ROOT, cache / 'downloads')
            checks['unambiguous_model'] = not model['issues'] and len(list(media_parts(model))) == 1
        except (ValueError, OSError):
            checks['unambiguous_model'] = False
        matched = [j for j in jobs if json.loads(j['model'])['id'] == event['message_id']]
        if direction == 'out':
            receipt = read(ROOT / 'local/probes/media-matrix-20261111/direct-mp4.json')['receipt']
            checks.update(
                confirmed=receipt['state'] == 'confirmed' and receipt['message_id'] == event['message_id'],
                bound_sender=event['sender_id'] == cfg['selfSenderId'],
                client_original=same_file(folder / 'direct-received.mp4', original),
                no_self_task=not matched,
            )
        else:
            checks['authorized_input_sender'] = event['sender_id'] in allowed
            checks['one_completed_task'] = len(matched) == 1 and matched[0]['state'] == 'completed'
            if len(matched) == 1:
                job = matched[0]
                checks['frozen_task_matches'] = job == read(folder / f'direct-{kind}-task.json')['job']
                result = json.loads(job['result'] or '{}')
                text = result.get('response', {}).get('text', '')
                checks['analysis_content'] = all(m in text for m in markers[kind])
                replies = [r for r in outbox if r['job_id'] == job['id']]
                checks['ack_answer_artifact_confirmed'] = len(replies) == 3 and all(r['state'] == 'confirmed' for r in replies)
                reply_events = [events.get(json.loads(r['receipt'] or '{}').get('message_id')) for r in replies]
                checks['reply_sender_and_no_echo'] = bool(reply_events) and all(
                    e and e['from_self'] and e['sender_id'] == cfg['selfSenderId'] and not any(
                        json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in reply_events)
                outputs = result.get('artifacts', [])
                checks['one_result_file'] = len(outputs) == 1
                if len(outputs) == 1:
                    output = outputs[0]
                    client = folder / Path(output['file']).name
                    data = (ROOT / output['file']).read_bytes()
                    checks['client_result_original'] = same_file(client, data) and digest(data) == output['sha256']
                    report_markers = ('16000', '1.000', '440') if kind == 'wav' else ('H.264', '320×180', '10', '1.000', '蓝色')
                    checks['downloaded_result_content'] = client.exists() and all(m in client.read_text() for m in report_markers)
                    artifacts[kind] = {'bytes': len(data), 'sha256': digest(data)}
        cases.append({'case': case, 'checks': checks})
    old_ids = {j['id'] for j in before['direct']['jobs']}
    expected_ids = {read(folder / f'direct-{k}-task.json')['job']['id'] for k in fixtures}
    # Later experiments may add tasks. Scope this assertion to the frozen final
    # snapshot rather than allowing their existence to rewrite this experiment.
    final = read(folder / 'final-direct-jobs.json')
    preserved['exactly_two_new_tasks'] = {j['id'] for j in final if j['id'] not in old_ids} == expected_ids
    preserved['frozen_final_tasks_unchanged'] = all({j['id']: j for j in jobs}.get(j['id']) == j for j in final)
    expected = {f'direct-{k}-{d}' for k in fixtures for d in ('in', 'out')}
    coverage = len(cases) == 4 and {c['case'] for c in cases} == expected
    return {'date': '2026-11-11', 'cases': cases, 'checks': preserved,
            'exact_direct_case_coverage': coverage,
            'fixtures': {k: {'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())} for k, p in fixtures.items()},
            'analysisArtifacts': artifacts,
            'ok': coverage and all(preserved.values()) and all(all(c['checks'].values()) for c in cases),
            'completedFileCases': 4, 'requiredFileCases': 8, 'matrixComplete': False,
            'nativeVoiceBubble': False, 'videoSendProtocol': 'file',
            'mp4ClientPresentation': 'playable video preview; client original downloaded and opened in Finder Quick Look',
            'group': 'not_sent_pending_membership_scope_confirmation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/audio-video-direct-ledger.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

#!/usr/bin/env python3
"""Read-only XLSX/ZIP UI experiment audit; never sends or replays a task."""
import argparse
import json
from pathlib import Path
import re

from accept_office_files import ROOT, digest, read, rows
from dingtalk_bridge.message_model import materialize, media_parts, normalize
from dingtalk_bridge.routing import route_configs


def audit():
    private = ROOT / 'local/office-ui-20261111'
    fixtures = {'xlsx': ROOT / 'fixtures/dab-office-001.xlsx',
                'zip': ROOT / 'fixtures/dab-archive-001.zip'}
    markers = {'xlsx': ('DAB-XLSX-001', 'A1', 'B1'),
               'zip': ('dab-file-001.txt', 'DAB-FILE-001', '中文 round-trip check.')}
    report = {'date': '2026-11-11',
              'scope': 'Eight XLSX/ZIP directions, client originals and two actual direct tasks; UI observed separately',
              'fixtures': {k: {'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())}
                           for k, p in fixtures.items()}, 'cases': []}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        route = cfg['conversationType']
        cache = ROOT / 'local/runtime/routes' / state
        events = {r['message_id']: json.loads(r['body']) for r in
                  rows(cache / 'bridge.sqlite3', 'SELECT message_id,body FROM events')}
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], route]).encode())[:24]
        db = ROOT / 'local/agents' / key / 'tasks.sqlite3'
        jobs, outbox = rows(db, 'SELECT * FROM jobs'), rows(db, 'SELECT * FROM outbox')
        for kind, fixture in fixtures.items():
            original = fixture.read_bytes()
            for direction in ('in', 'out'):
                case = f'{route}-{kind}-{direction}'
                saved = read(private / (case + '-ledger.json'))
                event, ledger = saved['event'], saved['ledger']
                model = materialize(normalize(event, cfg), ledger, ROOT, cache / 'downloads')
                checks = {
                    'committed_event_matches': events.get(event['message_id']) == event,
                    'correct_direction': event['from_self'] is (direction == 'out'),
                    'one_resource': len(ledger['downloads']) == 1,
                    'downloaded_original_intact': bool(ledger['downloads']) and all(
                        (ROOT / p['localPath']).read_bytes() == original for p in ledger['downloads']),
                    'one_file_without_issues': not model['issues'] and len(list(media_parts(model))) == 1,
                }
                matched = [j for j in jobs if json.loads(j['model'])['id'] == event['message_id']]
                if direction == 'out':
                    receipt = read(ROOT / 'local/probes/media-matrix-20261111' / f'{route}-{kind}.json')['receipt']
                    checks['durable_send_confirmed'] = receipt['state'] == 'confirmed' and receipt['message_id'] == event['message_id']
                    client = private / (f'{route}-received.xlsx' if kind == 'xlsx' else f'{route}-zip/{route}-received.zip')
                    checks['client_download_intact'] = client.exists() and client.read_bytes() == original
                    checks['own_message_did_not_execute'] = not matched
                    if kind == 'zip':
                        extracted = private / f'{route}-zip/dab-file-001.txt'
                        checks['client_extracted_content_intact'] = extracted.exists() and extracted.read_bytes() == (ROOT / 'fixtures/dab-file-001.txt').read_bytes()
                elif route == 'group':
                    checks['unprefixed_file_did_not_execute'] = not matched
                else:
                    checks['one_actual_task'] = len(matched) == 1
                    if len(matched) == 1:
                        task = matched[0]
                        result = json.loads(task['result'] or '{}')
                        checks['completed_with_file_content'] = task['state'] == 'completed' and all(
                            marker in result.get('response', {}).get('text', '') for marker in markers[kind])
                        if kind == 'xlsx':
                            checks['numeric_cell_correct'] = bool(re.search(r'B1\s*[=:：]\s*1(?!\d)', result.get('response', {}).get('text', '')))
                        replies = [o for o in outbox if o['job_id'] == task['id']]
                        checks['ack_answer_and_file_confirmed'] = len(replies) == 3 and all(o['state'] == 'confirmed' for o in replies)
                        checks['replies_from_bound_account'] = bool(replies) and all(
                            (e := events.get(json.loads(o['receipt'] or '{}').get('message_id'))) and e['from_self'] and e['sender_id'] == cfg['selfSenderId'] for o in replies)
                        artifacts = result.get('artifacts', [])
                        checks['one_result_file'] = len(artifacts) == 1
                        if len(artifacts) == 1:
                            artifact = artifacts[0]
                            client = private / Path(artifact['file']).name
                            checks['result_client_download_intact'] = client.exists() and digest(client.read_bytes()) == artifact['sha256'] == digest((ROOT / artifact['file']).read_bytes())
                            checks['result_file_content_correct'] = client.exists() and all(marker in client.read_text() for marker in markers[kind])
                            if kind == 'xlsx':
                                checks['result_numeric_cell_correct'] = client.exists() and bool(re.search(r'B1:\s*1\s*$', client.read_text(), re.M))
                            else:
                                checks['result_contains_entire_archive_text'] = client.exists() and (ROOT / 'fixtures/dab-file-001.txt').read_text() in client.read_text()
                report['cases'].append({'case': case, 'checks': checks})
    expected = {f'{route}-{kind}-{direction}' for route in ('group', 'direct')
                for kind in fixtures for direction in ('in', 'out')}
    report['exact_case_coverage'] = len(report['cases']) == 8 and {r['case'] for r in report['cases']} == expected
    report['ok'] = report['exact_case_coverage'] and all(all(r['checks'].values()) for r in report['cases'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/xlsx-zip-ui-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()

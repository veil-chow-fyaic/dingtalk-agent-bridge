#!/usr/bin/env python3
"""Read-only supplement for the original E001 CSV. Never sends or replays tasks."""
import argparse
import csv
import io
import json

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/csv-client-open-20261112'
    case = read(folder / 'case.json')
    before = read(ROOT / 'local/stream-network-20261112/final.json')
    after = read(folder / 'after-ui.json')
    artifact = case['artifact']
    downloaded = (folder / '0-dab-ui-input-summary.csv').read_bytes()
    checks = {
        'original_job_completed': case['job']['state'] == 'completed',
        'original_artifact_still_matches': digest((ROOT / artifact['file']).read_bytes()) == artifact['sha256'],
        'client_download_matches_original': digest(downloaded) == artifact['sha256'],
        'client_download_79_bytes': len(downloaded) == 79,
        'csv_cells_match_expected': list(csv.reader(io.StringIO(downloaded.decode()))) == [
            ['item', 'quantity', 'unit_price', 'subtotal'],
            ['DAB-UI-INPUT-004', '3', '12', '36'], ['B', '2', '9', '18'], ['TOTAL', '', '', '54']],
    }
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key / 'tasks.sqlite3'
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent, 'id'), ('outbox', agent, 'key'), ('deliveries', transport, 'key')]:
            old = before['routes'][kind][table]
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_unchanged_during_ui'] = bool(old) and old == after['routes'][kind][table]
            checks[kind + '_' + table + '_still_preserved'] = all(current.get(r[identity]) == r for r in old)
        if kind == 'direct':
            checks['original_job_still_preserved'] = any(r == case['job'] for r in rows(agent, 'jobs'))
    search = (folder / 'search-result.ax.txt').read_text()
    card = (folder / 'chat-card.ax.txt').read_text()
    opened = (folder / 'opened.ax.txt').read_text()
    checks['original_file_found_in_chat_files'] = '0-dab-ui-input-summary.csv' in search and '79B' in search
    checks['original_chat_card_downloadable'] = '下载 编辑 0-dab-ui-input-summary.csv 79 B' in card
    checks['quick_look_table_content_recorded'] = all(x in opened for x in (
        '快速查看', '表格', 'DAB-UI-INPUT-004', 'subtotal', 'TOTAL', ' 36', ' 18', ' 54'))
    observation = read(folder / 'ui-observation.json')
    checks['reviewed_screenshot_preserved'] = observation['reviewed'] is True and digest((folder / 'opened.png').read_bytes()) == observation['sha256']
    return {'date': '2026-11-12', 'checks': checks, 'bytes': len(downloaded), 'sha256': digest(downloaded),
            'newMessagesSent': 0, 'newRuntimeTasks': 0,
            'scope': 'E001 direct outbound CSV downloaded from original native chat and opened in Finder Quick Look; UI observation recorded separately',
            'limits': ['No new group CSV evidence', 'No spreadsheet editing/formula or large-file coverage'],
            'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/csv-client-open-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

#!/usr/bin/env python3
"""Read-only native UI supplement for the two existing E018 long replies."""
import argparse
import json
import re

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def extract_bubble(ax):
    match = re.search(r'\d+ 文本输入区 (\[Agent\][\s\S]*?)(?=\n\t+\d+ )', ax)
    return match[1] if match else None


def audit():
    folder = ROOT / 'local/quote-ui-20261112'
    case = read(ROOT / 'local/long-text-ui-20261111/postfix/case.json')
    before = read(ROOT / 'local/office-agent-20261111/final-ledgers.json')
    end = read(folder / 'after-ui-ledgers.json')
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key / 'tasks.sqlite3'
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent, 'id'), ('outbox', agent, 'key'),
                                    ('deliveries', transport, 'key')]:
            old = before['routes'][kind][table]
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_unchanged_during_ui'] = bool(old) and end['routes'][kind][table] == old
            checks[kind + '_' + table + '_still_preserved'] = all(current.get(r[identity]) == r for r in old)
    lengths = []
    for name, file in [('first', '04-long-first.full.ax.txt'), ('second', '06-long-second.full.ax.txt')]:
        ax = (folder / file).read_text()
        body = extract_bubble(ax)
        matches = [r for r in case['replyEvents'] if r['content'] == body]
        checks[name + '_native_chat_not_search_summary'] = '标准窗口 钉钉' in ax and 'text liev(' in ax and 'searchMore' not in ax
        checks[name + '_full_bubble_matches_one_original_reply'] = bool(body) and len(matches) == 1
        lengths.append(len(body or ''))
        if name == 'first':
            checks['first_contains_statistics_and_two_copy_sections'] = bool(body) and all(t in body for t in ('统计信息', '第一份', '第二份', '行060'))
            checks['first_ends_at_second_copy_line025'] = bool(body) and body.splitlines()[-1].startswith('行025｜')
        else:
            checks['second_starts_line026_ends_line060'] = bool(body) and body.startswith('[Agent] 行026｜') and body.splitlines()[-1].startswith('行060｜')
    observation = read(folder / 'observations.json')
    required = {'04-long-first.png', '06-long-second.png', '07-select-end.png',
                '08-second-start.png', '09-first-start.png', '10-copy-boundary.png', '11-first-end.png'}
    checks['all_required_viewports_reviewed'] = set(observation['frames']) == required
    checks['reviewed_screenshots_unchanged'] = all(
        (folder / f).is_file() and (folder / f).stat().st_size > 10000 and
        digest((folder / f).read_bytes()) == row['sha256'] and row['observed']
        for f, row in observation['frames'].items())
    checks['quote_not_claimed_as_passed'] = observation['quotePassed'] is False
    return {'date': '2026-11-12', 'checks': checks, 'nativeBubbleCharacters': lengths,
            'newMessagesSent': 0, 'newRuntimeTasks': 0,
            'scope': 'Complete text from native chat AX, plus reviewed start/boundary/end viewports; not every line separately screenshot-tested',
            'limits': ['Quote menu not opened; no native quote task sent',
                       'Original first-chunk trailing LF removal remains documented in E018',
                       'Built-in AI search summary is not evidence of delivered message content'],
            'ok': all(checks.values())}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-evidence', action='store_true')
    args = p.parse_args(); report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/long-bubble-ui-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

#!/usr/bin/env python3
"""Read-only documentation inventory and historical-body review; no live probes.

The catalog records lifecycle, not truth of every sentence. Handoff validation
separately checks local links/JSON/full-file digests. Never calls DWS or a model.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from review_acceptance import load_review

ROOT = Path(__file__).resolve().parents[1]
INDEX = 'docs/documentation-index.json'
START = '<!-- historical-scope:start -->'
END = '<!-- historical-scope:end -->'
ROLES = {'current', 'reference', 'historical', 'baseline', 'ledger', 'archive', 'fixture'}
LABELS = {'current': '现行说明', 'reference': '固定来源/采用说明',
          'historical': '阶段历史', 'baseline': '验收基线', 'ledger': '累计账本',
          'archive': '冻结归档', 'fixture': '合成素材说明'}


def documents(root):
    paths = [root / 'README.md', root / 'AGENTS.md']
    for folder in ('docs', 'plans', 'evidence', 'integrations', 'fixtures', 'tests', 'api'):
        paths.extend((root / folder).rglob('*.md'))
    return sorted(str(p.relative_to(root)) for p in paths if p.is_file())


def historical_banner(path):
    # All currently registered stage reports live at docs/ or docs/references/.
    prefix = '../' if Path(path).parent == Path('docs/references') else ''
    return (START + '\n> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；'
            '“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。'
            f'现状见[统一总览]({prefix}102-user-requirements-and-roadmap.md)，'
            f'操作见[运行手册]({prefix}15-service-runbook.md)。'
            '旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。\n' + END + '\n\n')


def original_body(path, text):
    heading, rest = text.split('\n', 1)
    banner = '\n' + historical_banner(path)
    if not rest.startswith(banner) or text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('missing or changed historical scope banner')
    return heading + '\n' + rest[len(banner):]


def render_index(index):
    lines = ['# 全部文档索引', '',
             '逐文件范围由[索引数据](documentation-index.json)维护；当前结论见'
             '[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。', '',
             '阶段历史只增加范围提示，原正文摘要受保护；冻结归档、原PRD/矩阵/最终自检保持原样。'
             '累计账本只追加新轮次，不执行旧行的“下一步”。合成素材不是用户文档或真实业务证据。', '',
             '| 文档 | 范围 |', '|---|---|']
    for name, entry in sorted(index['documents'].items()):
        target = name[5:] if name.startswith('docs/') else '../' + name
        lines.append(f'| [{name}]({target}) | {LABELS[entry["role"]]} |')
    return '\n'.join(lines) + '\n'


def review(root, index=None):
    errors = []
    if index is None:
        index = json.loads((root / INDEX).read_text())
    entries = index['documents']
    actual = set(documents(root))
    if actual != set(entries):
        errors.append({'check': 'inventory', 'missing': sorted(actual - set(entries)),
                       'extra': sorted(set(entries) - actual)})
    for name, entry in entries.items():
        role = entry.get('role')
        if role not in ROLES:
            errors.append({'check': 'role', 'path': name})
            continue
        if name not in actual:
            continue
        data = (root / name).read_bytes()
        text = data.decode('utf-8')
        if role == 'historical':
            try:
                data = original_body(name, text).encode('utf-8')
            except ValueError:
                errors.append({'check': 'scope_banner', 'path': name})
                continue
        if role in {'historical', 'baseline', 'archive', 'fixture'}:
            if hashlib.sha256(data).hexdigest() != entry.get('preservedSha256'):
                errors.append({'check': 'preserved_body', 'path': name})
        if role == 'ledger':
            length = entry['preservedPrefixBytes']
            if hashlib.sha256(data[:length]).hexdigest() != entry['preservedSha256']:
                errors.append({'check': 'ledger_prefix', 'path': name})
    if (root / 'docs/INDEX.md').read_text() != render_index(index):
        errors.append({'check': 'rendered_index'})
    coverage = load_review(root)
    if not coverage['valid']:
        errors.append({'check': 'invalid_acceptance'})
    state = index['state']
    if coverage['uiStateCounts'] != state['uiStateCounts']:
        errors.append({'check': 'coverage_counts'})
    if sorted(g['id'] for g in coverage['mustGaps']) != state['mustGaps']:
        errors.append({'check': 'must_gaps'})
    overview = (root / 'docs/102-user-requirements-and-roadmap.md').read_text()
    counts = state['uiStateCounts']
    required = [state[k] for k in ('documentationEvidence', 'latestUiEvidence',
                'deployedProduct', 'deploymentEvidence', 'candidateProduct')]
    required += [f'{counts["passed"]}通过、{counts["blocked"]}阻塞、{counts["partial"]}部分',
                 '/'.join(state['mustGaps'])]
    if any(value not in overview for value in required):
        errors.append({'check': 'overview_state'})
    return {'ok': not errors, 'scope': 'Offline documentation only; no product/UI/health certification',
            'documents': len(actual), 'roles': dict(sorted(Counter(e['role'] for e in entries.values()).items())),
            'uiStateCounts': coverage['uiStateCounts'], 'mustGaps': state['mustGaps'], 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = review(args.root.resolve())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {'ok': False, 'errors': [{'check': 'invalid_input', 'type': type(exc).__name__}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

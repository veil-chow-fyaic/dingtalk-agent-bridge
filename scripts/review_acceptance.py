#!/usr/bin/env python3
"""Read declared acceptance coverage only; never call DWS or certify completion."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = {f'R{i:02}': 'MUST' if i <= 14 else 'SHOULD' for i in range(1, 18)}
DIRECTIONS = ('群 veil→liev', '群 liev→veil', '私聊 veil→liev', '私聊 liev→veil')
TYPES = ('普通文字/任务', '长文/换行/中文/emoji', 'TXT原件', 'CSV原件', 'PDF原件',
         'DOCX原件', 'XLSX原件', 'ZIP原件', 'PNG内容/原件', 'JPEG内容/原件',
         'WAV作为文件', 'MP4作为文件', '原生语音条', '独立video协议', '引用/回复关系', '单消息多附件')
STATES = {'通过': 'passed', '部分': 'partial', '未完成': 'open', '阻塞': 'blocked'}
EVIDENCE_ID = r'(?<![A-Za-z0-9])E\d{3}(?![A-Za-z0-9])'


def cells(line):
    return [part.strip() for part in line.strip().strip('|').split('|')]


def table(document, heading):
    lines = document.splitlines()
    headers = [i for i, line in enumerate(lines) if line.strip() == heading]
    if len(headers) != 1:
        raise ValueError(f'Expected one table heading: {heading}')
    result = []
    for line in lines[headers[0] + 1:]:
        if not line.strip().startswith('|'):
            break
        row = cells(line)
        if all(re.fullmatch(r':?-+:?', item) for item in row):
            continue
        result.append(row)
    if not result:
        raise ValueError(f'Empty table: {heading}')
    return result


def evidence_ids(document):
    result = set()
    for line in document.splitlines():
        if line.startswith('| E'):
            result.update(re.findall(EVIDENCE_ID, cells(line)[0]))
        elif re.match(r'^## E\d{3}', line):
            # Combined E070/E071 headings are both declared evidence entries.
            prefix = re.match(r'^## (E\d{3}(?:/E\d{3})*)', line).group(1)
            result.update(re.findall(r'E\d{3}', prefix))
    return result


def review(prd, matrix, evidence):
    definitions = {}
    for row in table(prd, '| ID | 级别 | 真实需求与判据 | 当前证据/缺口 |'):
        if len(row) != 4 or row[0] in definitions:
            raise ValueError('Malformed or duplicate PRD requirement')
        definitions[row[0]] = row
    if {key: row[1] for key, row in definitions.items()} != REQUIREMENTS:
        raise ValueError('Requirement IDs or MUST/SHOULD levels differ from this mission')
    if any(not row[2] for row in definitions.values()):
        raise ValueError('Missing acceptance criterion')

    registered = evidence_ids(evidence)

    def references(text, required=False):
        refs = sorted(set(re.findall(EVIDENCE_ID, text)))
        if required and not refs:
            raise ValueError('Passed UI cell needs an evidence ID')
        if any(ref not in registered for ref in refs):
            raise ValueError('Unknown evidence ID in acceptance table')
        return refs

    requirements = {}
    for row in table(matrix, '| PRD | 当前判定 | 可复核证据 / 仍需完成 |'):
        if len(row) != 3 or not re.match(r'^R\d{2}\s', row[0]):
            raise ValueError('Malformed MUST assessment')
        key = row[0].split()[0]
        if key in requirements or row[1] not in STATES or not row[2]:
            raise ValueError('Duplicate, unrecognized or empty MUST assessment')
        requirements[key] = {'id': key, 'state': STATES[row[1]], 'detail': row[2],
                             'evidenceIds': references(row[2])}
    if set(requirements) != {key for key, level in REQUIREMENTS.items() if level == 'MUST'}:
        raise ValueError('MUST assessment rows are missing or unexpected')

    ui = []
    types = set()
    header = '| 类型 | ' + ' | '.join(DIRECTIONS) + ' |'
    for row in table(matrix, header):
        if len(row) != 5 or row[0] in types or row[0] not in TYPES:
            raise ValueError('Malformed, duplicate or unexpected UI type')
        types.add(row[0])
        for direction, value in zip(DIRECTIONS, row[1:]):
            # Partial comes first: neither 部分通过 nor 部分/blocked is a pass.
            if value.startswith(('部分通过 ', '部分/blocked：')):
                state = 'partial'
            elif value.startswith('blocked：'):
                state = 'blocked'
            elif value.startswith('通过 '):
                state = 'passed'
            else:
                raise ValueError('Unknown UI state; refusing to infer a pass')
            ui.append({'type': row[0], 'direction': direction, 'state': state,
                       'detail': value, 'evidenceIds': references(value, required=state == 'passed')})
    if types != set(TYPES):
        raise ValueError('UI rows are missing')

    gaps = [item for item in ui if item['state'] != 'passed']
    must_gaps = [item for item in requirements.values() if item['state'] != 'passed']
    return {
        'schemaVersion': 1, 'valid': True,
        'scope': 'Declared document coverage only; no raw UI verification, current health or final approval',
        'allDeclaredCovered': not gaps and not must_gaps,
        'requirementCounts': {'MUST': 14, 'SHOULD': 3},
        'mustStateCounts': dict(Counter(item['state'] for item in requirements.values())),
        'uiStateCounts': dict(Counter(item['state'] for item in ui)),
        'byDirection': {direction: dict(Counter(item['state'] for item in ui if item['direction'] == direction)) for direction in DIRECTIONS},
        'mustGaps': must_gaps, 'uiGaps': gaps,
        'requirements': list(requirements.values()), 'uiCells': ui,
        'criterionSha256': {key: hashlib.sha256(json.dumps(row[:3], ensure_ascii=False).encode()).hexdigest() for key, row in definitions.items()},
        'notAssessed': ['Private UI evidence contents and artifact hashes', 'Current DWS authentication and deployment',
                        'Real 24-hour observation and error disposition', 'Final release/privacy/rollback review'],
        'limits': ['Historical passes retain their original versions and scope; outages do not erase them',
                   'Unverified or blocked platform types stay gaps; this tool does not waive a MUST',
                   'Registered evidence IDs prove an index entry exists, not that its claim is true',
                   'All declared cells covered would still require independent final review'],
    }


def load_review(root):
    folder = Path(root) / 'plans/completion'
    sources = {name: (folder / name).read_bytes() for name in ('01-PRD.md', 'ACCEPTANCE_MATRIX.md', 'EVIDENCE.md')}
    result = review(*(sources[name].decode() for name in sources))
    result['sourceSha256'] = {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--require-covered', action='store_true')
    args = parser.parse_args()
    try:
        report = load_review(args.root)
    except (OSError, ValueError) as exc:
        print(json.dumps({'valid': False, 'errorType': type(exc).__name__, 'allDeclaredCovered': False}))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.require_covered and not report['allDeclaredCovered'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

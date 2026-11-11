#!/usr/bin/env python3
"""Read-only audit of the distinct DWS native-image direct experiment."""
import argparse
import json

from accept_office_files import ROOT, digest, read, rows
from dingtalk_bridge.routing import route_configs


def audit():
    directory = ROOT / 'local/native-png-20261111'
    intent, preview, status = (read(directory / f'direct-{name}.json')
                               for name in ('intent', 'preview', 'status'))
    matches = [(cfg, state) for cfg, state in route_configs(read(ROOT / 'local/service-config.json'))
               if cfg['conversationType'] == 'direct']
    assert len(matches) == 1
    cfg, state = matches[0]
    events = [json.loads(row['body']) for row in rows(
        ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3', 'SELECT body FROM events')]
    matching = [e for e in events if e['message_id'] == status['messageRef']['openMessageId']]
    key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], 'direct']).encode())[:24]
    jobs = rows(ROOT / 'local/agents' / key / 'tasks.sqlite3', 'SELECT model FROM jobs')
    original = (ROOT / 'fixtures/dab-image-001.png').read_bytes()
    received = directory / 'direct-received.png'
    checks = {
        'original_markdown_send_already_confirmed': read(ROOT / 'local/probes/media-matrix-20261111/direct-png.json')['receipt']['state'] == 'confirmed',
        'same_bound_profile': intent['profile'] == cfg['profile'],
        'preview_is_native_image': len(preview['actions']) == 1 and preview['actions'][0]['arguments']['msgType'] == 'image',
        'native_send_success': status['success'] is True and status['result']['sendStatus'] == 'SUCCESS',
        'exact_target': status['messageRef']['openConversationId'] == cfg['group'],
        'one_committed_native_event': len(matching) == 1,
        'bound_account_sent': len(matching) == 1 and matching[0]['from_self'] is True and matching[0]['sender_id'] == cfg['selfSenderId'],
        'no_self_task': not any(json.loads(j['model'])['id'] == status['messageRef']['openMessageId'] for j in jobs),
        'client_download_original_intact': received.exists() and received.read_bytes() == original,
    }
    return {'date': '2026-11-11', 'scope': 'Official DWS native image, direct chat only; bridge integration pending; UI separate',
            'fixture': {'bytes': len(original), 'sha256': digest(original)}, 'checks': checks, 'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/native-image-direct-ledger.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

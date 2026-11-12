#!/usr/bin/env python3
"""Read-only E056 review of frozen, credential-free official DWS dry-run plans."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from probe_dws_send_contract import cases, validate_case


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'local/send-contract-20261112'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def negatives(report):
    saved = {r['name']: r for r in report['cases']}
    checks = {}
    def refuse(name, case, mutate):
        result = copy.deepcopy(saved[case])
        mutate(result)
        expected = next(e for n, _, e in cases() if n == case)
        checks[name] = not validate_case(result, expected)
    refuse('executed_true', 'one_file', lambda r: r['data'].update(executed=True))
    refuse('dry_run_missing', 'one_file', lambda r: r['data'].pop('dry_run'))
    refuse('first_file_not_last', 'repeat_file_last_b', lambda r: r['data']['actions'][0]['file'].update(name='a.txt'))
    refuse('extra_send_action', 'one_file', lambda r: r['data']['actions'].append(copy.deepcopy(r['data']['actions'][1])))
    refuse('audio_not_file', 'audio_maps_to_file', lambda r: r['data']['actions'][1].update(effectiveMessageType='audio'))
    refuse('wrong_image_count', 'nine_local_images', lambda r: r['data'].update(imageCount=3))
    refuse('wrong_unique_paths', 'nine_repeated_image_refs', lambda r: r['data'].update(uniquePathCount=9))
    refuse('auth_failure_not_input_limit', 'ten_local_images', lambda r: r['data']['error'].update(category='auth'))
    refuse('network_failure_not_input_limit', 'ten_local_images', lambda r: r['data']['error'].update(message='proxyconnect tcp: connection refused'))
    return checks


def audit():
    report = read(FOLDER / 'probe.json')
    initial = read(FOLDER / 'probe-initial.json')
    before, after = (read(FOLDER / n) for n in ('before.json', 'after.json'))
    environment = read(FOLDER / 'environment.json')
    sources = read(FOLDER / 'source-hashes.json')
    checks = {'pinned_version': report['version'] == '1.0.67',
              'pinned_binary_unchanged': report['binarySha256'] == sha(ROOT / 'local/bin/v1.0.67/dws'),
              'complete_18_cases': len(report['cases']) == report['caseCount'] == len(cases()) == 18,
              'initial_five_category_assumptions_retained': sum(not c['ok'] for c in initial['cases']) == 5,
              'service_config_exact_and_official_context': environment['configExactAndOfficialContext'],
              'same_three_managed_processes_healthy': environment['sameManagedProcesses'] and environment['allRunning'],
              'product_code_still_e054': environment['codeUnchanged'],
              'original_observer_continues': before['observer']['pid'] == after['observer']['pid'] == 97881
                  and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
              'transport_poll_healthy': not after['health']['poll_error']}
    for actual, (name, tail, expected) in zip(report['cases'], cases()):
        argv = ['chat', '+messages-send', '--as', 'user', '--group', 'synthetic-offline-target',
                '--dry-run', '--format', 'json', *tail]
        checks['cli_' + name] = (actual['name'] == name and actual['argv'] == argv
                                and actual['expected'] == expected and validate_case(actual, expected))
    for name, digest in sources.items():
        checks['source_' + Path(name).name] = digest == sha(ROOT / 'local/research-v67/source' / name)
    for kind in ('direct', 'group'):
        for name in ('jobs', 'outbox', 'deliveries', 'events', 'meta', 'runtimeFiles'):
            checks[kind + '_' + name + '_unchanged'] = before['routes'][kind][name] == after['routes'][kind][name]
    negative = negatives(report)
    return {'date': '2026-11-12', 'evidence': 'E056', 'ok': all(checks.values()) and all(negative.values()),
            'checks': checks, 'negativeChecks': negative, 'officialCliDryRunCases': 18,
            'newMessages': 0, 'newNativeUICapabilityVerified': False, 'productChanged': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'sources': {name: {'sha256': digest, 'url': 'https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/' + name}
                        for name, digest in sources.items()},
            'artifactsSha256': {n: sha(FOLDER / n) for n in ('probe.json', 'probe-initial.json', 'probe.log', 'probe-initial.log')},
            'limits': report['limits']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/send-contract-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

#!/usr/bin/env python3
"""Read-only E058: first-download integrity, HTTP recovery and frozen deployment."""
import argparse
import json
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from accept_media_slot import passed
from dingtalk_bridge.routing import route_configs
from frozen_install import frozen_install_matches


def audit():
    folder = ROOT / 'local/fresh-download-20261112'
    before, after = (read(folder / n) for n in ('before.json', 'after-load.json'))
    install = read(ROOT / 'evidence/2026-11-12/fresh-download-install.json')
    old_source, old_wheel = ((folder / n).read_text() for n in ('before-fix.log', 'old-installed-wheel.log'))
    existing = read(folder / 'existing-caches.json')
    loaded = read(folder / 'manager-loaded.json')
    old_manager = {r['name']: r for r in read(folder / 'manager-before.json')['components']}
    checks = {
        'old_source_bad_responses_reproduced': 'Ran 3 tests' in old_source and old_source.rstrip().endswith('FAILED (failures=16, errors=10)'),
        'old_installed_wheel_and_http_bad_responses_reproduced': 'Ran 5 tests' in old_wheel and old_wheel.rstrip().endswith('FAILED (failures=18, errors=10)'),
        'fresh_cache_repair_http_and_consumer_tests': passed(folder, 'after-fix.log', 19),
        'source_python314_full_189': passed(folder, 'full-py314-final.log', 189),
        'installed_python314_full_189': passed(folder, 'installed-py314-tests.log', 189),
        'installed_python311_full_189': passed(folder, 'installed-py311-tests.log', 189),
        'frozen_wheel_and_install_match': frozen_install_matches(install, folder),
        'fifty_existing_caches_stay_valid_without_network_or_writes': existing['allAcceptedUnchanged'] and existing['networkCalls'] == 0
            and len(existing['caches']) == 50 and sum(r['resourceCount'] for r in existing['caches']) == 57 and all(
                digest((ROOT / r['manifest']).read_bytes()) == r['sha256'] for r in existing['caches']),
        'doctor_live_passed': read(folder / 'doctor.json')['ok'],
        'all_three_components_reloaded': loaded['status']['all_running'] and len(loaded['state']['components']) == 3 and all(
            old_manager[r['name']]['pid'] != r['pid'] for r in loaded['state']['components']),
        'loaded_source_matches_install': loaded['codeSha256'] == install['codeSha256'],
        'config_bytes_preserved': loaded['configsUnchanged'],
        'original_observer_preserved': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'transport_healthy_after_reload': not after['health']['poll_error'],
    }
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType'];old, new = before['routes'][kind], after['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key; transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key'), ('events', transport, 'seq')]:
            live = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = old[table] == new[table] and all(live.get(r[identity]) == r for r in old[table])
        checks[kind + '_session_and_logs_preserved'] = old['meta'] == new['meta'] and old['runtimeFiles'] == new['runtimeFiles'] and all(
            (ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
    return {'date': '2026-11-12', 'evidence': 'E058', 'ok': all(checks.values()), 'checks': checks,
            'fullTestCount': 189, 'newRegressionMethods': 5, 'invalidFreshVariants': 22,
            'partialOrMissingVariants': 3, 'invalidCacheVariants': 4, 'newNativeUITest': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'unavailableSamples': after['observer']['unavailable_samples'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in ('before-fix.log', 'old-installed-wheel.log',
                'after-fix.log', 'full-py314-final.log', 'installed-py314-tests.log', 'installed-py311-tests.log')},
            'limits': ['Synthetic provider responses and real local HTTP/CLI processes; no credential failure or new DingTalk UI test',
                       '50 existing manifests/57 resources read without network, repairs or writes',
                       'Resource ledger must cover required observed references; additional well-formed resources are not excluded',
                       'Failed repair validation preserves the old manifest; crash/power-loss during manifest replacement is separate',
                       'Historical manager failures and incomplete 24h remain']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/fresh-download-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

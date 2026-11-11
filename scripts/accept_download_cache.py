#!/usr/bin/env python3
"""Read-only E054 cache integrity and deployment audit; never repairs or sends."""
import argparse
import json
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from accept_message_shape import passed_log
from dingtalk_bridge.routing import route_configs
from frozen_install import frozen_install_matches


def audit():
    folder = ROOT / 'local/download-cache-20261112'
    before, after = (read(folder / n) for n in ('before.json', 'after-load.json'))
    install = read(ROOT / 'evidence/2026-11-12/download-cache-install.json')
    old_log = (folder / 'before-fix.log').read_text()
    existing = read(folder / 'existing-caches.json')
    checks = {
        'old_six_corrupt_manifests_reproduced': 'Ran 1 test' in old_log and old_log.rstrip().endswith('FAILED (failures=6)'),
        'six_corrupt_cases_refused_and_explicit_repair_verified': passed_log(folder, 'after-fix.log', 1),
        'source_python314_full_180': passed_log(folder, 'full-py314.log', 180),
        'installed_python314_full_180': passed_log(folder, 'installed-py314-tests.log', 180),
        'installed_python311_full_180': passed_log(folder, 'installed-py311-tests.log', 180),
        'frozen_wheel_and_install_match': frozen_install_matches(install, folder),
        'existing_caches_verified_without_network_or_changes': existing['allAcceptedUnchanged'] and existing['networkCalls'] == 0 and len(existing['caches']) == 48 and all(
            digest((ROOT / row['manifest']).read_bytes()) == row['sha256'] for row in existing['caches']),
        'doctor_live_passed': read(folder / 'doctor.json')['ok'],
    }
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        old, new = before['routes'][kind], after['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'),
                                    ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key'), ('events', transport, 'seq')]:
            live = {row[identity]: row for row in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = old[table] == new[table] and all(
                live.get(row[identity]) == row for row in old[table])
        checks[kind + '_session_and_logs_preserved'] = old['meta'] == new['meta'] and old['runtimeFiles'] == new['runtimeFiles'] and all(
            (ROOT / path).is_file() and digest((ROOT / path).read_bytes()) == sha for path, sha in old['runtimeFiles'].items())
    loaded = read(folder / 'manager-loaded.json')
    old_manager = {r['name']: r for r in read(folder / 'manager-before.json')['components']}
    checks['all_components_reloaded_and_running'] = loaded['status']['all_running'] and all(
        old_manager[r['name']]['pid'] != r['pid'] for r in loaded['state']['components'])
    checks['loaded_source_matches_tested_install'] = loaded['codeSha256'] == install['codeSha256']
    checks['config_bytes_preserved'] = loaded['configsUnchanged']
    checks['original_observer_preserved'] = before['observer']['pid'] == after['observer']['pid'] == 97881 and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active']
    return {'date': '2026-11-12', 'evidence': 'E054', 'ok': all(checks.values()), 'checks': checks,
            'newTestMethods': 1, 'corruptManifestVariants': 6, 'fullTestCount': 180,
            'existingCaches': 48, 'existingResources': sum(r['resourceCount'] for r in existing['caches']),
            'newNativeUITest': False,
            'limits': ['Corruption injected only into synthetic temporary caches',
                       '48 existing manifests and 55 resources checked locally without network or writes',
                       'No new platform download, message, native UI action or credential manipulation',
                       'Explicit repair verified only in synthetic fixtures; historical artifacts retained'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in
                          ('before-fix.log', 'after-fix.log', 'full-py314.log', 'installed-py314-tests.log', 'installed-py311-tests.log')}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/download-cache-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

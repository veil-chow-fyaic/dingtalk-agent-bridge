#!/usr/bin/env python3
"""Read-only E057 media completion scheduling and frozen deployment audit."""
import argparse
import json
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs
from frozen_install import frozen_install_matches


def passed(folder, name, count):
    value = (folder / name).read_text()
    return f'Ran {count} tests' in value and value.rstrip().endswith('OK')


def audit():
    folder = ROOT / 'local/media-slot-20261112'
    before, after = (read(folder / n) for n in ('before-load.json', 'after-load.json'))
    install = read(ROOT / 'evidence/2026-11-12/media-slot-install.json')
    old_source, old_wheel = ((folder / n).read_text() for n in ('before-fix.log', 'old-installed-wheel.log'))
    loaded = read(folder / 'manager-loaded.json')
    old_manager = {r['name']: r for r in read(folder / 'manager-before.json')['components']}
    new_manager = {r['name']: r for r in loaded['state']['components']}
    checks = {
        'old_source_two_failures_reproduced': 'Ran 3 tests' in old_source and old_source.rstrip().endswith('FAILED (failures=2)') and "['m1', 'm2', 'm1', 'm2', 'm1', 'm2']" in old_source,
        'old_installed_wheel_two_failures_reproduced': 'Ran 4 tests' in old_wheel and old_wheel.rstrip().endswith('FAILED (failures=2)'),
        'four_deterministic_scheduling_cancel_restart_tests': passed(folder, 'after-fix.log', 4),
        'source_python314_full_184': passed(folder, 'full-py314.log', 184),
        'installed_python314_full_184': passed(folder, 'installed-py314-tests.log', 184),
        'installed_python311_full_184': passed(folder, 'installed-py311-tests.log', 184),
        'frozen_wheel_and_install_match': frozen_install_matches(install, folder),
        'doctor_live_passed': read(folder / 'doctor.json')['ok'],
        'only_two_gateways_reloaded': loaded['status']['all_running'] and all(
            old_manager[n]['pid'] != new_manager[n]['pid'] for n in new_manager if n != 'transport'),
        'transport_identity_unchanged': old_manager['transport'] == new_manager['transport'],
        'loaded_source_matches_install': loaded['codeSha256'] == install['codeSha256'],
        'config_bytes_preserved': loaded['configsUnchanged'],
        'original_observer_preserved': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'transport_healthy_after_reload': not after['health']['poll_error'],
    }
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType'];old, new = before['routes'][kind], after['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key'), ('events', transport, 'seq')]:
            live = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = old[table] == new[table] and all(live.get(r[identity]) == r for r in old[table])
        checks[kind + '_session_and_logs_preserved'] = old['meta'] == new['meta'] and old['runtimeFiles'] == new['runtimeFiles'] and all(
            (ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
    return {'date': '2026-11-12', 'evidence': 'E057', 'ok': all(checks.values()), 'checks': checks,
            'fullTestCount': 184, 'newRegressionMethods': 4, 'newNativeUITest': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'unavailableSamples': after['observer']['unavailable_samples'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in ('invalid-fixture.log', 'before-fix.log',
                'old-installed-wheel.log', 'after-fix.log', 'full-py314.log', 'installed-py314-tests.log', 'installed-py311-tests.log')},
            'limits': ['Real local download threads with synthetic HTTP and runtime responses; no account data',
                       'Waiting-media restart can repeat read-only download, never the task or acknowledgement',
                       'A cancelled in-flight request retains the one-request bound until it finishes or times out',
                       'No new native UI, quoted-input UI or multi-file single-message acceptance',
                       'Historical manager shutdown errors and incomplete 24h remain']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args(); result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/media-slot-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

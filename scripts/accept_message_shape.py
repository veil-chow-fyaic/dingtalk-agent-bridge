#!/usr/bin/env python3
"""Read-only E053 audit: malformed input isolation, not inbound quote UI proof."""
import argparse
import importlib.util
import json
import re
from accept_office_files import ROOT, read, digest
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs
from frozen_install import frozen_install_matches


def load_model(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def passed_log(folder, name, count):
    text = (folder / name).read_text()
    found = re.search(r'Ran (\d+) tests? in', text)
    return bool(found and int(found[1]) == count and text.rstrip().endswith('OK'))


def audit():
    folder = ROOT / 'local/message-shape-20261112'
    prior_folder = ROOT / 'local/reconcile-race-20261112'
    before, after = (read(folder / name) for name in ('before.json', 'after-load.json'))
    prior = load_model(prior_folder / 'clean-source/dingtalk_bridge/message_model.py', 'e052_model')
    fixed = load_model(folder / 'clean-source/dingtalk_bridge/message_model.py', 'e053_model')
    install = read(ROOT / 'evidence/2026-11-12/message-shape-install.json')
    prior_install = read(ROOT / 'evidence/2026-11-12/reconcile-race-install.json')
    old_log = (folder / 'before-fix.log').read_text()
    checks = {
        'old_implementation_reproduces_shape_failures': 'Ran 2 tests' in old_log and
            old_log.rstrip().endswith('FAILED (failures=2, errors=15)'),
        'fixed_isolation_and_gateway_tests': passed_log(folder, 'after-fix.log', 2),
        'python314_full_179': passed_log(folder, 'full-py314.log', 179),
        'installed_python314_full_179': passed_log(folder, 'installed-py314-tests.log', 179),
        'installed_python311_full_179': passed_log(folder, 'installed-py311-tests.log', 179),
        'fixed_frozen_install': frozen_install_matches(install, folder),
        'prior_frozen_install': frozen_install_matches(prior_install, prior_folder),
        'doctor_live_passed': read(folder / 'doctor.json')['ok'],
    }
    projections = read(folder / 'projections.json')
    count = quotes = 0
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
        records = next(p['records'] for p in projections if p['kind'] == kind)
        events = [{**json.loads(row['body']), 'seq': row['seq']} for row in old['events']]
        checks[kind + '_all_frozen_events_project_identically'] = bool(events) and [r['event'] for r in records] == events and all(
            r['model'] == prior.normalize(r['event'], cfg) == fixed.normalize(r['event'], cfg) for r in records)
        count += len(records)
        quotes += sum(bool(r['model'].get('quote')) for r in records)
    manager_before = read(folder / 'manager-before.json')
    loaded = read(folder / 'manager-loaded.json')
    original = {r['name']: r for r in manager_before['components']}
    current = {r['name']: r for r in loaded['state']['components']}
    checks['transport_identity_preserved'] = original['transport'] == current['transport']
    checks['agents_reloaded_and_running'] = loaded['status']['all_running'] and all(
        original[n]['pid'] != current[n]['pid'] for n in ('agent-1', 'agent-2'))
    checks['loaded_source_matches_tested_install'] = loaded['codeSha256'] == install['codeSha256']
    checks['config_bytes_preserved'] = loaded['configsUnchanged']
    checks['original_observer_preserved'] = before['observer']['pid'] == after['observer']['pid'] == 97881 and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active']
    return {'date': '2026-11-12', 'evidence': 'E053', 'ok': all(checks.values()), 'checks': checks,
            'malformedShapes': 18, 'newTestMethods': 2, 'fullTestCount': 179,
            'existingOfficialEventsReplayed': count, 'existingQuoteSamples': quotes,
            'newNativeUITest': False,
            'limits': ['Synthetic malformed payloads only; no claim these shapes occurred on DingTalk',
                       'Existing official events replayed offline, not new incoming quote UI acceptance',
                       'Quarantined payloads are retained locally and never execute; following authorized messages proceed',
                       'Transport, original observation run and all historical records retained'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in
                          ('before-fix.log', 'after-fix.log', 'full-py314.log', 'installed-py314-tests.log', 'installed-py311-tests.log')}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/message-shape-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

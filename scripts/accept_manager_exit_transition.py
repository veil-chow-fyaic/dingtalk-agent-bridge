#!/usr/bin/env python3
"""Read-only E062: captured exiting transition, strict signal boundary, installation."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, read, digest
from frozen_install import frozen_install_matches, module_sources_match


def audit():
    folder = ROOT / 'local/manager-exit-20261112'
    before, after = (read(folder / n) for n in ('before-tests.json', 'after-tests.json'))
    install = read(ROOT / 'evidence/2026-11-12/manager-exit-install.json')
    old_install = read(ROOT / 'evidence/2026-11-12/atomic-manifest-install.json')
    replay = read(folder / 'captured-replay.json')
    checks = {
        'old_source_two_regressions_reproduced': (folder / 'before-fix.log').read_text().rstrip().endswith('FAILED (failures=2)'),
        'old_installed_two_regressions_reproduced': (folder / 'old-installed-regression.log').read_text().rstrip().endswith('FAILED (failures=2)'),
        'new_transition_and_refusal_boundary_passed': 'Ran 2 tests' in (folder / 'after-fix.log').read_text()
            and (folder / 'after-fix.log').read_text().rstrip().endswith('OK'),
        'captured_exact_transition_old_refuses_new_waits_for_absence': replay['old']['outcome'] == 'refused'
            and replay['old']['psCalls'] == 3 and replay['new']['outcome'] == 'stopped' and replay['new']['psCalls'] == 4
            and all(r['signals'] == 1 and r['onlyTerm'] for r in replay.values()),
        'local_system_manual_confirms_E_exit_state': 'The process is trying to exit.' in (folder / 'ps-man.txt').read_text(),
        'original_py311_full_suite_failure_preserved': 'FAILED (errors=1)' in (ROOT / 'local/route-process-20261112/py311-tests.log').read_text(),
        'frozen_wheel_install_and_current_source_match': frozen_install_matches(install, folder)
            and module_sources_match(install, ROOT / 'dingtalk_bridge'),
        'only_manager_product_module_changed': [n for n in install['codeSha256'] if install['codeSha256'][n] != old_install['codeSha256'][n]] == ['service_manager.py'],
        'live_processes_unchanged_current_manager_status_healthy': read(folder / 'manager-state.json') == read(ROOT / 'local/route-process-20261112/manager-state.json')
            and read(folder / 'manager-status.json')['all_running'],
        'same_original_observer': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'transport_healthy': not after['health']['poll_error'],
    }
    for name in ('source-tests.log', 'installed-py314-tests.log', 'installed-py311-tests.log'):
        text = (folder / name).read_text();last = json.loads(text.splitlines()[-1])
        private = Path(last['evidence']);private.resolve().relative_to((ROOT / 'local').resolve())
        summary = read(private / 'summary.json')
        checks[name + '_197_passed_with_diagnostics'] = last['ok'] and summary['ok'] and summary['testsRun'] == 197 and not summary['retentionErrors']
    for kind in ('group', 'direct'):
        for key in ('jobs', 'outbox', 'events', 'deliveries', 'meta', 'runtimeFiles'):
            checks[kind + '_' + key + '_preserved'] = before['routes'][kind][key] == after['routes'][kind][key]
    return {'date': '2026-11-12', 'evidence': 'E062', 'ok': all(checks.values()), 'checks': checks,
            'fullTestCount': 197, 'newTestMethods': 2, 'newNativeUITest': False, 'liveProcessesRestarted': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'unavailableSamples': after['observer']['unavailable_samples'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in ('before-fix.log', 'old-installed-regression.log',
                'after-fix.log', 'captured-replay.json', 'source-tests.log', 'installed-py314-tests.log',
                'installed-py311-tests.log', 'py314-initial-preflight-failure.log')},
            'limits': ['Fixes the observed post-TERM same-birth E transition; does not assign unobserved historical failures the same cause',
                       'Transition permits bounded waiting only; pre-signal checks, different birth, non-E changes and timeout remain strict',
                       'Exact captured observation replay uses mocked ps and signal, not a new live process kill',
                       'Manager is invoked on demand; unchanged transport/gateway modules need no restart',
                       'Initial Python3.14 suite preflight rejected the preceding synthetic diagnostic directory; retained and narrowed to allow only test-evidence',
                       'No new UI or credentials experiment; original 24h incomplete']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/manager-exit-transition-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

#!/usr/bin/env python3
"""Read-only E061: actual route-owner process contention and death recovery."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, read, digest
from frozen_install import frozen_install_matches, module_sources_match


def audit():
    folder = ROOT / 'local/route-process-20261112'
    evidence = read(folder / 'actual-processes.json')
    before, after = (read(folder / n) for n in ('before-tests.json', 'after-tests.json'))
    install = read(ROOT / 'evidence/2026-11-12/atomic-manifest-install.json')
    checks = {
        'two_real_child_scenarios_passed': evidence['ok'] and len(evidence['cases']) == 2,
        'product_still_matches_frozen_E059': frozen_install_matches(install, ROOT / 'local/atomic-manifest-20261112')
            and module_sources_match(install, ROOT / 'dingtalk_bridge'),
        'live_manager_unchanged_and_running': read(folder / 'manager-state.json') == read(ROOT / 'local/manager-shutdown-20261112/manager-state.json')
            and read(folder / 'manager-status.json')['all_running'],
        'same_original_observer': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'healthy_after_tests': not after['health']['poll_error'],
    }
    for case in evidence['cases']:
        rows = case['observations'];mode = rows[0]['mode']
        expected = 'confirmed' if mode == 'confirmed' else 'outcome_unknown'
        checks[mode + '_crash_boundary_reached'] = rows[0]['ready']['ready'] and rows[0]['ready']['state'] == (
            'confirmed' if mode == 'confirmed' else 'executing')
        checks[mode + '_same_route_refused_and_other_route_independent'] = rows[1]['data']['rejected'] and rows[1]['data']['sends'] == 0 and rows[2]['data'] == {
            'rejected': False, 'events': 0, 'deliveries': 0, 'sends': 0}
        checks[mode + '_actual_owner_sigkill'] = rows[3]['ownerExitCode'] == -9
        checks[mode + '_different_scope_refused_without_sending'] = rows[4]['data']['rejected'] and rows[4]['data']['sends'] == 0
        checks[mode + '_resume_twice_keeps_state_no_resend_no_duplicate'] = rows[5]['data'] == rows[6]['data'] and all(
            r['data']['before']['state'] == expected and r['data']['result'] == {**r['data']['before'], 'replayed': True}
            and r['data']['sends'] == 0 and r['data']['mismatchRejected'] and r['data']['events'] == 2
            and r['data']['deliveries'] == 1 for r in rows[5:7])
    for label in ('source', 'py314', 'py311'):
        text = (folder / (label + '-tests.log')).read_text();last = json.loads(text.splitlines()[-1])
        private = Path(last['evidence']);private.resolve().relative_to((ROOT / 'local').resolve())
        result = read(private / 'summary.json')
        if label == 'py311':
            checks['py311_195_retains_one_new_manager_failure'] = not last['ok'] and not result['ok'] and result['testsRun'] == 195 and result['errors'] == 1 and result['failures'] == 0 and not result['retentionErrors']
            records = [r for r in result['refusals'] if r['test'].endswith('test_real_process_start_is_idempotent_and_stop_uses_persisted_ownership')]
            decision = read(private / records[0]['folder'] / 'decision.json') if len(records) == 1 else {}
            observed = decision.get('observed', {})
            checks['new_failure_same_decision_retained'] = decision.get('phase') == 'stop-after-signal' and observed.get('returncode') == 0 and observed.get('stdout', '').split()[0] == '?Es' and observed.get('identity', '').endswith('(python3.11)') and observed['identity'].split()[:5] == decision['record']['identity'].split()[:5]
        else:
            checks[label + '_195_passed_with_diagnostics'] = last['ok'] and result['ok'] and result['testsRun'] == 195 and not result['retentionErrors']
        if label != 'source':
            package = Path(read(folder / (label + '-import.json'))['module']).parent
            checks[label + '_installed_product_unchanged'] = 'site-packages' in package.parts and module_sources_match(install, package)
    for kind in ('group', 'direct'):
        checks[kind + '_all_previous_records_and_sessions_preserved'] = all(before['routes'][kind][key] == after['routes'][kind][key]
            for key in ('jobs', 'outbox', 'deliveries', 'events', 'meta', 'runtimeFiles'))
    return {'date': '2026-11-12', 'evidence': 'E061', 'ok': all(checks.values()), 'checks': checks,
            'fullTestCount': 195, 'installedPython311FullSuitePassed': False, 'newManagerFailureCaptured': True, 'newTestMethods': 2, 'productChanged': False, 'newNativeUITest': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'unavailableSamples': after['observer']['unavailable_samples'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in ('targeted.log', 'actual-processes.json',
                'source-tests.log', 'py314-tests.log', 'py311-tests.log')},
            'limits': ['Real independent processes and kernel locks with a synthetic provider; not a new DingTalk fault or UI test',
                       'Exactly one synthetic send entry per case is asserted in the tests; recovery does not infer external delivery',
                       'An executing reservation becomes outcome_unknown, never successful by assumption',
                       'No live service restart, credential changes or existing message replay',
                       'Python3.11 full suite has one new manager error: same-start-time ?Es (python3.11) after TERM; exact decision retained',
                       'This observed exiting transition is not proof of every historical error cause; real 24h is incomplete']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/route-process-recovery-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

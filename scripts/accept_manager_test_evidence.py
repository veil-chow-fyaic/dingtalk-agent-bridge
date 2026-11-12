#!/usr/bin/env python3
"""Read-only E060: bounded shutdown follow-up and retained test diagnostics."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, read, digest
from frozen_install import frozen_install_matches, module_sources_match


def audit():
    folder = ROOT / 'local/manager-shutdown-20261112'
    before, after = (read(folder / n) for n in ('before-runner.json', 'after-runner.json'))
    probe = read(folder / 'summary.json')
    install = read(ROOT / 'evidence/2026-11-12/atomic-manifest-install.json')
    old = ROOT / 'local/atomic-manifest-20261112'
    checks = {
        'bounded_followup_stopped_at_16_without_reproduction': probe['attemptLimit'] == 16
            and probe['stopOnFirstFailure'] and len(probe['cases']) == 16
            and all(r['ok'] for r in probe['cases']) and not probe['failuresPreserved'],
        'original_failure_log_retained': (old / 'full-py314-before-error-text.log').read_text().rstrip().endswith('FAILED (errors=1)'),
        'frozen_product_install_unchanged': frozen_install_matches(install, old)
            and module_sources_match(install, ROOT / 'dingtalk_bridge'),
        'manager_processes_unchanged': read(folder / 'manager-state.json') == read(old / 'manager-loaded.json')['state']
            and read(folder / 'manager-status.json')['all_running'],
        'observer_and_start_preserved': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'transport_healthy': not after['health']['poll_error'],
    }
    allowed = {
        'test_changed_pid_identity_never_signals_foreign_process',
        'test_diagnostic_write_failure_does_not_allow_signal',
        'test_replaced_identity_at_signal_time_is_still_rejected',
        'test_shutdown_error_keeps_deciding_observation_and_sends_no_more_signals',
        'test_original_failure_and_exact_observation_survive_fixture_cleanup',
        'test_retention_failure_does_not_mask_original_refusal',
    }
    for label in ('source', 'py314', 'py311'):
        text = (folder / (label + '-tests.log')).read_text()
        last = json.loads(text.splitlines()[-1]); private = Path(last['evidence'])
        private.resolve().relative_to((ROOT / 'local').resolve())
        report = read(private / 'summary.json')
        checks[label + '_193_passed_with_retention'] = last['ok'] and report['ok'] and report['testsRun'] == 193
        checks[label + '_seven_expected_refusals_only'] = len(report['refusals']) == 7 and all(
            r['test'].split('.')[-1] in allowed for r in report['refusals']) and not report['retentionErrors']
        complete = True
        for r in report['refusals']:
            saved = private / r['folder'];decision = read(saved / 'decision.json')
            complete &= decision['test'] == r['test'] and decision['phase'] == r['phase']
            complete &= saved.stat().st_mode & 0o777 == 0o700
            complete &= all(p.stat().st_mode & 0o777 == 0o600 for p in saved.iterdir())
            journal = saved / 'manager-identity-errors.ndjson'
            if journal.exists():
                error = json.loads(journal.read_text().splitlines()[-1])
                complete &= error['observed'] == decision['observed'] and error['phase'] == decision['phase']
        checks[label + '_same_decision_and_private_permissions'] = complete
        if label != 'source':
            imported = read(folder / (label + '-import.json'))
            package = Path(imported['module']).parent
            checks[label + '_uses_unchanged_installed_product'] = 'site-packages' in package.parts and module_sources_match(install, package)
    for kind in ('group', 'direct'):
        for key in ('jobs', 'outbox', 'deliveries', 'events', 'meta', 'runtimeFiles'):
            checks[kind + '_' + key + '_unchanged'] = before['routes'][kind][key] == after['routes'][kind][key]
    return {'date': '2026-11-12', 'evidence': 'E060', 'ok': all(checks.values()), 'checks': checks,
            'fullTestCount': 193, 'newTestMethods': 2, 'productChanged': False, 'newNativeUITest': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'unavailableSamples': after['observer']['unavailable_samples'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in (
                'tests.log', 'summary.json', 'evidence-runner-tests.log', 'source-tests.log',
                'py314-tests.log', 'py311-tests.log', 'initial-installed-failure.txt')},
            'limits': ['16 follow-ups did not reproduce the initial shutdown error; its cause remains unknown',
                       'Retained refusals in passing suites are expected negative tests, not fresh live failures',
                       'The original temporary ps diagnosis was lost before this runner existed; the runner cannot recover it',
                       'Product is the same E059 install; no restart, account operation or new UI',
                       'Python3.11 initial environment path typo was corrected without rerunning passed Python3.14']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/manager-test-evidence-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

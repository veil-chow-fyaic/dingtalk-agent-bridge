#!/usr/bin/env python3
"""Read-only E068: sanitized DWS credential-store diagnostics, isolated recovery, and no live reload."""
import argparse
import json
from pathlib import Path
import zipfile
from accept_office_files import ROOT, read, digest
from frozen_install import module_sources_match


def audit():
    folder = ROOT / 'local/credential-health-20261112'
    report = read(folder / 'install-report.json')
    before, after = (read(folder / n) for n in ('before.json', 'after.json'))
    wheel, = (folder / 'wheels').glob('*.whl')
    tests = {}
    for name in ('source', 'py314', 'py311'):
        result = json.loads((folder / (name + '-final-tests.log')).read_text().splitlines()[-1])
        path = Path(result['evidence']);path.resolve().relative_to((ROOT / 'local').resolve())
        tests[name] = read(path / 'summary.json')
    old = read(ROOT / 'local/image-build-20261112/manager-after.json')
    status = read(folder / 'manager-status.json')
    protected = read(ROOT / 'local/image-build-20261112/protected-after.json')
    checks = {
        'old_five_method_failure_retained': 'failures=1, errors=6' in (folder / 'before-fix.log').read_text(),
        'six_final_targeted_methods_passed': 'Ran 6 tests' in (folder / 'final-targeted.log').read_text()
            and '\nOK\n' in (folder / 'final-targeted.log').read_text(),
        'source_and_both_installed_207_test_runs_passed': all(t['ok'] and t['testsRun'] == 207
            and not t['retentionErrors'] for t in tests.values()),
        'original_official_stderr_shape_classified_without_new_call': read(folder / 'real-error-replay.json') == {
            'classified': True, 'code': 'credential_store_unavailable', 'actualOfficialCalls': 0, 'originalErrorStream': 'stderr'},
        'new_wheel_digest_matches': digest(wheel.read_bytes()) == report['wheelSha256'],
        'all_19_frozen_source_modules_match': len(report['codeSha256']) == 19
            and module_sources_match(report, folder / 'clean-source/dingtalk_bridge'),
        'both_new_installed_modules_match': all(module_sources_match(report,
            Path(read(folder / (n + '-import.json'))['module']).parent) for n in ('py314', 'py311')),
        'both_new_installs_have_six_working_entrypoints': all(len(r['entrypoints']) == 6
            and not any(r['entrypoints'].values()) and r['exitCode'] == 0 for r in report['results']),
        'installed_suite_has_no_product_source_or_account_data': not (folder / 'installed-suite/dingtalk_bridge').exists()
            and {p.name for p in (folder / 'installed-suite/local').iterdir()} == {'test-evidence'},
        'installed_final_regression_matches_frozen_test': digest((folder / 'installed-suite/tests/test_credential_health.py').read_bytes())
            == '4d3a5bc3c7fe3372539da2a49309bf2400cffa12acf6fd9d1ae8c879b6007be3',
        'old_handoff_and_image_reaudits_use_frozen_source': all(read(folder / n)['ok']
            and read(folder / n)['currentProductMatchesFrozen'] is False
            for n in ('old-handoff-after.log', 'old-image-after.log')),
        'two_frozen_digest_tamper_negatives_rejected': len(read(folder / 'frozen-audit-negative.json')) == 2
            and all(r['tamperedFrozenModuleRejected'] for r in read(folder / 'frozen-audit-negative.json')),
        'old_shared_reports_not_rewritten': all(digest((ROOT / 'evidence/2026-11-12' / n).read_bytes()) == sha
            for n, sha in read(folder / 'old-report-sha256.json').items()),
        'original_three_managed_pids_still_running': status['all_running'] and len(status['components']) == 3
            and {r['pid'] for r in status['components']} == {r['pid'] for r in old['components']},
        'official_binaries_and_live_configs_unchanged': all(digest((ROOT / n).read_bytes()) == sha for n, sha in protected.items()),
        'original_observer_not_restarted': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'unresolved_live_failure_is_not_reported_as_fixed': before['health']['poll_error'] and after['health']['poll_error']
            and report['deployed'] is False,
    }
    with zipfile.ZipFile(wheel) as archive:
        checks['wheel_modules_match_source'] = all(digest(archive.read('dingtalk_bridge/' + n)) == sha
            for n, sha in report['codeSha256'].items())
    for kind in ('group', 'direct'):
        checks[kind + '_old_records_session_and_logs_unchanged'] = all(before['routes'][kind][key] == after['routes'][kind][key]
            for key in ('jobs', 'outbox', 'events', 'deliveries', 'meta', 'runtimeFiles'))
    return {'date': '2026-11-12', 'evidence': 'E068', 'ok': all(checks.values()), 'checks': checks,
        'currentProductMatchesFrozen': module_sources_match(report, ROOT / 'dingtalk_bridge'),
        'testsPerSuite': 207, 'newMethods': 6, 'deployed': False, 'newNativeUITest': False,
        'liveCredentialFailureResolved': False, 'wheelSha256': report['wheelSha256'], 'codeSha256': report['codeSha256'],
        'logSha256': {n: digest((folder / n).read_bytes()) for n in ('before-fix.log', 'final-targeted.log',
            'source-final-tests.log', 'py314-final-tests.log', 'py311-final-tests.log', 'real-error-replay.json',
            'old-handoff-before.log', 'old-image-before.log', 'old-handoff-after.log', 'old-image-after.log', 'frozen-audit-negative.json')},
        'limits': ['Only the exact pinned official Keychain failure shape is classified; unknown errors remain generic',
            'Provider error text is never copied to health/doctor; no expiry/locked-keychain conclusion is inferred',
            'HTTP recovery and same-key restart tests use isolated synthetic DWS processes, not the live credentials',
            'No authentication policy, credential reset/migration, automatic retry or delivery reconciliation change',
            'Current source/new wheel include this diagnostic; existing live processes have not loaded it',
            'Original 24h observation and live Keychain failure remain unresolved']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/credential-health-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

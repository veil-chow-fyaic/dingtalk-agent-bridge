#!/usr/bin/env python3
"""Read-only E064: optional image builder ownership, real build, and live boundaries."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, read, digest
from frozen_install import module_sources_match


def audit():
    folder = ROOT / 'local/image-build-20261112'
    source = ROOT / 'integrations/dws_image_upload'
    receipt = read(folder / 'bin/dws-image-upload.build.json')
    before, after = (read(folder / n) for n in ('before.json', 'after.json'))
    protected = read(folder / 'protected-before.json')
    plan = read(folder / 'plan.stdout')['data']
    provenance = read(folder / 'source-provenance.json')
    tests = {}
    for name in ('source', 'py314', 'py311'):
        result = json.loads((folder / (name + '-tests.log')).read_text().splitlines()[-1])
        path = Path(result['evidence']);path.resolve().relative_to((ROOT / 'local').resolve())
        tests[name] = read(path / 'summary.json')
    frozen_product = read(ROOT / 'evidence/2026-11-12/manager-exit-install.json')
    checks = {
        'old_overwrite_failure_retained': 'failures=3, errors=1' in (folder / 'before-fix.log').read_text(),
        'four_new_builder_tests_passed': 'Ran 4 tests' in (folder / 'after-fix.log').read_text()
            and '\nOK\n' in (folder / 'after-fix.log').read_text(),
        'all_three_201_test_runs_passed_with_diagnostics': all(t['ok'] and t['testsRun'] == 201
            and not t['retentionErrors'] for t in tests.values()),
        'installed_suites_exclude_product_source': not (folder / 'installed-suite/dingtalk_bridge').exists()
            and all(r['exitCode'] == 0 and r['sourcePackageAbsent'] for r in read(folder / 'installed-results.json')),
        'installed_builder_and_test_match_current_public_files': all(
            (folder / 'installed-suite' / n).read_bytes() == (ROOT / n).read_bytes()
            for n in ('integrations/dws_image_upload/build.py', 'tests/test_image_build.py')),
        'separate_checkout_started_clean_at_pinned_commit': provenance['cleanBeforeBuild']
            and provenance['upstreamCommit'] == receipt['upstreamCommit'] == '63a7c4906c7dee10750011ea309b9eb78abb7eb0',
        'failed_network_clone_retained': provenance['networkCloneFailed'] and (folder / 'clone.log').stat().st_size > 0,
        'only_expected_source_changes': read(folder / 'source-after.json') == {
            'trackedChanged': ['internal/helpers/chat.go'],
            'untracked': ['internal/helpers/bridge_image_upload.go', 'internal/helpers/bridge_image_upload_test.go']},
        'real_go_helper_and_schema_tests_passed': all('ok  \tgithub.com/DingTalk-Real-AI/dingtalk-workspace-cli/' + n
            in (folder / 'real-build.log').read_text() for n in ('internal/helpers', 'internal/app')),
        'receipt_matches_actual_new_binary_and_public_go_sources': all(
            receipt[k] == digest(path.read_bytes()) for k, path in (
                ('binarySha256', folder / 'bin/dws-image-upload'), ('addonSha256', source / 'bridge_image_upload.go'),
                ('testSha256', source / 'bridge_image_upload_test.go'))),
        'new_build_did_not_claim_stock_protection_without_measurement': receipt['replacedVerifiedOutput'] is False
            and 'stockDWSUnchanged' not in receipt,
        'protected_stock_live_supplement_and_three_configs_unchanged': len(protected) == 5
            and protected == read(folder / 'protected-after.json')
            and all(digest((ROOT / n).read_bytes()) == sha for n, sha in protected.items()),
        'new_help_and_plan_succeeded': read(folder / 'cli-checks.json')['commands'] == [
            {'name': 'help', 'exitCode': 0}, {'name': 'plan', 'exitCode': 0}],
        'isolated_dws_config_contains_only_generated_log': {
            str(p.relative_to(folder / 'empty-dws-config')) for p in (folder / 'empty-dws-config').rglob('*') if p.is_file()
        } == {'logs/dws.log'},
        'plan_only_no_upload_or_compression': plan['dry_run'] and not plan['executed'] and not plan['compressed']
            and plan['steps'][0]['args']['bizType'] == 'CHAT_IMAGE' and plan['size'] == 1853,
        'frozen_runtime_source_matches_installed_version': module_sources_match(frozen_product,
            ROOT / 'local/manager-exit-20261112/clean-source/dingtalk_bridge'),
        'both_installed_runtime_modules_still_match': all(module_sources_match(frozen_product,
            Path(read(folder / (n + '-import.json'))['module']).parent) for n in ('py314', 'py311')),
        'manager_processes_not_changed': read(folder / 'manager-before.json') == read(folder / 'manager-after.json'),
        'observer_not_restarted': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'new_real_sync_failure_preserved': not before['health']['poll_error'] and after['health']['poll_error']
            and read(ROOT / 'local/sync-failure-20261112/official-summary.json')['exitCode'] == 51,
    }
    for kind in ('group', 'direct'):
        checks[kind + '_records_session_and_runtime_logs_unchanged'] = all(before['routes'][kind][key] == after['routes'][kind][key]
            for key in ('jobs', 'outbox', 'events', 'deliveries', 'meta', 'runtimeFiles'))
    names = ('before-fix.log', 'after-fix.log', 'source-tests.log', 'py314-tests.log', 'py311-tests.log',
             'real-build.log', 'clone.log', 'local-clone.log', 'help.stdout', 'plan.stdout')
    return {'date': '2026-11-12', 'evidence': 'E064', 'ok': all(checks.values()), 'checks': checks,
        'receipt': receipt, 'fullTestsPerSuite': 201, 'runtimeChanged': False, 'deployed': False,
        'currentProductMatchesFrozen': module_sources_match(frozen_product, ROOT / 'dingtalk_bridge'),
        'newNativeUITest': False, 'transportHealthyAfterBuild': not after['health']['poll_error'],
        'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
        'logSha256': {n: digest((folder / n).read_bytes()) for n in names},
        'limits': ['Audit success validates recorded evidence; the live Keychain failure remains unresolved',
            'Installed suites use the installed runtime plus copied public integrations helper, not a helper in the runtime wheel',
            'Git network clone failed; independent checkout used verified local official Git objects',
            'Real Go build used the existing toolchain and cached dependencies with module network disabled',
            'Fresh binary differs from the live supplement; no bit-for-bit reproducibility or deployment claim',
            'Isolated DWS config acquired a log, so emptyDwsConfig=false is preserved; no account configuration was copied',
            'No OS sandbox, hostile concurrent writer, fresh upload, new UI or completed 24h claim']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/image-build-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

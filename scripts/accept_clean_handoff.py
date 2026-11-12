#!/usr/bin/env python3
"""Read-only E063: immutable Git export, offline build/install, and live noninterference."""
import argparse
import json
from pathlib import Path
import tarfile
import zipfile
from accept_office_files import ROOT, read, digest
from frozen_install import module_sources_match
from verify_privacy import known_private_values


def audit():
    folder = ROOT / 'local/clean-handoff-20261112';bundle = folder / 'bundle'
    report = read(ROOT / 'evidence/2026-11-12/clean-handoff-build.json')
    before, after = (read(folder / n) for n in ('before.json', 'after.json'))
    wheel, = (bundle / 'wheels').glob('*.whl')
    private_values = known_private_values(ROOT)
    with tarfile.open(bundle / 'source.tar') as archive:
        members = archive.getmembers()
        safe_names = all(not m.issym() and not m.islnk() and not Path(m.name).is_absolute()
            and '..' not in Path(m.name).parts and Path(m.name).parts[0] not in {'local', '.git'} for m in members)
        files = {m.name: archive.extractfile(m).read() for m in members if m.isfile()}
    exported_manifest = json.loads(files['evidence/handoff-manifest.json'])
    with zipfile.ZipFile(wheel) as archive:
        modules_match = all(digest(archive.read('dingtalk_bridge/' + n)) == sha for n, sha in report['codeSha256'].items())
        wheel_private_absent = all(not any(v in archive.read(n) for v in private_values) for n in archive.namelist() if not n.endswith('/'))
    test_result = json.loads((folder / 'installed-tests.log').read_text().splitlines()[-1])
    test_folder = Path(test_result['evidence']);test_folder.resolve().relative_to((ROOT / 'local').resolve())
    tests = read(test_folder / 'summary.json')
    imported = read(folder / 'installed-import.log')
    checks = {
        'source_archive_digest_matches_frozen_report': digest((bundle / 'source.tar').read_bytes()) == report['sourceArchiveSha256'],
        'archive_names_and_types_exclude_private_roots': safe_names,
        'all_492_exported_manifest_entries_match': len(exported_manifest['sha256']) == 492
            and all(digest(files[n]) == sha for n, sha in exported_manifest['sha256'].items()),
        'exported_source_still_identical_after_build_and_tests': all((folder / 'source' / n).is_file()
            and digest((folder / 'source' / n).read_bytes()) == digest(data) for n, data in files.items()),
        'no_known_private_values_in_archive_or_wheel': wheel_private_absent and not any(v in data for data in files.values() for v in private_values),
        'wheel_digest_and_all_modules_match': digest(wheel.read_bytes()) == report['wheelSha256'] and modules_match,
        'frozen_product_source_matches_export': module_sources_match(report, folder / 'source/dingtalk_bridge'),
        'build_dependencies_prepared_and_frozen_separately': len(report['buildDependenciesPreparedSeparately']) == 3 and all(
            digest((folder / 'build-wheelhouse' / item['file']).read_bytes()) == item['sha256'] for item in report['buildDependenciesPreparedSeparately']),
        'all_16_offline_steps_successful': len(report['offlineSteps']) == 16 and all(r['exitCode'] == 0 for r in report['offlineSteps']),
        'new_python311_install_is_from_site_packages_and_has_no_runtime_dependencies': 'site-packages' in Path(imported['module']).parts
            and imported['python'].startswith('3.11.') and imported['runtimeRequiresDist'] == [],
        'installed_modules_match_export': module_sources_match(report, Path(imported['module']).parent),
        'installed_suite_has_no_source_package_or_account_configuration': not (folder / 'installed-suite/dingtalk_bridge').exists()
            and {p.name for p in (folder / 'installed-suite/local').iterdir()} == {'test-evidence'},
        'installed_197_tests_and_diagnostic_retention_passed': test_result['ok'] and tests['ok'] and tests['testsRun'] == 197 and not tests['retentionErrors'],
        'empty_workspace_status_does_not_create_state': read(folder / 'empty-service-status.log')['managed'] is False and not list((folder / 'empty-workspace').iterdir()),
        'manager_processes_unchanged_and_healthy': read(folder / 'manager-before.json') == read(folder / 'manager-after.json')
            and read(folder / 'manager-status.json')['all_running'],
        'original_observer_preserved': before['observer']['pid'] == after['observer']['pid'] == 97881
            and before['observer']['startedAt'] == after['observer']['startedAt'] and after['observer']['active'],
        'transport_healthy': not after['health']['poll_error'],
    }
    for kind in ('group', 'direct'):
        checks[kind + '_records_session_and_logs_unchanged'] = all(before['routes'][kind][key] == after['routes'][kind][key]
            for key in ('jobs', 'outbox', 'events', 'deliveries', 'meta', 'runtimeFiles'))
    return {'date': '2026-11-12', 'evidence': 'E063', 'ok': all(checks.values()), 'checks': checks,
            'currentProductMatchesFrozen': module_sources_match(report, ROOT / 'dingtalk_bridge'),
            'sourceCommit': report['commit'], 'fullInstalledTests': 197, 'productChanged': False, 'newNativeUITest': False,
            'observerElapsedHours': round(after['observer']['elapsed_seconds'] / 3600, 3),
            'unavailableSamples': after['observer']['unavailable_samples'],
            'logSha256': {n: digest((folder / n).read_bytes()) for n in ('offline-build-tools.log', 'offline-build.log',
                'offline-install.log', 'installed-tests.log', 'export-manifest-before.log', 'export-manifest-after.log')},
            'limits': report['limits'] + ['The archive is immutable at its stated Git commit; this later audit record is separate from that commit',
                'No Linux certification, new UI, real credential-expiry experiment or completed 24h claim']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args();result = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-12/clean-handoff-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2));raise SystemExit(0 if result['ok'] else 1)

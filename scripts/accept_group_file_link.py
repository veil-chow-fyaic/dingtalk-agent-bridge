#!/usr/bin/env python3
"""Read-only E070 frozen group file association verification; no account calls."""
import argparse
import json
from pathlib import Path
import zipfile
from accept_office_files import ROOT,read,digest
from frozen_install import module_sources_match


def audit():
    folder=ROOT/'local/group-file-link-20261112'
    install=read(folder/'install-report.json');before=read(folder/'before.json');after=read(folder/'after.json')
    tests={}
    for name in ('source','py314','py311'):
        outcome=json.loads((folder/(name+'-tests.log')).read_text().splitlines()[-1])
        path=Path(outcome['evidence']);path.resolve().relative_to((ROOT/'local').resolve())
        tests[name]=read(path/'summary.json')
    wheel,=(folder/'wheels').glob('*.whl')
    status=read(folder/'manager-status.json');prior=read(ROOT/'local/credential-health-20261112/manager-status.json')
    checks={
        'old_seven_method_fifteen_failures_retained':'Ran 7 tests' in (folder/'before-fix.log').read_text() and 'failures=15' in (folder/'before-fix.log').read_text(),
        'nine_final_targeted_methods_passed':'Ran 9 tests' in (folder/'targeted-final.log').read_text() and '\nOK\n' in (folder/'targeted-final.log').read_text(),
        'source_and_both_installed_216_tests_passed':all(t['ok'] and t['testsRun']==216 and not t['retentionErrors'] for t in tests.values()),
        'wheel_digest_matches':digest(wheel.read_bytes())==install['wheelSha256'],
        'all_19_frozen_modules_match':len(install['codeSha256'])==19 and module_sources_match(install,folder/'clean-source/dingtalk_bridge'),
        'both_installed_modules_match':all(module_sources_match(install,Path(read(folder/(n+'-import.json'))['module']).parent) for n in ('py314','py311')),
        'six_entrypoints_both_installs':len(install['results'])==2 and all(r['exitCode']==0 and len(r['entrypoints'])==6 and not any(r['entrypoints'].values()) for r in install['results']),
        'installed_suite_without_product_source_or_account_data':not (folder/'installed-suite/dingtalk_bridge').exists() and {p.name for p in (folder/'installed-suite/local').iterdir()}=={'test-evidence'},
        'e068_frozen_reaudit_passed_with_current_difference':read(folder/'e068-after.log')['ok'] and read(folder/'e068-after.log')['currentProductMatchesFrozen'] is False,
        'e068_frozen_tamper_rejected':read(folder/'e068-negative.json')['changedFrozenDigestRejected'],
        'original_e068_report_unchanged':digest((ROOT/'evidence/2026-11-12/credential-health-validation.json').read_bytes())==read(folder/'e068-original-report-sha.json')['sha256'],
        'live_three_managed_processes_unchanged':status['all_running'] and len(status['components'])==3 and {c['pid'] for c in status['components']}=={c['pid'] for c in prior['components']},
        'official_binaries_and_live_configs_unchanged':all(digest((ROOT/n).read_bytes())==sha for n,sha in read(ROOT/'local/image-build-20261112/protected-after.json').items()),
        'original_observation_preserved':before['observer']['pid']==after['observer']['pid']==97881 and before['observer']['startedAt']==after['observer']['startedAt'] and after['observer']['active'],
        'live_auth_failure_still_open':bool(before['health']['poll_error']) and bool(after['health']['poll_error']) and install['deployed'] is False,
    }
    with zipfile.ZipFile(wheel) as archive:
        checks['wheel_all_modules_match']=all(digest(archive.read('dingtalk_bridge/'+n))==sha for n,sha in install['codeSha256'].items())
    for kind in ('group','direct'):
        checks[kind+'_old_ledger_session_and_runtime_files_unchanged']=all(before['routes'][kind][key]==after['routes'][kind][key] for key in ('jobs','outbox','events','deliveries','meta','runtimeFiles'))
    return {'date':'2026-11-12','evidence':'E070','ok':all(checks.values()),'checks':checks,
        'currentProductMatchesFrozen':module_sources_match(install,ROOT/'dingtalk_bridge'),
        'testsPerSuite':216,'newMethods':9,'deployed':False,'newNativeUITest':False,'liveCredentialFailureResolved':False,
        'wheelSha256':install['wheelSha256'],'codeSha256':install['codeSha256'],
        'testSha256':digest((folder/'installed-suite/tests/test_group_file_link.py').read_bytes()),
        'logSha256':{n:digest((folder/n).read_bytes()) for n in ('before-fix.log','targeted-final.log','source-tests.log','py314-tests.log','py311-tests.log','e068-before.log','e068-after.log','e068-negative.json')},
        'limits':['Explicit group --files selection only; ordinary group files do not execute',
            'At most eight unique names from the same sender and route, preceding fifty events and thirty minutes',
            'Missing or ambiguous names are blocked; source bindings are persisted and never guessed from future files',
            'Synthetic providers/runtime and real local download threads; not DingTalk UI or actual Kimi acceptance',
            'No official upload protocol, native multiple-file message, authorization, runtime binding or delivery changes',
            'New wheel not deployed; live Keychain failure and remaining UI/24h work are open']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');args=p.parse_args();result=audit()
    if args.write_evidence:(ROOT/'evidence/2026-11-12/group-file-link-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 1)

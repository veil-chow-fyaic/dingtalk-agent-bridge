#!/usr/bin/env python3
"""Read-only E072 offline verification. Never starts DWS, a service, or a login probe."""
import argparse
import json
from pathlib import Path
import zipfile
from accept_office_files import ROOT, read, digest
from frozen_install import module_sources_match


def audit():
    folder=ROOT/'local/dws-containment-final-20261112'
    install=read(folder/'install-report.json')
    tests={}
    for name,filename in [('source','source-final-tests.log'),('py314','py314-tests.log'),('py311','py311-tests.log')]:
        outcome=json.loads((folder/filename).read_text().splitlines()[-1])
        path=Path(outcome['evidence']);path.resolve().relative_to((ROOT/'local').resolve())
        tests[name]=read(path/'summary.json')
    wheel,=(folder/'wheels').glob('*.whl')
    status=read(folder/'manager-status.json')
    protected=read(ROOT/'local/image-build-20261112/protected-after.json')
    checks={
        'old_stdin_eof_regression_retained':'FAILED (failures=1)' in (folder/'stdin-before-fix.log').read_text(),
        'old_orphan_process_failure_retained':'FAILED (failures=1)' in (folder/'before-fix.log').read_text(),
        'initial_serialization_regressions_retained':'FAILED (failures=5)' in (folder/'source-tests.log').read_text(),
        'short_test_startup_budget_failure_retained':'FAILED (errors=1)' in (folder/'revised-targeted.log').read_text(),
        'twenty_one_final_targeted_methods_passed':'Ran 21 tests' in (folder/'verified-targeted.log').read_text() and '\nOK\n' in (folder/'verified-targeted.log').read_text(),
        'source_and_both_installed_228_tests_passed':all(t['ok'] and t['testsRun']==228 and not t['retentionErrors'] for t in tests.values()),
        'wheel_digest_matches':digest(wheel.read_bytes())==install['wheelSha256'],
        'twenty_frozen_source_modules_match':len(install['codeSha256'])==20 and module_sources_match(install,folder/'clean-source/dingtalk_bridge'),
        'both_installed_modules_match':all(module_sources_match(install,Path(read(folder/(n+'-import.json'))['module']).parent) for n in ('py314','py311')),
        'six_entrypoints_both_installs':len(install['results'])==2 and all(r['exitCode']==0 and len(r['entrypoints'])==6 and not any(r['entrypoints'].values()) for r in install['results']),
        'installed_suite_without_product_source_or_account_data':not (folder/'installed-suite/dingtalk_bridge').exists() and {p.name for p in (folder/'installed-suite/local').iterdir()}=={'test-evidence'},
        'historical_e068_uses_frozen_source_and_test':read(folder/'e068-reaudit.json')['ok'] and read(folder/'e068-reaudit.json')['currentProductMatchesFrozen'] is False,
        'historical_e068_frozen_test_tamper_rejected':read(folder/'e068-negative.json')['ok'],
        'historical_e068_public_report_unchanged':digest((ROOT/'evidence/2026-11-12/credential-health-validation.json').read_bytes())==read(folder/'e068-negative.json')['originalReportSha256'],
        'three_services_remained_stopped_at_checkpoint':not status['all_running'] and len(status['components'])==3 and all(c['status']=='stopped' for c in status['components']),
        'official_binaries_and_live_configs_unchanged':all(digest((ROOT/n).read_bytes())==sha for n,sha in protected.items()),
        'not_deployed':install['deployed'] is False,
        'services_still_stopped_after_verification':read(folder/'manager-after.json')==status,
        'frozen_module_tamper_rejected':read(folder/'negative.json')['frozenModuleTamperRejected'],
    }
    with zipfile.ZipFile(wheel) as archive:
        checks['wheel_modules_match']=all(digest(archive.read('dingtalk_bridge/'+n))==sha for n,sha in install['codeSha256'].items())
    return {'date':'2026-11-12','evidence':'E072','ok':all(checks.values()),'checks':checks,
        'currentProductMatchesFrozen':module_sources_match(install,ROOT/'dingtalk_bridge'),
        'testsPerSuite':228,'newMethods':12,'deployed':False,'deploymentEligible':False,
        'realDwsCalls':0,'newNativeUITest':False,'liveCredentialFailureResolved':False,
        'wheelSha256':install['wheelSha256'],'codeSha256':install['codeSha256'],
        'frozenTestSha256':{n:digest((folder/'installed-suite/tests'/n).read_bytes()) for n in
            ('test_dws_containment.py','test_credential_health.py','test_core.py','test_rejection.py')},
        'logSha256':{n:digest((folder/n).read_bytes()) for n in
            ('before-fix.log','stdin-before-fix.log','source-tests.log','revised-targeted.log','verified-targeted.log','source-final-tests.log','py314-tests.log','py311-tests.log')},
        'limits':['Synthetic processes and loopback HTTP only; no official CLI or Keychain calls',
            'At most two RPCs/Stream handshakes per workspace; existing in-flight calls may finish',
            'Persistent latch blocks subsequent bridge calls; explicit resume does not itself probe credentials',
            'Supervisor cleans owned process groups on CLI exit, timeout and parent death',
            'Detached official event bus and direct runtime official-tool invocations remain uncovered; do not restore services yet',
            'No claim of macOS repair, UI delivery, deployment readiness or completed project acceptance']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence',action='store_true')
    args=parser.parse_args();result=audit()
    if args.write_evidence:(ROOT/'evidence/2026-11-12/dws-containment-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 1)

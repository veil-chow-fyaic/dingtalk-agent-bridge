#!/usr/bin/env python3
"""Read-only E073 frozen runtime office proxy verification; never invokes DWS."""
import argparse
import json
from pathlib import Path
import zipfile
from accept_office_files import ROOT, read, digest
from frozen_install import module_sources_match


def audit():
    folder=ROOT/'local/official-proxy-20261112';install=read(folder/'install-report.json')
    tests={}
    for name,filename in [('source','source-final-tests.log'),('py314','py314-tests.log'),('py311','py311-tests.log')]:
        outcome=json.loads((folder/filename).read_text().splitlines()[-1])
        path=Path(outcome['evidence']);path.resolve().relative_to((ROOT/'local').resolve())
        tests[name]=read(path/'summary.json')
    wheel,=(folder/'wheels').glob('*.whl')
    status=read(folder/'manager-status.json');pause=read(folder/'local-suspension.json')
    checks={
        'old_runtime_entrypoint_repeated_read_failure_retained':'FAILED (failures=1)' in (folder/'before-fix.log').read_text(),
        'canonical_path_fixture_failures_retained':'FAILED (failures=6)' in (folder/'targeted.log').read_text(),
        'old_gateway_raw_binary_expectation_failure_retained':'FAILED (failures=1)' in (folder/'source-tests.log').read_text(),
        'fourteen_final_targeted_methods_passed':'Ran 14 tests' in (folder/'final-targeted.log').read_text() and '\nOK\n' in (folder/'final-targeted.log').read_text(),
        'source_and_both_installed_237_tests_passed':all(t['ok'] and t['testsRun']==237 and not t['retentionErrors'] for t in tests.values()),
        'wheel_digest_matches':digest(wheel.read_bytes())==install['wheelSha256'],
        'twenty_one_frozen_modules_match':len(install['codeSha256'])==21 and module_sources_match(install,folder/'clean-source/dingtalk_bridge'),
        'both_installed_modules_match':all(module_sources_match(install,Path(read(folder/(n+'-import.json'))['module']).parent) for n in ('py314','py311')),
        'six_entrypoints_both_installs':len(install['results'])==2 and all(r['exitCode']==0 and len(r['entrypoints'])==6 and not any(r['entrypoints'].values()) for r in install['results']),
        'installed_suite_without_product_source_or_account_data':not (folder/'installed-suite/dingtalk_bridge').exists() and {p.name for p in (folder/'installed-suite/local').iterdir()}=={'test-evidence'},
        'e072_frozen_audit_still_passes_with_current_difference':read(folder/'e072-reaudit.json')['ok'] and read(folder/'e072-reaudit.json')['currentProductMatchesFrozen'] is False,
        'three_services_remained_stopped':not status['all_running'] and len(status['components'])==3 and all(c['status']=='stopped' for c in status['components']),
        'official_binaries_and_live_configs_unchanged':all(digest((ROOT/n).read_bytes())==sha for n,sha in read(ROOT/'local/image-build-20261112/protected-after.json').items()),
        'local_operator_suspension_without_authentication':pause['officialCalls']==pause['credentialReads']==0 and pause['mode']=='0o600' and pause['after']=={'state':'suspended','reason':'operator_suspended'},
        'not_deployed':install['deployed'] is False,
    }
    with zipfile.ZipFile(wheel) as archive:
        checks['wheel_modules_match']=all(digest(archive.read('dingtalk_bridge/'+n))==sha for n,sha in install['codeSha256'].items())
    return {'date':'2026-11-12','evidence':'E073','ok':all(checks.values()),'checks':checks,
        'currentProductMatchesFrozen':module_sources_match(install,ROOT/'dingtalk_bridge'),
        'testsPerSuite':237,'newMethods':9,'deployed':False,'deploymentEligible':False,
        'realDwsCalls':0,'newNativeUITest':False,'liveCredentialFailureResolved':False,
        'wheelSha256':install['wheelSha256'],'codeSha256':install['codeSha256'],
        'frozenTestSha256':{n:digest((folder/'installed-suite/tests'/n).read_bytes()) for n in
            ('test_official_proxy.py','test_official_tools.py','test_agent_gateway.py')},
        'logSha256':{n:digest((folder/n).read_bytes()) for n in
            ('before-fix.log','targeted.log','final-targeted.log','source-tests.log','source-final-tests.log','py314-tests.log','py311-tests.log')},
        'limits':['The generated runtime context now selects the supervised office entrypoint, not the raw CLI',
            'Six office command families; arguments, working directory, raw stdout/stderr and exit status are preserved',
            'Explicit profile/as-user/json binding; auth/event/dev/mcp and credential overrides are not enabled',
            'No OS sandbox: a caller deliberately bypassing or editing the generated entrypoint is not contained',
            'Synthetic runtime, CLI and process-death tests only; no actual Kimi, DingTalk UI or credential access',
            'Shared detached official Stream bus remains a deployment blocker; real services stay stopped']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence',action='store_true')
    args=parser.parse_args();result=audit()
    if args.write_evidence:(ROOT/'evidence/2026-11-12/official-proxy-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 1)

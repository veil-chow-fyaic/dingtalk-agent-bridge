#!/usr/bin/env python3
"""Read-only E074 frozen checks. Never executes the prepared real read."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, read, digest
from frozen_install import module_sources_match


def audit():
    folder=ROOT/'local/recovery-plan-20261112';report=read(folder/'installed-report.json')
    prior=ROOT/'local/official-proxy-20261112';install=read(prior/'install-report.json')
    preparation=read(folder/'preparation-state.json');plan=read(folder/'prepared-plan.json')
    manager=read(folder/'manager-status.json');tests={}
    for name,file in [('source','source-final-tests.log'),('py314','py314-tests.log'),('py311','py311-tests.log')]:
        outcome=json.loads((folder/file).read_text().splitlines()[-1])
        path=Path(outcome['evidence']);path.resolve().relative_to((ROOT/'local').resolve())
        tests[name]=read(path/'summary.json')
    checks={
        'source_and_both_installed_244_tests_passed':all(t['ok'] and t['testsRun']==244 and not t['retentionErrors'] for t in tests.values()),
        'unchanged_e073_product_reused':report['newWheelBuilt'] is False and report['codeSha256']==install['codeSha256'] and report['wheelSha256']==install['wheelSha256'],
        'frozen_twenty_one_modules_match':len(report['codeSha256'])==21 and module_sources_match(report,prior/'clean-source/dingtalk_bridge'),
        'both_installed_modules_match':all(module_sources_match(report,Path(read(folder/(n+'-import.json'))['module']).parent) for n in ('py314','py311')),
        'both_new_suites_successful_without_product_source':not (folder/'installed-suite/dingtalk_bridge').exists() and all(r['exitCode']==0 and r['modulesMatch'] for r in report['results']),
        'checker_matches_frozen_installed_copy':report['checkerSha256']==digest((folder/'installed-suite/scripts/check_dws_recovery_once.py').read_bytes()),
        'prepared_checker_matches_tested_checker':plan['checkerSha256']==report['checkerSha256']==preparation['checkerSha256'],
        'prepared_library_matches_tested_library':plan['packageSha256']==report['codeSha256'],
        'prepared_one_read_fifteen_seconds_keeps_pause':plan['operation']=='chat +conversation-info' and plan['maxInvocations']==1 and plan['timeoutSeconds']==15 and plan['keepsSuspended'] is True,
        'preparation_checkpoint_has_no_attempt':preparation['attempted'] is False and preparation['officialCalls']==0,
        'operator_pause_unchanged_at_checkpoint':preparation['paused']=={'state':'suspended','reason':'operator_suspended'},
        'services_stopped_at_checkpoint':not manager['all_running'] and len(manager['components'])==3 and all(c['status']=='stopped' for c in manager['components']),
        'frozen_protected_config_and_binary_digests_unchanged':preparation['liveConfigsAndOfficialBinariesUnchanged'] and preparation['protectedSha256']==read(ROOT/'local/image-build-20261112/protected-after.json'),
        'raw_account_data_not_copied_into_suite':{p.name for p in (folder/'installed-suite/local').iterdir()}=={'test-evidence'},
        'not_deployed':report['deployed'] is False,
    }
    return {'date':'2026-11-12','evidence':'E074','ok':all(checks.values()),'checks':checks,
        'currentProductMatchesFrozen':module_sources_match(report,ROOT/'dingtalk_bridge'),
        'currentCheckerMatchesPreparedPlan':digest((ROOT/'scripts/check_dws_recovery_once.py').read_bytes())==plan['checkerSha256'],
        'testsPerSuite':244,'newMethods':7,'productReusedFrom':'E073','deployed':False,
        'realReadExecuted':False,'realDwsCalls':0,'newNativeUITest':False,'liveCredentialFailureResolved':False,
        'wheelSha256':report['wheelSha256'],'codeSha256':report['codeSha256'],'checkerSha256':report['checkerSha256'],
        'frozenTestSha256':{n:digest((folder/'installed-suite/tests'/n).read_bytes()) for n in ('test_recovery_once.py','test_history_recovery_mode.py')},
        'logSha256':{n:digest((folder/n).read_bytes()) for n in ('source-tests.log','source-final-tests.log','py314-tests.log','py311-tests.log')},
        'limits':['Synthetic two-route HTTP history receive/send/replay/circuit test; event CLI invocation count is zero',
            'Prepared real query requires separate explicit permission; no background restart is included',
            'Only one invocation per prepared key, even after timeout/checker death; never change keys to retry an unknown attempt',
            'Configuration, executable, full package, checker and DWS environment are bound to preparation',
            'Request budget is 15 seconds plus up to 15 seconds for supervisor cleanup; a system auth prompt remains possible',
            'Read success is not proof of complete login recovery, UI delivery or 24-hour stability',
            'Original live config remains unchanged; history-only background recovery is a later explicit step']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-evidence',action='store_true')
    args=parser.parse_args();result=audit()
    if args.write_evidence:(ROOT/'evidence/2026-11-12/recovery-plan-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 1)

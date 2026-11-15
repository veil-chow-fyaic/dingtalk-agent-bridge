#!/usr/bin/env python3
"""Offline review of a recorded synthetic OpenClaw host probe; never launch a runtime."""
import argparse
import json
from pathlib import Path


def review_guard(root, source):
    """Denied build-info discovery is metadata, not an attempted credential read.

    Keep denying the filesystem access. Only classify the already-recorded event;
    every other home read or credential command remains a failed isolation check.
    """
    path = root / 'guard-denials.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    metadata = str(source.parent / 'build-info.json')
    rejected = [event for event in events if not (
        event.get('kind') == 'login-shell' and event.get('target') == '/bin/sh'
        or event.get('kind') == 'ambient-home-read' and event.get('target') == metadata
    )]
    return {'ok': not rejected, 'deniedLoginShellProbes': sum(e.get('kind') == 'login-shell' for e in events),
            'deniedBuildMetadataReads': sum(e.get('kind') == 'ambient-home-read' and e.get('target') == metadata for e in events),
            'unexpectedDenials': len(rejected)}


def review(root, source):
    data = json.loads((root / 'result.json').read_text())
    cases = {item['case']: item for item in data['results']}
    expected = {'first': 0, 'resume': 0, 'tool': 0, 'isolated': 0, 'contender': 1,
                'cancel': 130, 'deadline': 1, 'length': 0, 'missing': 0}
    checks = {k: v is True for k, v in data['checks'].items()
              if k != 'no_ambient_credential_access_attempt'}
    checks['exact_case_inventory_and_exits'] = set(cases) == set(expected) and len(cases) == len(data['results']) and all(
        cases[k]['exitCode'] == v and cases[k]['forcedCleanup'] is False for k, v in expected.items())
    checks['native_tool_settlement_and_observation'] = all(
        cases[k].get('aliveAtCliExit') == [] and cases[k].get('observedSecondsAfterToolStart', 0) >= seconds
        and not (root / 'workspace' / (k + '-late.txt')).exists()
        for k, seconds in [('cancel', 28), ('deadline', 13)])
    # Require the full frozen driver check inventory, not a hand-picked successful subset.
    required = {'first_success', 'resume_success', 'tool_success', 'resume_contains_prior_user_and_assistant',
                'python_artifact_value', 'tool_record_confirms_one_success',
                'same_uuid_distinct_state_has_no_prior_history', 'exclusive_state_rejects_second_cli',
                'deadline_reports_unknown_tool_outcome', 'explicit_direct_fixture_auth',
                'no_external_profile_directory_created', 'length_is_explicit_partial_not_full_success'}
    checks['required_checks_present'] = required <= set(data['checks'])
    guard = review_guard(root, source)
    checks['credential_boundaries_preserved'] = guard['ok']
    return {'ok': all(checks.values()), 'cases': len(cases), 'checks': checks, 'guard': guard,
            'originalGuardAggregate': data['checks'].get('no_ambient_credential_access_attempt'),
            'originalFailureRecordPreserved': (root / 'failure.json').exists()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    result = review(args.run_dir.resolve(), args.source_root.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(not result['ok'])

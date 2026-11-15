#!/usr/bin/env python3
"""Audit captured E131 ingress and failed execution; never send or retry a task."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'local/group-multi-image-20261115'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(folder=PRIVATE):
    data = {n: json.loads((folder / (n + '.json')).read_text())
            for n in ('intent', 'before', 'final', 'case', 'ui-observations')}
    names = list(data['ui-observations']['frames']) + ['run/events.jsonl', 'run/stderr.log']
    for i, item in enumerate(data['intent']['fixtures']):
        names += ['input/' + item['name'], f'captured/cache-{i}.png', f'captured/staged-{i}.png']
    data['files'] = {n: (folder / n).read_bytes() for n in names}
    return data


def validate(data):
    intent, before, final, case = (data[k] for k in ('intent', 'before', 'final', 'case'))
    files, ui = data['files'], data['ui-observations']
    job = case['job']
    model = json.loads(job['model'])
    old_group, group = (x['routes']['0'] for x in (before, final))
    jobs = [j for j in group['tasks']['jobs'] if j['id'] not in {x['id'] for x in old_group['tasks']['jobs']}]
    checks = {
        'one_native_attempt': intent['nativeAttempts'] == 1,
        'one_new_failed_job': jobs == [job] and job['state'] == 'failed' and
            job['error'] == 'runtime_terminal_missing' and job['result'] is None,
        'group_input_not_self': model['conversationType'] == 'group' and model['fromSelf'] is False,
        'one_text_two_images_no_issues': [p['type'] for p in model['parts']] == ['text', 'image', 'image'] and not model['issues'],
        'prompt_exact_and_no_answer_leak': model['parts'][0]['text'].strip() == intent['prompt'] and
            job['command'] == intent['prompt'].removeprefix('/agent ') and
            all(str(x['value']) not in job['command'] for x in intent['fixtures']),
        'two_distinct_originals': len(intent['fixtures']) == 2 and len({x['sha256'] for x in intent['fixtures']}) == 2,
    }
    media = [p for p in model['parts'] if p['type'] == 'image']
    for i, item in enumerate(intent['fixtures']):
        original = files['input/' + item['name']]
        part = media[i] if i < len(media) else {}
        checks[f'image_{i}_original_cache_staged_exact'] = (
            sha(original) == item['sha256'] == part.get('sha256') and
            len(original) == item['bytes'] == part.get('sizeBytes') and
            original == files[f'captured/cache-{i}.png'] == files[f'captured/staged-{i}.png'])
    events = {e['message_id']: e for e in case['events']}
    source = events.get(model['id'], {})
    checks['native_source_same_route_and_sender'] = (
        source.get('from_self') is False and source.get('account_id') == model['accountId'] and
        source.get('conversation_id') == model['conversationId'] and source.get('sender_id') == model['senderId'])
    for route in ('0', '1'):
        old, end = (x['routes'][route] for x in (before, final))
        checks[f'route_{route}_old_jobs_outbox_preserved'] = all(
            row in end['tasks'][table] for table in ('jobs', 'outbox') for row in old['tasks'][table])
        checks[f'route_{route}_session_unchanged'] = old['tasks']['meta'] == end['tasks']['meta']
        checks[f'route_{route}_old_transport_preserved'] = all(
            row in end['bridge'][table] for table in ('events', 'deliveries', 'rejection_audit', 'image_uploads')
            for row in old['bridge'][table])
        checks[f'route_{route}_old_inbox_preserved'] = all(row in end['inbox']['inbox'] for row in old['inbox']['inbox'])
    checks['direct_route_no_new_jobs_or_messages'] = all(
        before['routes']['1'][db][table] == final['routes']['1'][db][table]
        for db, table in (('tasks', 'jobs'), ('tasks', 'outbox'), ('bridge', 'events'), ('bridge', 'deliveries'), ('inbox', 'inbox')))
    outbox = [r for r in group['tasks']['outbox'] if r['key'] not in {x['key'] for x in old_group['tasks']['outbox']}]
    checks['only_ack_and_error_confirmed'] = outbox == case['outbox'] and len(outbox) == 2 and all(
        o['job_id'] == job['id'] and o['state'] == 'confirmed' and not o['error'] and
        set(json.loads(o['payload'])) == {'text'} for o in outbox) and any(
            '未交付结果文件' in json.loads(o['payload'])['text'] for o in outbox)
    deliveries = [d for d in group['bridge']['deliveries'] if d['key'] not in {x['key'] for x in old_group['bridge']['deliveries']}]
    checks['two_confirmed_transport_deliveries'] = deliveries == case['deliveries'] and len(deliveries) == 2 and all(
        d['state'] == 'confirmed' and not d['error'] for d in deliveries)
    checks['outbox_receipts_match_delivery'] = all(
        json.loads(o['receipt']) == {k: d[k] for k in json.loads(o['receipt'])}
        for o in outbox for d in deliveries if o['key'] == d['key']) and {o['key'] for o in outbox} == {d['key'] for d in deliveries}
    new_events = [json.loads(e['body']) for e in group['bridge']['events'] if e['message_id'] not in {x['message_id'] for x in old_group['bridge']['events']}]
    checks['input_and_two_replies_history_exact'] = len(events) == len(new_events) == 3 and {
        e['message_id']: e for e in new_events} == events and all(
            events.get(d['message_id'], {}).get('from_self') is True for d in deliveries)
    inbox = [r for r in group['inbox']['inbox'] if r['message_id'] in events]
    checks['all_events_normalized_without_error'] = len(inbox) == 3 and all(
        not r['error'] and r['state'] == 'normalized' for r in inbox)
    stdout = [json.loads(s) for s in files['run/events.jsonl'].decode().splitlines()]
    stderr = files['run/stderr.log'].decode()
    checks['runtime_only_version_no_tools_or_completion'] = stdout == [{'role': 'meta', 'type': 'system.version', 'version': '2.1.1'}]
    checks['provider_403_subscription_denial_captured'] = all(s in stderr for s in (
        'provider.auth_error: 403', 'Your current subscription does not have access to Kimi Code right now.'))
    guard = [json.loads(s) for s in stderr.splitlines() if s.startswith('{')]
    checks['owned_cli_cleanup_reported'] = len(guard) == 1 and guard[0]['runtime_guard'] == 'cli_exit' and guard[0]['cleanup_complete'] is True
    checks['no_result_export'] = case['exportExists'] is False
    checks['owned_services_unchanged'] = before['manager'] == final['manager'] and final['manager']['all_running']
    checks['transport_ready_and_sync_complete'] = before['access'] == final['access'] == {'state': 'ready'} and all(
        r.get('last_sync', {}).get('complete') is True and not r.get('poll_error') for r in final['health']['routes'])
    checks['native_frames_frozen'] = len(ui['frames']) == 10 and all(sha(files[n]) == h for n, h in ui['frames'].items())
    checks['visual_group_input_failure_reviewed'] = all(ui[k] is True for k in (
        'groupAndTwoMembersVisible', 'nativeSingleMessageTwoImages', 'failureNoticeAndAIBadgeVisible'))
    checks['draft_sent_two_images_and_failure_ax'] = all(
        files[n].decode().count('[附带的图像]') >= 2 for n in ('draft.ax.txt', 'sent.ax.txt')) and '未交付结果文件' in files['failure.ax.txt'].decode()
    return checks


def audit():
    data = load()
    checks = validate(data)
    return {'schemaVersion': 1, 'evidence': 'E131', 'date': '2026-11-15',
            'auditPassed': all(checks.values()), 'taskSucceeded': False, 'checks': checks,
            'nativeInputs': 1, 'newJobs': 1, 'totalJobs': 99, 'confirmedReplies': 2,
            'matrixChange': 'group inbound multi-attachment: blocked to partial (two PNG ingress only)',
            'runtimeFailure': 'runtime_terminal_missing; captured Kimi provider.auth_error 403 subscription denial',
            'requiredNewEvidence': 'Authorized Kimi Code service access restored before another model task; no retry/auth repair/token copying',
            'privateEvidence': 'local/group-multi-image-20261115',
            'limitations': ['No model image understanding, Python calculation, result or client-download pass',
                'One native message with two PNG images only, not arbitrary file bundles',
                'Cleanup is the owned CLI group report, not independent detached-process verification',
                'No product/deployment/runtime migration; six databases read separately, not one common atomic snapshot']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.write:
        (ROOT / 'evidence/2026-11-15/group-multi-image-failure-validation.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['auditPassed'] else 1)

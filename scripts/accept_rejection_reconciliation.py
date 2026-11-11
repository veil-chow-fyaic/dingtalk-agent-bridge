#!/usr/bin/env python3
"""Read-only proof of audited rejection, no replay, and real UI feedback."""
import argparse
import json

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from accept_long_text_ui import preserved_or_rejected
from dingtalk_bridge.rejection import read_length_rejection
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/rejection-reconciliation-20261111'
    before, final, cases, intent = (read(folder / name) for name in
        ('before-ledgers.json', 'final-ledgers.json', 'cases.json', 'reconciliation-intent.json'))
    if set(cases) != {'status', 'warning'}:
        return {'ok': False, 'error': 'incomplete_ui_case_coverage'}
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        deliveries = {r['key']: r for r in rows(transport, 'deliveries')}
        audits = {r['key']: r for r in rows(transport, 'rejection_audit')}
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'),
                                    ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved_or_audited_rejection'] = bool(old[table]) and all(
                preserved_or_rejected(current.get(r[identity]), r, table, deliveries, audits) for r in old[table])
        checks[kind + '_native_binding_preserved'] = old['meta'] == end['meta']
        checks[kind + '_no_runtime_execution'] = bool(end['runtimeFiles']) and all(
            (ROOT / name).is_file() and digest((ROOT / name).read_bytes()) == item['sha256'] and
            item['mtime'] < before['at'] for name, item in end['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged_during_experiment'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'deliveries'))
        else:
            direct_cfg = cfg
            direct_audits, direct_deliveries = audits, deliveries
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    key = intent['key']
    record = direct_audits.get(key)
    checks['one_expected_audit_record'] = bool(record) and len(final['routes']['direct']['rejection_audit']) == 1
    if not record:
        return {'checks': checks, 'ok': False}
    original = json.loads(record['before_json'])
    checks['exact_original_unknown_snapshot_preserved'] = original == intent['expectedBefore'] and original['state'] == 'outcome_unknown'
    raw, sha = read_length_rejection(ROOT, intent['evidencePath'], original, direct_cfg)
    checks['official_key_target_execution_and_length_proof'] = sha == record['evidence_sha256'] == intent['evidenceSha256']
    checks['entire_source_evidence_stored_unchanged'] = raw.decode() == record['evidence_json']
    checks['explicit_recorded_terminal_rejection'] = record['source'] == 'official_cli_log' and record['recorded_at'] >= intent['at']
    checks['only_state_changed_to_rejected'] = direct_deliveries[key] == {**original, 'state': 'rejected', 'error': 'PARAM_ERROR'}
    receipt = read(folder / 'reconcile-result.json')['receipt']
    checks['receipt_bound_to_audit'] = receipt['key'] == key and receipt['state'] == 'rejected' and receipt['rejection']['evidence_sha256'] == sha
    checks['original_text_not_present_in_history'] = not any(e['content'] == json.loads(original['payload'])['text'] for e in events.values())
    count = read(folder / 'official-send-count.json')
    checks['original_official_send_observed_once'] = count['originalKeyRequestCount'] == len(count['matches']) == 1 and (
        json.loads(count['matches'][0]['arguments_summary'])['uuid'] == key)
    by_id, by_key = {j['id']: j for j in jobs}, {o['key']: o for o in outbox}
    status, warning = cases['status'], cases['warning']
    checks['new_status_completed'] = status['job']['command'] == 'status' and status['job']['state'] == 'completed' and by_id.get(status['job']['id']) == status['job']
    event = status['event']
    checks['authorized_native_status_input'] = events.get(event['message_id']) == event and event['content'] == '/agent status' and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    for name, case in cases.items():
        reply, out = case['reply'], case['outbox']
        checks[name + '_reply_confirmed_unchanged'] = out['state'] == 'confirmed' and by_key.get(out['key']) == out
        checks[name + '_reply_bound_to_liev'] = events.get(reply['message_id']) == reply and reply['from_self'] is True and reply['sender_id'] == direct_cfg['selfSenderId']
        checks[name + '_no_reply_echo_task'] = not any(json.loads(j['model'])['id'] == reply['message_id'] for j in jobs)
    checks['status_shows_terminal_rejection_not_unknown'] = all(x in status['reply']['content'] for x in ('执行中 0，排队 0', '结果未确认 0', '已拒绝 1', '投递失败 0'))
    checks['warning_is_about_original_job'] = warning['outbox']['job_id'] == by_key[key]['job_id'] and warning['outbox']['key'].endswith('-delivery-issue')
    checks['one_durable_warning_only'] = sum(o['job_id'] == warning['outbox']['job_id'] and o['key'].endswith('-delivery-issue') for o in outbox) == 1
    checks['visible_warning_content'] = all(x in warning['reply']['content'] for x in ('部分回复未送达', '已保留任务结果', '不会自动重发失败内容'))
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_one_new_control_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {status['job']['id']}
    checks['exact_two_new_notifications'] = {o['key'] for o in end['outbox']} - {o['key'] for o in old['outbox']} == {c['outbox']['key'] for c in cases.values()}
    return {'date': '2026-11-11', 'checks': checks, 'originalResent': False,
            'newControlTasks': 1, 'newConfirmedReplies': 2, 'newRuntimeExecutions': 0,
            'limits': ['Explicit operator-supplied local log import; not automatic inference from PARAM_ERROR alone',
                       'Legacy log reconciliation supports only this bound personal-text length rejection shape',
                       'Rejection is terminal failure, not successful delivery or retry approval',
                       'No group messages sent'], 'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/rejection-reconciliation-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

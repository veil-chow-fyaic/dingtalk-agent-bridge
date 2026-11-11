#!/usr/bin/env python3
"""Read-only native direct quote acceptance; never sends or restarts anything."""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder = ROOT / 'local/quote-bridge-20261112'
    before, deployed, final, intent, receipt, event, ui = (read(folder / n) for n in
        ('before.json', 'deployed.json', 'final.json', 'intent.json', 'receipt.json', 'reply-event.json', 'ui-observations.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        db = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, path, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', db, 'key')]:
            current = {r[identity]: r for r in rows(path, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_runtime_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        checks[kind + '_deployment_no_replay'] = all(old[t] == deployed['routes'][kind][t] for t in ('jobs', 'outbox', 'deliveries', 'events'))
        checks[kind + '_no_new_tasks_or_outbox'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta'))
        if kind == 'group':
            checks['group_no_messages'] = all(old[t] == end[t] for t in ('events', 'deliveries'))
        else:
            direct_cfg = cfg
            delivery = next(r for r in final['routes']['direct']['deliveries'] if r['key'] == receipt['key'])
            checks['receipt_immutable'] = delivery in rows(db, 'deliveries') and all(delivery[k] == v for k, v in receipt.items())
            checks['event_immutable'] = any(json.loads(r['body']) == event for r in rows(db, 'events'))
    source, quote = intent['source'], event['raw']['quotedMessage']
    checks['source_bound_to_route'] = source['message_id'] == intent['reply_to'] and source['account_id'] == direct_cfg['accountId'] and source['conversation_id'] == direct_cfg['group'] and source['from_self'] is False
    checks['source_is_original_multi_image_input'] = source == read(ROOT / 'local/multi-image-ui-20261112/case.json')['event']
    checks['single_http_send_attempt'] = read(folder / 'send-attempt.json')['attempts'] == 1
    checks['confirmed_delivery_and_fingerprint'] = receipt['key'] == intent['idempotency_key'] and receipt['state'] == 'confirmed' and bool(receipt['task_id']) and receipt['message_id'] == event['message_id'] and json.loads(delivery['payload']) == {'kind': 'text', 'text': intent['text'], 'reply_to': intent['reply_to']} and delivery['fingerprint'] == digest(delivery['payload'].encode())
    checks['quote_source_identity_and_content'] = quote['messageId'] == intent['reply_to'] and quote['conversationId'] == source['conversation_id'] and quote['text'] == source['content'] and quote['resourceRefs'] == source['attachments']
    checks['reply_identity_content'] = event['from_self'] is True and event['sender_id'] == direct_cfg['selfSenderId'] and event['content'] == intent['text']
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_one_new_delivery'] = {r['key'] for r in end['deliveries']} - {r['key'] for r in old['deliveries']} == {intent['idempotency_key']}
    checks['exact_one_new_event'] = {r['message_id'] for r in end['events']} - {r['message_id'] for r in old['events']} == {event['message_id']}
    dry = read(folder / 'dry-run.json'); dry = dry.get('data', dry)
    checks['official_dry_run_bound_no_write'] = dry['dryRun'] is True and dry['willSend'] is False and dry['conversationId'] == direct_cfg['group'] and dry['mode'] == 'quote' and dry['transport'] == 'chat/send_personal_message'
    ax = (folder / 'received.ax.txt').read_text()
    checks['native_quote_body_source_and_ai_badge'] = intent['text'] in ax and read(ROOT / 'local/multi-image-ui-20261112/intent.json')['prompt'] in ax and '通过AI发送' in ax and ax.count('[图片]') >= 2
    checks['reviewed_ui_frame_preserved'] = all(ui[k] is True for k in ('replyBubbleViewed', 'quotedSourceViewed', 'lievSenderViewed', 'aiBadgeViewed')) and digest((folder / 'received.png').read_bytes()) == ui['receivedPngSha256'] and digest(ax.encode()) == ui['receivedAxSha256']
    checks['jump_failure_not_claimed_pass'] = ui['sourceJumpPassed'] is False and 'cannotClickOffscreenElement' in ui['sourceJumpError']
    checks['stop_guard_failure_retained'] = read(folder / 'manager-stop.json')['ok'] is False and 'PID changed' in read(folder / 'manager-stop.json')['error'] and all(c['status'] == 'stopped' for c in read(folder / 'post-stop-status.json')['components'])
    checks['restart_and_doctor_passed'] = read(folder / 'manager-start.json')['all_running'] is True and read(folder / 'doctor.json')['ok'] is True
    checks['original_observer_not_reset'] = all(before['observer'][k] == final['observer'][k] for k in ('pid', 'startedAt', 'duration_seconds')) and final['observer']['samples'] > before['observer']['samples']
    return {'date': '2026-11-12', 'checks': checks, 'confirmedQuoteReplies': 1, 'newRuntimeJobs': 0,
            'limits': ['Direct outbound text quote only; inbound and group quote not UI verified',
                       'Quoted source visible; AX jump to source failed and was not retried',
                       'Stop guard reported PID change; all old processes independently found stopped, then normal start succeeded',
                       '24h observer continues; planned deployment outage retained'], 'ok': all(checks.values())}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true'); args = p.parse_args()
    result = audit()
    if args.write:
        (ROOT / 'evidence/2026-11-12/quote-reply-ui-ledger.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

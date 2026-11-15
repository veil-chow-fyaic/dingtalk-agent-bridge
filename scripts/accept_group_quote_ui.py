#!/usr/bin/env python3
"""Audit captured group quote UI/ledger evidence; never send or contact services."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'local/group-quote-20261115'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(folder):
    names = ('intent', 'before', 'final', 'preflight', 'source-event',
             'reply-event', 'native-reply-event', 'receipt', 'send-attempt',
             'ui-observations')
    data = {n: json.loads((folder / (n + '.json')).read_text()) for n in names}
    data['ui_files'] = {p.name: p.read_bytes() for p in folder.iterdir()
                        if p.suffix == '.png' or p.name.endswith('.ax.txt')}
    return data


def validate(data):
    intent, before, final = (data[n] for n in ('intent', 'before', 'final'))
    source, reply, inbound = (data[n] for n in
                              ('source-event', 'reply-event', 'native-reply-event'))
    receipt, attempt, ui = (data[n] for n in ('receipt', 'send-attempt', 'ui-observations'))
    checks = {}
    checks['single_attempt_per_new_message'] = all(intent[k] == 1 for k in
        ('source_ui_attempts', 'http_send_attempts', 'native_reply_attempts')) and attempt['attempts'] == 1
    expected_payload = {k: intent[k] for k in
                        ('account_id', 'conversation_id', 'idempotency_key', 'reply_to')}
    expected_payload['text'] = intent['reply_text']
    checks['exact_http_request'] = attempt['payload'] == expected_payload
    checks['three_distinct_messages'] = len({e['message_id'] for e in (source, reply, inbound)}) == 3
    checks['all_messages_same_group_route'] = all(
        e['account_id'] == intent['account_id'] and
        e['conversation_id'] == intent['conversation_id'] and
        e['conversation_type'] == 'group' for e in (source, reply, inbound))
    checks['source_native_text_exact'] = source['content'] == intent['source_text'] and source['from_self'] is False
    checks['outbound_sender_and_body'] = reply['from_self'] is True and bool(reply['sender_id']) and intent['reply_text'] in reply['content']
    checks['native_reply_sender_and_body'] = inbound['from_self'] is False and inbound['sender_id'] == source['sender_id'] and intent['native_reply_text'] in inbound['content']
    for label, event, target in (('outbound', reply, source), ('inbound', inbound, reply)):
        quote = event['raw'].get('quotedMessage', {})
        checks[label + '_quote_identity_and_text'] = (
            quote.get('messageId') == target['message_id'] and
            quote.get('conversationId') == target['conversation_id'] and
            quote.get('sender') == target['sender'] and
            quote.get('text') == target['content'])
    checks['confirmed_exact_receipt'] = (
        receipt['key'] == intent['idempotency_key'] and receipt['state'] == 'confirmed' and
        bool(receipt['task_id']) and receipt['message_id'] == reply['message_id'] and not receipt['error'])
    old_group, group = (x['routes']['0'] for x in (before, final))
    deliveries = group['bridge']['deliveries']
    added = [d for d in deliveries if d['key'] not in {x['key'] for x in old_group['bridge']['deliveries']}]
    checks['only_one_new_transport_delivery'] = len(added) == 1 and added[0]['key'] == intent['idempotency_key']
    delivery = added[0] if len(added) == 1 else {}
    payload = {'kind': 'text', 'text': intent['reply_text'], 'reply_to': source['message_id']}
    checks['delivery_payload_fingerprint_receipt'] = bool(delivery) and (
        json.loads(delivery['payload']) == payload and
        delivery['fingerprint'] == digest(delivery['payload'].encode()) and
        all(delivery.get(k) == v for k, v in receipt.items()))
    new_events = [r for r in group['bridge']['events'] if r['message_id'] not in
                  {x['message_id'] for x in old_group['bridge']['events']}]
    checks['exact_three_new_history_events'] = len(new_events) == 3 and {
        r['message_id']: json.loads(r['body']) for r in new_events
    } == {e['message_id']: e for e in (source, reply, inbound)}
    for route in ('0', '1'):
        old, end = (x['routes'][route] for x in (before, final))
        checks['route_' + route + '_all_jobs_outbox_session_unchanged'] = old['tasks'] == end['tasks']
        checks['route_' + route + '_old_transport_rows_preserved'] = all(
            row in end['bridge'][table] for table in ('events', 'deliveries', 'rejection_audit', 'image_uploads')
            for row in old['bridge'][table])
        checks['route_' + route + '_old_inbox_preserved'] = all(row in end['inbox']['inbox'] for row in old['inbox']['inbox'])
    checks['direct_route_no_new_events_or_deliveries'] = all(
        before['routes']['1']['bridge'][t] == final['routes']['1']['bridge'][t] for t in ('events', 'deliveries'))
    consumed = [r for r in group['inbox']['inbox'] if r['message_id'] in {e['message_id'] for e in (source, reply, inbound)}]
    cursor = int(next(r['value'] for r in group['inbox']['meta'] if r['key'] == 'cursor'))
    checks['all_three_events_normalized_and_cursor_covered'] = len(consumed) == 3 and all(
        r['state'] == 'normalized' and not r['error'] and r['seq'] <= cursor for r in consumed)
    for label, event, target in (('outbound', reply, source), ('inbound', inbound, reply)):
        model = next((json.loads(r['model']) for r in consumed if r['message_id'] == event['message_id']), {})
        quote = model.get('quote', {})
        checks[label + '_normalized_quote_preserved'] = (
            quote.get('id') == target['message_id'] and
            quote.get('conversationId') == target['conversation_id'] and
            quote.get('senderName') == target['sender'] and
            not quote.get('senderId') and
            quote.get('parts') == [{'type': 'text', 'text': target['content']}] and not quote.get('issues'))
    checks['no_unknown_delivery'] = all(d['state'] in ('confirmed', 'failed', 'rejected')
        for route in final['routes'].values() for d in route['bridge']['deliveries'])
    checks['owned_services_unchanged'] = data['preflight']['manager'] == final['manager'] and final['manager']['all_running']
    checks['dws_ready_at_both_snapshots'] = data['preflight']['access'] == final['access'] == {'state': 'ready'}
    checks['both_routes_sync_complete_at_end'] = len(final['health']['routes']) == 2 and all(
        r.get('last_sync', {}).get('complete') is True and not r.get('poll_error') for r in final['health']['routes'])
    checks['reviewed_native_frames_preserved'] = all(
        digest(data['ui_files'].get(name, b'')) == sha for name, sha in ui['files'].items()) and len(ui['files']) == 10
    checks['native_visual_observations_recorded'] = all(ui[k] is True for k in (
        'authorizedGroupAndTwoMembersVisible', 'outboundSourceAndSenderVisible',
        'outboundReplyAndAIBadgeVisible', 'explicitReplyEntryOpened',
        'nativeReplyDraftQuoteVisible', 'nativeReplySentQuoteVisible'))
    for name, texts in {
        'source-sent.ax.txt': [intent['source_text']],
        'reply-received.ax.txt': [intent['source_text'], intent['reply_text'], '通过AI发送'],
        'native-reply-draft.ax.txt': [intent['reply_text'], intent['native_reply_text']],
        'native-reply-sent.ax.txt': [intent['reply_text'], intent['native_reply_text']],
    }.items():
        ax = data['ui_files'][name].decode()
        checks[name + '_content_present'] = all(t in ax for t in texts)
    return checks


def audit(folder=PRIVATE):
    data = load(folder)
    checks = validate(data)
    return {'schemaVersion': 1, 'evidence': 'E130', 'date': '2026-11-15',
            'ok': all(checks.values()), 'checks': checks,
            'newMatrixCells': ['group_outbound_quote', 'group_inbound_quote'],
            'newNativeInputs': 2, 'newBridgeSends': 1, 'newRuntimeJobs': 0,
            'totalJobsPreserved': sum(len(r['tasks']['jobs']) for r in data['before']['routes'].values()),
            'privateEvidence': 'local/group-quote-20261115',
            'limitations': ['AIC group only; direct inbound quote remains unverified',
                'Visual mention renders a name while AX uses [unknown]; raw history retains native mention text',
                'Official quotedMessage supplies sender name but no sender ID in these samples; normalized senderId stays empty',
                'No jump-to-source, receipt-read status, arbitrary nested quote or attachment combination claim',
                'Per-database read transactions are not a common six-database cutoff snapshot',
                'No product change/deployment/runtime execution, natural refresh or long-term health claim']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.write:
        (ROOT / 'evidence/2026-11-15/group-quote-ui-validation.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

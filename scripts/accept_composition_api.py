#!/usr/bin/env python3
"""Read saved E134 API/deployment evidence; never send, hydrate an inbox or run a model."""
import argparse
import copy
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'local/composition-api-20261116'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('invalid_saved_snapshot')
        return {t[0]: [dict(r) for r in db.execute('SELECT * FROM ' + t[0] + ' ORDER BY rowid')]
                for t in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def load(folder=PRIVATE):
    names = ('preflight', 'baseline', 'stop-planner-refusal', 'stopped', 'history-attempt',
             'history-result', 'backlog-audit', 'started', 'final', 'ui-observation')
    data = {name: json.loads((folder / (name + '.json')).read_text()) for name in names}
    data['cases'] = {}
    data['files'] = {}
    data['covered'] = []
    data['snapshots'] = []
    for i, kind in enumerate(('group', 'direct')):
        data['cases'][kind] = {n: json.loads((folder / (kind + '-' + n + '.json')).read_text())
                              for n in ('prepared', 'send-intent', 'send-result', 'event', 'model',
                                        'download-intent', 'download-result', 'hydrated')}
        data['covered'].append(snapshot(folder / 'covered-backlog-review' / f'{i}-bridge.sqlite3'))
        data['snapshots'].append({n: snapshot(folder / 'final-snapshots' / f'{i}-{n}.sqlite3')
                                  for n in ('bridge', 'tasks', 'inbox')})
        for position in range(2):
            for label in ('original', 'staged', 'download'):
                name = f'{kind}-{position}-{label}.png'
                data['files'][name] = (folder / 'captured' / name).read_bytes()
    data['validated'] = json.loads((ROOT / 'evidence/2026-11-16/outbound-composition-validation.json').read_text())
    return data


def validate(data):
    before, final, start = (data[n] for n in ('baseline', 'final', 'started'))
    refusal = data['stop-planner-refusal']
    checks = {
        'validated_product_deployed': start['ok'] and start['productCommit'] == '2467fe2' and
            start['codeSha256'] == before['codeSha256'] == final['codeSha256'] == data['validated']['codeSha256'],
        'configs_and_runtime_binding_not_changed': start['configSha256'] == before['configSha256'] == final['configSha256'] and
            start['runtimeChange'] is False and start['bindingChange'] is False,
        'original_planner_refusal_preserved': refusal['error'] == 'sqlite_sidecar_requires_separate_review' and
            refusal['noDatabaseDeletion'] and not refusal['services']['all_running'],
        'separate_stopped_review_and_backlog_passed': data['stopped']['ok'] and data['backlog-audit']['ok'] and
            all(data['stopped']['checks'].values()) and all(data['backlog-audit']['checks'].values()),
        'history_phase_single_attempt': data['history-attempt']['attempts'] == 1 and data['history-result']['ok'] and
            not data['history-result']['manager']['all_running'],
        'started_services_still_owned_and_running': start['status'] == final['manager'] and final['manager']['all_running'],
        'transport_ready_without_poll_error_at_capture': final['access'] == {'state': 'ready'} and all(
            not r.get('poll_error') and r.get('last_sync', {}).get('complete') for r in final['health']['routes']),
        'ui_failed_no_ui_pass_claim': data['ui-observation']['error'] == 'failedToCreateImageDestination' and
            data['ui-observation']['snapshotObtained'] is False and data['ui-observation']['stoppedSamePath'] is True,
    }
    for i, kind in enumerate(('group', 'direct')):
        old, end = before['routes'][i], final['routes'][i]
        case = data['cases'][kind]
        request = case['prepared']['request']
        receipt = case['send-result']['body']
        event, model, hydrated = (case[k] for k in ('event', 'model', 'hydrated'))
        new_deliveries = [d for d in end['data']['bridge']['deliveries']
                          if d['key'] not in {r['key'] for r in old['data']['bridge']['deliveries']}]
        delivery = new_deliveries[0] if len(new_deliveries) == 1 else {}
        payload = json.loads(delivery.get('payload', '{}'))
        new_events = [r for r in end['data']['bridge']['events']
                      if r['message_id'] not in {e['message_id'] for e in old['data']['bridge']['events']}]
        inbox = [r for r in end['data']['inbox']['inbox'] if r['message_id'] == event['message_id']]
        ledger = case['download-result']['body']
        images = [p for p in hydrated['parts'] if p['type'] == 'image']
        refs = {(d['resourceType'], d['resourceId']): d for d in ledger['downloads']}
        meta = {r['key']: r['value'] for r in data['covered'][i]['meta']}
        checks.update({
            kind + '_fixed_cut_same_saved_sqlite': 'history_window' not in meta and
                datetime.fromisoformat(meta['watermark']) >= datetime.fromisoformat(data['history-attempt']['cut']),
            kind + '_final_matches_saved_sqlite': end['data'] == data['snapshots'][i],
            kind + '_tasks_sessions_bindings_outbox_exact': old['data']['tasks'] == end['data']['tasks'],
            kind + '_old_transport_and_inbox_kept': all(
                r in end['data'][db][table] for db, table in (('bridge', 'events'), ('bridge', 'deliveries'),
                ('bridge', 'image_uploads'), ('bridge', 'rejection_audit'), ('inbox', 'inbox')) for r in old['data'][db][table]),
            kind + '_one_send_intent': case['send-intent']['attempts'] == 1 and case['send-intent']['request'] == request,
            kind + '_one_confirmed_delivery': len(new_deliveries) == 1 and case['send-result']['status'] == 200 and
                receipt['state'] == delivery.get('state') == 'confirmed' and request['idempotency_key'] == delivery.get('key') and
                all(receipt.get(k) == delivery.get(k) for k in ('key', 'task_id', 'message_id', 'error')) and not delivery.get('error'),
            kind + '_one_history_message_exact_route_self': len(new_events) == 1 and
                {'seq': new_events[0]['seq'], **json.loads(new_events[0]['body'])} == event and
                event['message_id'] == receipt['message_id'] == model['id'] == hydrated['id'] and
                event['account_id'] == request['account_id'] == old['route']['accountId'] and
                event['conversation_id'] == request['conversation_id'] == old['route']['group'] and
                event['from_self'] is model['fromSelf'] is hydrated['fromSelf'] is True,
            kind + '_text_and_ordered_two_images': [p['type'] for p in model['parts']] == ['text', 'image', 'image'] and
                not model['issues'] and model['parts'][0]['text'].strip() == request['composition']['text'] and
                [(p['type'], p.get('resource')) for p in model['parts']] == [(p['type'], p.get('resource')) for p in hydrated['parts']],
            kind + '_consumer_self_pending_not_runtime_ready': len(inbox) == 1 and inbox[0]['state'] == 'pending_media' and
                not inbox[0]['error'] and inbox[0]['attempts'] == 0 and json.loads(inbox[0]['model']) == model,
            kind + '_one_official_complete_download': case['download-intent']['attempts'] == 1 and
                case['download-intent']['messageId'] == event['message_id'] and case['download-result']['status'] == 200 and
                ledger['ok'] is True and ledger.get('partial') is False and ledger.get('failedCount') == 0 and
                len(ledger['downloads']) == len(refs) == len(images) == 2,
            kind + '_composition_payload_and_fingerprint': payload.get('kind') == 'composition' and
                payload.get('text') == request['composition']['text'] and
                len(payload.get('images', [])) == 2 and digest(delivery['payload'].encode()) == delivery['fingerprint'],
        })
        for j, src in enumerate(request['composition']['images']):
            original, staged, downloaded = (data['files'][f'{kind}-{j}-{label}.png']
                                            for label in ('original', 'staged', 'download'))
            part = images[j]
            record = refs.get((part['resource']['type'], part['resource']['resourceId']), {})
            checks[f'{kind}_image_{j}_original_staged_download_exact'] = (
                original == staged == downloaded and digest(original) == src['sha256'] == part.get('sha256') ==
                record.get('sha256') == payload['images'][j]['sha256'] and
                len(original) == case['prepared']['sourceSizes'][j] == part.get('sizeBytes') == record.get('sizeBytes') and
                part.get('path') == str((ROOT / record.get('localPath', '')).resolve()))
    return checks


def negative_checks(data):
    variants = []
    changed = copy.deepcopy(data)
    changed['cases']['group']['send-result']['body']['state'] = 'acked'
    variants.append(('ack_is_not_confirmation', changed, 'group_one_confirmed_delivery'))
    changed = copy.deepcopy(data)
    changed['files']['direct-1-download.png'] += b'changed'
    variants.append(('download_corruption_rejected', changed, 'direct_image_1_original_staged_download_exact'))
    changed = copy.deepcopy(data)
    parts = changed['cases']['group']['hydrated']['parts']
    parts[1], parts[2] = parts[2], parts[1]
    variants.append(('image_order_change_rejected', changed, 'group_text_and_ordered_two_images'))
    changed = copy.deepcopy(data)
    changed['covered'][0]['meta'].append({'key': 'history_window', 'value': '{}'})
    variants.append(('unfinished_history_window_rejected', changed, 'group_fixed_cut_same_saved_sqlite'))
    changed = copy.deepcopy(data)
    changed['final']['routes'][1]['data']['tasks']['meta'].append({'key': 'unexpected_session', 'value': 'changed'})
    variants.append(('session_ledger_change_rejected', changed, 'direct_tasks_sessions_bindings_outbox_exact'))
    return {name: validate(changed)[check] is False for name, changed, check in variants}


def audit():
    data = load()
    checks = validate(data)
    negatives = negative_checks(data)
    return {'schemaVersion': 1, 'evidence': 'E134', 'date': '2026-11-16',
            'auditPassed': all(checks.values()) and all(negatives.values()), 'checks': checks,
            'negativeChecks': negatives, 'deployedProduct': '2467fe2',
            'codeSha256': data['started']['codeSha256'], 'newMessages': 2, 'newDeliveries': 2,
            'originalImages': 4, 'totalJobs': 99, 'totalAgentOutbox': 240, 'newModelTasks': 0,
            'uiValidated': False, 'matrixChanged': False, 'privateEvidence': 'local/composition-api-20261116',
            'limitations': ['API/history/official original downloads only; no native UI, sender badge or client-save verification',
                'Two PNG images per route; not arbitrary files, nine images or native image cards',
                'Self messages remain pending_media in gateway inbox by design; hydrated projection here is offline only',
                'Six final databases were backed up separately, not one cross-database atomic snapshot or long-run cutoff',
                'OpenClaw adapter code included in deployment, but no OpenClaw binding, provider request or UI acceptance',
                'Original sidecar planner refusal retained; separate owner-lock SQLite review used without deleting sidecars',
                'No Kimi request, credential repair or runtime migration; previous provider denial remains unresolved']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.write:
        (ROOT / 'evidence/2026-11-16/composition-api-validation.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['auditPassed'] else 1)

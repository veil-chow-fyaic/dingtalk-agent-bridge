#!/usr/bin/env python3
"""Read-only long-text UI, transport chunking and client-file audit."""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.text_limits import utf16_units


def audit_phase(after=False):
    base = ROOT / 'local/long-text-ui-20261111'
    folder = base / 'postfix' if after else base
    before, final, case = (read(folder / n) for n in
                           ('before-ledgers.json', 'final-ledgers.json', 'case.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        old, end = before['routes'][kind], final['routes'][kind]
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'),
                                    ('outbox', agent / 'tasks.sqlite3', 'key'),
                                    ('deliveries', transport, 'key')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(
                current.get(r[identity]) == r for r in old[table])
        if kind == 'group':
            checks['group_unchanged_during_experiment'] = all(
                old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries'))
        else:
            direct_cfg = cfg
            jobs, replies = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    job, event, out, actual = (case[k] for k in ('job', 'event', 'outbox', 'replyEvents'))
    result = json.loads(job['result'] or '{}')
    response = result.get('response', {}).get('text', '')
    intent = read(folder / 'bounded-input-intent.json')
    large = read(base / 'input-intent.json')
    original = (ROOT / intent['sourceFixture']).read_bytes()
    body = original.decode('utf-8')
    allowed = read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    by_id, by_key = {j['id']: j for j in jobs}, {r['key']: r for r in replies}
    checks.update(
        completed_job_unchanged=job['state'] == 'completed' and by_id.get(job['id']) == job,
        input_full_text_preserved=events.get(event['message_id']) == event and event['content'] == intent['text'],
        authorized_nonself_input=event['from_self'] is False and event['sender_id'] in allowed,
        oversized_paste_not_sent=not any(e['content'] == large['text'] for e in events.values()),
        no_input_projection_issue=not json.loads(job['model']).get('issues'),
        frozen_replies=len(out) == 4 and all(by_key.get(r['key']) == r for r in out),
        bound_confirmed_reply_identity=len(actual) == len(out) and all(
            (e is None and r['state'] != 'confirmed') or (e and events.get(e['message_id']) == e and
            e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId']) for r,e in zip(out,actual)),
        no_reply_echo_task=all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in actual if e),
        runtime_log_preserved=digest((ROOT / case['runLog']).read_bytes()) == case['runLogSha256'],
        computed_summary_correct=all(m in response for m in (str(len(body)), str(len(original)), digest(original))),
        requested_two_full_copies=response.count(body) == 2,
    )
    text_replies = [r for r in out if 'text' in json.loads(r['payload']) and
                    not json.loads(r['payload'])['text'].startswith('[Agent] 已接收任务')]
    chunks = [json.loads(r['payload'])['text'] for r in text_replies]
    checks['two_chunks_reconstruct_runtime_response'] = len(chunks) == 2 and all(
        s.startswith('[Agent] ') for s in chunks) and ''.join(s[8:] for s in chunks) == response
    if after:
        checks['every_reply_confirmed'] = all(r['state'] == 'confirmed' for r in out)
        checks['chunks_within_server_utf16_limit'] = all(utf16_units(c) <= 5120 for c in chunks)
    else:
        checks['original_oversized_failure_preserved'] = (len(chunks) == 2 and len(chunks[0]) == 6008 and
            utf16_units(chunks[0]) == 6220 and text_replies[0]['state'] == 'outcome_unknown' and
            sum(r['state'] == 'confirmed' for r in out) == 3 and
            not json.loads(text_replies[0]['receipt']).get('task_id') and
            not any(e['content'] == chunks[0] for e in events.values()))
        logs = read(base / 'dws-parameter-error-log.json')
        checks['official_server_rejected_length'] = any(e.get('server_error_code') == 'PARAM_ERROR' and
            e.get('reason') == 'invalid_request' and 'cannot greater than 5120 but actual is 6220' in
            e.get('errorMsg', '') for e in logs)
    projections = [(json.loads(r['payload'])['text'], events[json.loads(r['receipt'])['message_id']]['content'])
                   for r in text_replies if r['state'] == 'confirmed']
    # DWS RuntimeContext.Str explicitly TrimSpace's flags. Record the one
    # observed removed final LF; do not hide arbitrary whitespace/data loss.
    checks['history_matches_except_known_terminal_lf_trim'] = bool(projections) and all(
        actual == wanted or (wanted.endswith('\n') and actual == wanted[:-1]) for wanted, actual in projections)
    artifacts = result.get('artifacts', [])
    checks['one_result_file'] = len(artifacts) == 1
    if len(artifacts) == 1:
        artifact = artifacts[0]
        client = folder / Path(artifact['file']).name
        checks['artifact_exact_original'] = (ROOT / artifact['file']).read_bytes() == original and artifact['sha256'] == digest(original)
        checks['client_download_exact_original'] = client.is_file() and client.read_bytes() == original
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['one_new_task_only'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']}
    checks['four_new_replies_only'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in out}
    checks['same_native_session'] = old['meta'] == end['meta'] and bool(old['meta'])
    return {'date': '2026-11-11', 'checks': checks, 'inputCharacters': len(intent['text']),
            'phase': 'fixed' if after else 'original_failure',
            'allTextSendReceiptsConfirmed': after and all(r['state'] == 'confirmed' for r in out),
            'historyProjectionByteExact': all(wanted == actual for wanted, actual in projections),
            'terminalLfTrimCount': sum(wanted != actual for wanted, actual in projections),
            'sourceCharacters': len(body), 'sourceBytes': len(original), 'sourceSha256': digest(original),
            'runtimeResponseCharacters': len(response), 'replyChunkCharacters': list(map(len, chunks)),
            'replyChunkUtf16Units': list(map(utf16_units, chunks)),
            'limits': ['6942-character native paste prompted document conversion and was cancelled',
                       'This is not a measured universal client/API size limit',
                       'Original first chunk was rejected; only confirmed chunks compared with history',
                       'Official CLI trims a terminal LF on the fixed first chunk; file preserves every byte',
                       'Both full chat text bubbles not visually inspected; UI evidence covers inputs and downloaded/opened files',
                       'Direct chat only; no new group send'], 'ok': all(checks.values())}


def audit():
    phases = [audit_phase(False), audit_phase(True)]
    return {'date': '2026-11-11', 'phases': phases,
            'historicalUnknownPolicy': 'Original rejected delivery retained, not resent or rewritten as success',
            'ok': all(p['ok'] for p in phases)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-evidence', action='store_true')
    args = parser.parse_args()
    report = audit()
    if args.write_evidence:
        (ROOT / 'evidence/2026-11-11/long-text-ledger.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

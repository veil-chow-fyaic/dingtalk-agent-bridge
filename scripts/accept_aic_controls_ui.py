#!/usr/bin/env python3
"""Read-only E100 ledger/process/artifact audit; native UI observations are separate."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def ledger(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        return {table: [dict(r) for r in db.execute('SELECT * FROM ' + table + ' ORDER BY ' + key)]
                for table, key in (('jobs', 'id'), ('outbox', 'key'), ('meta', 'key'))}


def audit():
    folder = ROOT / 'local/aic-controls-20261112'
    labels = ['LONG', 'CONTEXT', 'CANCEL', 'AFTER', 'NEW-CHECK']
    found = []
    for path in (ROOT / 'local/agents').glob('*/tasks.sqlite3'):
        data = ledger(path)
        if any(j['command'].startswith('[AIC-E100-LONG]') for j in data['jobs']):
            found.append((path, data))
    assert len(found) == 1
    path, data = found[0]
    base = path.parent
    jobs = {}
    for label in labels:
        matches = [r for r in data['jobs'] if r['command'].startswith('[AIC-E100-' + label + ']')]
        assert len(matches) == 1
        jobs[label] = matches[0]
    checks = {'one_job_per_unique_task': True,
              'four_completed_one_cancelled': all(jobs[k]['state'] == 'completed' for k in labels if k != 'CANCEL')
                  and jobs['CANCEL']['state'] == 'cancelled'}
    first = jobs['LONG']
    relevant = [j for j in data['jobs'] if first['seq'] <= j['seq'] <= jobs['NEW-CHECK']['seq']]
    ids = {j['id'] for j in relevant}
    outbox = [o for o in data['outbox'] if o['job_id'] in ids]
    checks['all_new_receipts_confirmed'] = bool(outbox) and all(
        o['state'] == 'confirmed' and read_receipt(o).get('message_id') for o in outbox)
    expected = (folder / 'long-expected.txt').read_bytes()
    response = json.loads(first['result'])
    artifact = response['artifacts'][0]
    downloaded = folder / 'downloads/0-aic-e100-long.txt'
    checks['long_input_exact'] = '/agent ' + first['command'] == (folder / 'long-command.txt').read_text()
    checks['long_response_exact'] = response['response']['text'] == (folder / 'long-reply-expected.txt').read_text()
    checks['download_staged_and_input_exact'] = expected == downloaded.read_bytes() == (ROOT / artifact['file']).read_bytes()
    digest = hashlib.sha256(expected).hexdigest()
    checks['artifact_digest_exact'] = digest == artifact['sha256']
    # Outbox insertion order is not the protocol order; keys carry the chunk ordinal.
    text_chunks = [json.loads(o['payload'])['text'] for o in sorted(outbox, key=lambda r: r['key'])
                   if o['job_id'] == first['id'] and '-text-' in o['key']]
    checks['two_chunks_reconstruct_exactly'] = len(text_chunks) == 2 and ''.join(t.removeprefix('[Agent] ') for t in text_chunks) == response['response']['text']
    calls = {}
    for label, job in jobs.items():
        events = [json.loads(line) for line in (base / 'runs' / job['id'] / 'events.jsonl').read_text().splitlines()]
        calls[label] = [t['function'] for e in events if e.get('role') == 'assistant' for t in e.get('tool_calls', [])]
    checks['long_actual_python'] = any(t['name'] == 'Bash' and 'python' in t['arguments'] for t in calls['LONG'])
    context = json.loads(jobs['CONTEXT']['result'])['response']['text']
    checks['context_without_file_tools'] = not calls['CONTEXT'] and all(x in context for x in ('60', '1830', '2'))
    running = read(folder / 'cancel-running-process.json')
    marker = running['marker']
    processes = {int(x.split()[0]): x.split(None, 4) for x in running['ps'].splitlines()
                 if x.split() and x.split()[0].isdigit()}
    child, shell = processes[marker['pid']], processes[marker['pgid']]
    checks['cancel_was_real_python_child'] = int(child[1]) == marker['pgid'] and 'Python' in child[4] and 'time.sleep(180)' in shell[4]
    deadline = read(folder / 'cancel-deadline-check.json')
    checks['cancel_no_process_or_late_file_after_deadline'] = deadline['elapsed'] >= 180 and not deadline['process'] and not deadline['lateExists'] and not (base / 'workspaces/0/exports/e100-late.txt').exists()
    checks['cancel_dispatched_no_artifact'] = all(set(json.loads(o['payload'])) == {'text'} for o in outbox if o['job_id'] == jobs['CANCEL']['id'])
    checks['after_cancel_real_tool_result'] = any(t['name'] == 'Bash' and 'python' in t['arguments'] for t in calls['AFTER']) and (base / 'workspaces/0/exports/e100-after.txt').read_text().strip() == '1517'
    old = read(folder / 'before-new.json')
    transition = read(folder / 'new-transition.json')
    old_meta = {r['key']: r['value'] for r in old['meta']}
    transition_meta = {r['key']: r['value'] for r in transition['meta']}
    current_meta = {r['key']: r['value'] for r in data['meta']}
    checks['new_generation_and_native_session_reset'] = old_meta['generation'] == '0' and transition_meta['generation'] == current_meta['generation'] == '1' and 'session_id' not in transition_meta and current_meta['session_id'] != old_meta['session_id']
    current_jobs = {j['id']: j for j in data['jobs']}
    checks['old_jobs_unchanged'] = all(current_jobs[j['id']] == j for j in old['jobs'])
    new_text = json.loads(jobs['NEW-CHECK']['result'])['response']['text']
    checks['new_context_and_workspace_isolated'] = '不知道' in new_text and '6042' not in new_text and not list((base / 'workspaces/1/exports').iterdir()) and any(t['name'] == 'Bash' for t in calls['NEW-CHECK'])
    statuses = [j for j in relevant if j['command'] == 'status']
    checks['same_body_distinct_status_messages'] = len(statuses) == 3 and len({json.loads(j['model'])['id'] for j in statuses}) == 3
    checks['status_saw_actual_running_job'] = any('执行中 1，排队 0' in json.loads(o['payload']).get('text', '') for o in outbox)
    before = read(folder / 'after-ledgers.json')
    checks['other_routes_jobs_outbox_sessions_unchanged'] = all(ledger(ROOT / 'local/agents' / key / 'tasks.sqlite3') == value for key, value in before.items() if key != base.name)
    checks['managed_reload_preserved_transport_and_ledgers'] = read(folder / 'reload-result.json')['ok']
    return {'evidence': 'E100', 'date': '2026-11-12', 'ok': all(checks.values()), 'checks': checks,
            'download': {'bytes': len(expected), 'sha256': digest},
            'taskCount': len(relevant), 'receiptCount': len(outbox),
            'cancelDeadlineElapsedSeconds': deadline['elapsed'],
            'scope': 'Read-only local records and artifacts; native UI observations in docs/104, no DWS calls.'}


def read_receipt(row):
    return json.loads(row['receipt'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report')
    args = parser.parse_args()
    result = audit()
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        Path(args.report).write_text(text)
    print(text)
    raise SystemExit(0 if result['ok'] else 1)

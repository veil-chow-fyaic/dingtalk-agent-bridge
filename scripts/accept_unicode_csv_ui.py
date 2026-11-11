#!/usr/bin/env python3
"""Read-only audit of original attachment names and the native Unicode CSV task."""
import argparse
import csv
from decimal import Decimal
import io
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from frozen_install import frozen_install_matches, module_sources_match
from dingtalk_bridge.routing import route_configs


def content_checks(source, csv_data, report):
    original = list(csv.reader(io.StringIO(source.read_bytes().decode('utf-8-sig'), newline='')))
    received = list(csv.reader(io.StringIO(csv_data.decode('utf-8-sig'), newline='')))
    values = original[1:]
    amounts = [Decimal(r[1]) * Decimal(r[2]) for r in values]
    expected = [dict(zip(original[0], r), 金额=f'{v:.2f}') for r, v in zip(values, amounts)]
    total = f'{sum(amounts):.2f}'
    return {
        'source_bom_and_complex_fields': source.read_bytes().startswith(b'\xef\xbb\xbf') and len(values) == 3 and values[0][0] == '咖啡,深焙' and values[0][3] == '第一行\n第二行' and values[1][0] == '"纸杯"' and values[1][3] == '' and values[2][0] == '茶🫖',
        'output_bom_and_header': csv_data.startswith(b'\xef\xbb\xbf') and received[0] == original[0] + ['金额'],
        'csv_original_fields_preserved': [r[:-1] for r in received[1:-1]] == values,
        'csv_amounts_and_total': [r[-1] for r in received[1:-1]] == [f'{v:.2f}' for v in amounts] and received[-1] == ['TOTAL', '', '', '', total] and total == '57.00',
        'report_original_name': report['originalName'] == source.name,
        'report_encoding_count_total': (report['encoding'], report['rowCount'], report['total']) == ('utf-8-sig', 3, total),
        'report_rows_exact': report['rows'] == expected,
    }


def audit():
    folder = ROOT / 'local/unicode-csv-ui-20261112'
    before, final, cases, intent, obs = (read(folder / n) for n in ('before.json', 'final.json', 'cases.json', 'intent.json', 'ui-observations.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key
        transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key'), ('events', transport, 'message_id')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group':
            checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct_cfg, direct_folder = cfg, agent
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    old, end = before['routes']['direct'], final['routes']['direct']
    checks['exact_two_new_tasks'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {c['job']['id'] for c in cases.values()}
    checks['exact_six_new_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for c in cases.values() for r in c['outbox']} and sum(len(c['outbox']) for c in cases.values()) == 6
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    for label, case in cases.items():
        job = case['job']; model = json.loads(job['model']); event = case['event']
        checks[label + '_authorized_completed_input'] = job in jobs and job['state'] == 'completed' and events.get(model['id']) == event and event['from_self'] is False and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
        checks[label + '_confirmed_bound_replies'] = all(r in outbox and r['state'] == 'confirmed' for r in case['outbox']) and len(case['replyEvents']) == len(case['outbox']) and all(events.get(e['message_id']) == e and e['from_self'] is True and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
        checks[label + '_no_self_echo_task'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
        log = ROOT / case['runLog']; entries = [json.loads(x) for x in log.read_text().splitlines()]
        checks[label + '_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
        calls = {t['id']: t['function'] for e in entries for t in e.get('tool_calls', [])}
        results = {e['tool_call_id']: e['content'] for e in entries if e.get('role') == 'tool'}
        result = json.loads(job['result'])
        if label == 'prepare':
            checks['preparation_waited_without_tools_or_files'] = not calls and not result['response']['files'] and not result['artifacts'] and '准备接收' in result['response']['text']
            checks['prompt_contains_no_filename_or_answers'] = job['command'] == intent['prompt'] and all(x not in job['command'] for x in (intent['originalName'], '57.00', '12.50', '咖啡', '纸杯'))
        else:
            file_model, file_result, file_calls, file_results = model, result, calls, results
    source = ROOT / intent['fixture']; data = source.read_bytes(); part = file_model['parts'][0]
    checks['single_original_attachment_exact'] = len(file_model['parts']) == 1 and not file_model['issues'] and part['name'] == source.name and part['type'] == 'file' and len(data) == intent['bytes'] == 135 and digest(data) == intent['sha256'] == part['sha256'] and Path(part['path']).read_bytes() == data
    paths = list((direct_folder / 'workspaces/1/inputs' / cases['file']['job']['id']).glob('*'))
    checks['safe_runtime_input_original_bytes'] = len(paths) == 1 and paths[0].read_bytes() == data and paths[0].name != source.name and '🧾' not in paths[0].name
    checks['actual_python_read_and_csv_parse'] = any(fn['name'] == 'Bash' and 'csv.reader' in fn['arguments'] and 'read_bytes' in fn['arguments'] and 'bytes 135 bom True' in str(file_results.get(cid)) for cid, fn in file_calls.items())
    checks['actual_decimal_compute_and_two_exports'] = any(fn['name'] == 'Bash' and 'from decimal import Decimal' in fn['arguments'] and 'csv.DictWriter' in fn['arguments'] and 'write_text' in fn['arguments'] and json.loads(file_results[cid]) == {'rowCount': 3, 'total': '57.00', 'csv_bytes': 175, 'json_bytes': 572} for cid, fn in file_calls.items() if cid in file_results)
    artifacts = file_result['artifacts']
    checks['two_requested_artifacts'] = len(artifacts) == 2 and file_result['response']['files'] == ['exports/dab-utf8-summary.csv', 'exports/dab-utf8-report.json']
    for index, kind in enumerate(('csv', 'json')):
        client = folder / obs['client' + kind.capitalize()]; content = client.read_bytes(); artifact = artifacts[index]
        checks[kind + '_client_export_staged_exact'] = content == (ROOT / artifact['file']).read_bytes() == (direct_folder / 'workspaces/1' / file_result['response']['files'][index]).read_bytes() and digest(content) == artifact['sha256']
        resource = read(folder / (kind + '-resources.json'))
        checks[kind + '_official_resource_exact'] = resource['ok'] and resource['failedCount'] == 0 and bool(resource['downloads']) and all((ROOT / r['localPath']).read_bytes() == content for r in resource['downloads'])
        checks[kind + '_native_download_completed'] = client.name + ' 下载完成' in (folder / (kind + '-saved.ax.txt')).read_text()
    checks.update(content_checks(source, (folder / obs['clientCsv']).read_bytes(), read(folder / obs['clientJson'])))
    checks['full_native_reply_correct'] = file_result['response']['text'] == '已处理原始文件「' + source.name + '」：3行，总额57.00。' and '[Agent] ' + file_result['response']['text'] in (folder / 'text-reply.ax.txt').read_text()
    checks['csv_opened_native_cells'] = all(x in (folder / 'csv-opened.ax.txt').read_text() for x in ('快速查看', '咖啡,深焙', '"纸杯"', '茶🫖', '37.50', '3.00', '16.50', 'TOTAL', '57.00'))
    checks['json_opened_native_full_report'] = (folder / obs['clientJson']).read_text().strip() in (folder / 'json-opened.ax.txt').read_text()
    checks['one_text_and_one_file_attempt'] = all(read(folder / n)['attempts'] == 1 for n in ('text-send-attempt.json', 'file-send-attempt.json'))
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 6 and all(v['reviewed'] and digest((folder / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    install = read(ROOT / 'evidence/2026-11-12/attachment-metadata-install.json')
    checks['frozen_tested_install_matches'] = frozen_install_matches(install, folder)
    return {'currentWorkspaceCodeMatchesTestedWheel': module_sources_match(install, ROOT / 'dingtalk_bridge'), 'date': '2026-11-12', 'checks': checks, 'ok': all(checks.values()),
            'sourceSha256': digest(data), 'outputs': {k: {'bytes': (folder / obs['client' + k.capitalize()]).stat().st_size, 'sha256': digest((folder / obs['client' + k.capitalize()]).read_bytes())} for k in ('csv', 'json')},
            'scope': 'Two native DM inputs: prepare then one file; original name metadata, CSV data, real tools and two client downloads/openings. No group or single-message multi-file claim.',
            'counts': {k: {t: len(v[t]) for t in ('jobs', 'outbox', 'deliveries', 'events')} for k, v in final['routes'].items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: Path(args.output).write_text(encoded)
    print(encoded); raise SystemExit(0 if report['ok'] else 1)

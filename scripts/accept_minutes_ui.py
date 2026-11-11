#!/usr/bin/env python3
"""Read-only audit of the original synthetic WAV / official minutes / native IM report."""
import argparse
import json
import re
from pathlib import Path
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def content_checks(source, transcript, summary, todos, report):
    def normalize(s):
        return re.sub(r'[，。\s]', '', s.replace('七百零三', '703').replace('五份', '5份'))
    return {
        'transcript_matches_synthetic_source': normalize(source) == normalize(transcript),
        'server_summary_key_facts': all(x in summary for x in ('周五前', '703元', '5份', '先完成草稿', '预算复核')),
        'server_three_action_items': todos == ['周五前完成海港项目初稿', '核对703元预算', '检查5份样本文件'],
        'report_transcript_and_summary_exact': transcript in report and summary in report,
        'report_actions_and_empty_keywords_truthful': all(x in report for x in todos) and '是，共 3 项' in report and 'keywords 服务端返回为空列表' in report,
    }


def official_checks(upload, detail, receipt, detail_receipt, plan, profile, marker):
    command = receipt['command']
    def arg(flag): return command[command.index(flag) + 1] if flag in command else None
    return {
        'official_upload_completed': upload['complete'] and not upload['failures'] and upload['operation'] == 'minutes.upload_and_analyze' and all(s['complete'] for s in upload['stages']),
        'independent_detail_same_created_id': bool(upload['taskUuid']) and upload['taskUuid'] == detail['taskUuid'] == detail['basic']['result']['taskUuid'] == detail['transcript']['taskUuid'] == detail_receipt['task_uuid'],
        'detail_complete_no_failures': detail['complete'] and detail['failureCount'] == 0 and all(detail[k]['success'] in (True, 'true') for k in ('basic', 'summary', 'keywords', 'todos')) and detail['transcript']['complete'] and detail['todos']['result']['complete'],
        'explicit_profile_title_and_language': arg('--profile') == profile and arg('--title') == marker == detail['basic']['result']['title'] and arg('--input-language') == plan['input_language'] == 'zh',
        'bounded_analysis_without_cards_or_extra_generation': arg('--wait-timeout') == '180' and not any(x in command for x in ('--enable-message-card', '--mindmap', '--speaker-insights', '--upload-and-notify')) and all(plan[k] is False for k in ('message_card', 'mindmap', 'speaker_insights')),
        'official_commands_succeeded': receipt['exit_code'] == detail_receipt['exit_code'] == 0,
    }


def audit():
    folder = ROOT / 'local/minutes-ui-20261112'
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
    checks['exact_five_new_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for c in cases.values() for r in c['outbox']} and sum(len(c['outbox']) for c in cases.values()) == 5
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
            checks['prompt_contains_no_transcript_or_answers'] = job['command'] == intent['prompt'] and all(x not in job['command'] for x in ('海港', '703', '七百零三', '5份', '五份', '周五前'))
        else:
            file_model, file_result, file_calls, file_results = model, result, calls, results
    workspace = direct_folder / 'workspaces/1'; office = workspace / 'office-evidence'; marker = intent['marker']
    source = ROOT / intent['fixture']; data = source.read_bytes(); part = file_model['parts'][0]
    checks['single_original_wav_exact'] = len(file_model['parts']) == 1 and not file_model['issues'] and part['name'] == source.name and part['type'] == 'file' and len(data) == intent['bytes'] == 701836 and digest(data) == intent['sha256'] == part['sha256'] and Path(part['path']).read_bytes() == data
    paths = list((workspace / 'inputs' / cases['file']['job']['id']).glob('*'))
    checks['runtime_input_original_bytes'] = len(paths) == 1 and paths[0].read_bytes() == data
    checks['office_records_preserved'] = bool(cases['file']['officeFiles']) and all(digest((ROOT / p).read_bytes()) == sha for p, sha in cases['file']['officeFiles'].items())
    upload = read(office / (marker + '-upload-analyze-001.stdout.json')); detail = read(office / (marker + '-detail-001.stdout.json'))
    plan = read(office / (marker + '-upload-analyze-001.intent.json'))
    checks.update(official_checks(upload, detail, read(office / (marker + '-upload-analyze-001.receipt.json')), read(office / (marker + '-detail-001.receipt.json')), plan, direct_cfg['profile'], marker))
    checks['upload_input_matches_original'] = (workspace / plan['file']).read_bytes() == data and plan['file_sha256'] == digest(data) and plan['file_bytes'] == len(data)
    commands = [json.loads(fn['arguments']).get('command', '') for fn in file_calls.values() if fn['name'] == 'Bash']
    creates = [c for c in commands if '+upload-and-analyze' in c and 'subprocess.run(cmd' in c and '--dry-run' not in c]
    checks['single_actual_create_and_intent'] = len(creates) == 1 and len(list(office.glob(marker + '-upload-analyze-*.intent.json'))) == len(list(office.glob(marker + '-upload-analyze-*.receipt.json'))) == 1
    checks['actual_separate_detail_and_report_tools'] = any('+detail' in c and 'subprocess.run(cmd' in c and "['taskUuid']" in c for c in commands) and any('write_text' in c and 'transcript_text' in c and 'summary_text' in c for c in commands)
    dry_ids = [cid for cid, fn in file_calls.items() if '--dry-run' in fn['arguments']]
    checks['dry_run_not_mistaken_for_creation'] = len(dry_ids) == 1 and '"executed": false' in file_results[dry_ids[0]]
    transcript = '\n'.join(p['paragraph'] for p in detail['transcript']['paragraphList'])
    summary = detail['summary']['result']['fullSummary']; todos = [i['title'] for i in detail['todos']['result']['items']]
    client = folder / obs['client']; report = client.read_text(); artifacts = file_result['artifacts']; text = file_result['response']['text']
    checks.update(content_checks((ROOT / intent['script']).read_text(), transcript, summary, todos, report))
    checks['upload_detail_artifacts_consistent'] = upload['artifacts']['transcript'] == detail['transcript'] and upload['artifacts']['summary'] == summary and upload['artifacts']['todos']['items'] == detail['todos']['result']['items'] and detail['keywords']['result']['keywords'] == []
    checks['single_report_staged_download_exact'] = file_result['response']['files'] == ['exports/dab-minutes-report.txt'] and len(artifacts) == 1 and client.read_bytes() == (workspace / file_result['response']['files'][0]).read_bytes() == (ROOT / artifacts[0]['file']).read_bytes() and digest(client.read_bytes()) == artifacts[0]['sha256']
    resource = read(folder / 'txt-resources.json')
    checks['official_im_resource_exact'] = resource['ok'] and resource['failedCount'] == 0 and bool(resource['downloads']) and all((ROOT / r['localPath']).read_bytes() == client.read_bytes() for r in resource['downloads'])
    checks['native_download_completed'] = client.name + ' 下载完成' in (folder / 'saved.ax.txt').read_text()
    checks['native_report_opened_and_end_reviewed'] = report.strip() in (folder / 'opened.ax.txt').read_text() and '快速查看' in (folder / 'opened.ax.txt').read_text() and 'keywords 服务端返回为空列表' in (folder / 'opened-bottom.ax.txt').read_text()
    checks['full_native_reply_correct'] = '[Agent] ' + text in (folder / 'text-reply.ax.txt').read_text() and all(x in text for x in ('3项任务', '周五前', '703元', '5份', '先完成草稿再复核预算'))
    checks['no_private_ids_or_urls_in_report'] = all(x not in report + text for x in (direct_cfg['profile'], upload['taskUuid'], detail['basic']['result']['url'])) and 'http' not in report + text
    checks['one_text_and_one_file_attempt'] = all(read(folder / n)['attempts'] == 1 for n in ('text-send-attempt.json', 'file-send-attempt.json'))
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 6 and all(v['reviewed'] and digest((folder / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    return {'date': '2026-11-12', 'ok': all(checks.values()), 'checks': checks,
            'source': {'bytes': len(data), 'sha256': digest(data)}, 'report': {'bytes': client.stat().st_size, 'sha256': digest(client.read_bytes())},
            'counts': {k: {t: len(v[t]) for t in ('jobs', 'outbox', 'deliveries', 'events')} for k, v in final['routes'].items()},
            'scope': 'Synthetic WAV file via native DM, one official minutes creation and independent detail, actual Kimi report, native reply/download/open. Not native voice, independent conference, or assigned standalone todo verification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: (ROOT / args.output).write_text(data)
    print(data); raise SystemExit(0 if report['ok'] else 1)

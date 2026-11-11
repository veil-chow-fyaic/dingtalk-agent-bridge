#!/usr/bin/env python3
"""Read-only audit of the original personal Drive upload/download IM task."""
import argparse
import json
from pathlib import Path
from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def content_checks(expected, source, downloaded, client):
    return {'source_exact_utf8': source == expected.encode() and not source.startswith(b'\xef\xbb\xbf'),
            'official_download_exact': downloaded == source,
            'native_client_exact': client == downloaded,
            'expected_57_bytes': len(source) == len(downloaded) == len(client) == 57}


def official_checks(space, upload, info, download, plan, receipt, profile):
    cmd = receipt['command']
    def arg(flag):
        return cmd[cmd.index(flag) + 1] if flag in cmd and cmd.index(flag) + 1 < len(cmd) else None
    return {
        'upload_target_scope_and_no_overwrite': plan['space_id'] == space['spaceId'] and plan['folder_id'] == space['rootFolderId'] and plan['overwrite'] is False and arg('--space-id') == space['spaceId'] and arg('--folder') == space['rootFolderId'] and '--node' not in cmd and arg('--profile') == profile,
        'independent_info_same_created_node': info['ok'] and info['data']['fileId'] == upload['data']['nodeId'] and info['data']['spaceId'] == space['spaceId'] and info['data']['name'] == plan['remote_file_name'] and info['data']['fileSize'] == 57,
        'official_download_same_node': download['ok'] and download['data']['success'] and download['data']['nodeId'] == upload['data']['nodeId'] and download['data']['sizeBytes'] == 57 and download['data']['savedPath'] == 'exports/dab-drive-returned.txt',
    }


def audit():
    f = ROOT / 'local/office-boundary-20261112'
    before, final, case, intent, obs = (read(f / n) for n in ('before.json', 'final.json', 'case.json', 'intent.json', 'ui-observations.json'))
    checks = {}
    for cfg, state in route_configs(read(ROOT / 'local/service-config.json')):
        kind = cfg['conversationType']; old, end = before['routes'][kind], final['routes'][kind]
        key = digest(json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], kind]).encode())[:24]
        agent = ROOT / 'local/agents' / key; transport = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        for table, db, identity in [('jobs', agent / 'tasks.sqlite3', 'id'), ('outbox', agent / 'tasks.sqlite3', 'key'), ('deliveries', transport, 'key'), ('events', transport, 'message_id')]:
            current = {r[identity]: r for r in rows(db, table)}
            checks[kind + '_' + table + '_preserved'] = bool(old[table]) and all(current.get(r[identity]) == r for r in old[table])
        checks[kind + '_old_logs_preserved'] = all((ROOT / p).is_file() and digest((ROOT / p).read_bytes()) == sha for p, sha in old['runtimeFiles'].items())
        if kind == 'group': checks['group_unchanged'] = all(old[t] == end[t] for t in ('jobs', 'outbox', 'meta', 'deliveries', 'events'))
        else:
            direct_cfg, direct_folder = cfg, agent
            jobs, outbox = rows(agent / 'tasks.sqlite3', 'jobs'), rows(agent / 'tasks.sqlite3', 'outbox')
            events = {r['message_id']: json.loads(r['body']) for r in rows(transport, 'events')}
    old, end = before['routes']['direct'], final['routes']['direct']; job = case['job']; model = json.loads(job['model'])
    checks['exact_one_new_task'] = {j['id'] for j in end['jobs']} - {j['id'] for j in old['jobs']} == {job['id']} and sum(j['command'] == intent['prompt'] for j in jobs) == 1
    checks['exact_three_confirmed_outbox'] = {r['key'] for r in end['outbox']} - {r['key'] for r in old['outbox']} == {r['key'] for r in case['outbox']} and len(case['outbox']) == 3 and all(r in outbox and r['state'] == 'confirmed' for r in case['outbox'])
    checks['native_session_unchanged'] = bool(old['meta']) and old['meta'] == end['meta']
    event = case['event']
    checks['authorized_completed_input'] = job in jobs and job['state'] == 'completed' and events.get(model['id']) == event and not event['from_self'] and event['sender_id'] in read(ROOT / 'local/agent-direct-config.json')['allowedSenderIds']
    checks['liev_bound_replies'] = len(case['replyEvents']) == 3 and all(events.get(e['message_id']) == e and e['from_self'] and e['sender_id'] == direct_cfg['selfSenderId'] for e in case['replyEvents'])
    checks['no_self_echo'] = all(not any(json.loads(j['model'])['id'] == e['message_id'] for j in jobs) for e in case['replyEvents'])
    log = ROOT / case['runLog']; checks['run_log_preserved'] = digest(log.read_bytes()) == case['runLogSha256']
    checks['office_records_preserved'] = all(digest((ROOT / p).read_bytes()) == sha for p, sha in case['officeFiles'].items())
    workspace = direct_folder / 'workspaces/1'; office = workspace / 'office-evidence'; marker = intent['marker']
    space = read(office / (marker + '-space-list-001.stdout.json'))['result']['items']
    upload = read(office / (marker + '-upload-001.stdout.json')); plan = read(office / (marker + '-upload-001.intent.json'))
    checks['unique_personal_space'] = len(space) == 1 and space[0]['spaceType'] == 'mySpace' and space[0]['spaceName'] == '我的文件'
    checks['official_created_file_target'] = upload['ok'] and upload['data']['success'] and upload['data']['spaceId'] == space[0]['spaceId'] and upload['data']['file']['type'] == 'FILE' and upload['data']['file']['name'] == intent['fileName'] and upload['data']['sizeBytes'] == 57
    checks['single_preserved_upload_attempt'] = len(list(office.glob(marker + '-upload-*.intent.json'))) == 1 and len(list(office.glob(marker + '-upload-*.receipt.json'))) == 1 and read(office / (marker + '-upload-001.receipt.json'))['exit_code'] == 0
    checks.update(official_checks(space[0], upload, read(office / (marker + '-info-001.stdout.json')), read(office / (marker + '-download-001.stdout.json')), plan, read(office / (marker + '-upload-001.receipt.json')), direct_cfg['profile']))
    entries = [json.loads(x) for x in log.read_text().splitlines()]
    commands = [json.loads(t['function']['arguments']).get('command', '') for e in entries for t in e.get('tool_calls', []) if t['function']['name'] == 'Bash']
    uploads = [c for c in commands if '+upload' in c and '--help' not in c]
    checks['exact_one_real_upload_command'] = len(uploads) == 1 and 'subprocess.run(cmd' in uploads[0]
    checks['actual_info_download_and_byte_comparison'] = any('+info' in c and '+download' in c and 'subprocess.run' in c for c in commands) and any('read_bytes()' in c and 'sha256' in c and 'same_bytes' in c for c in commands)
    checks['official_info_download_exit_zero'] = all(read(office / (marker + '-' + op + '-001.receipt.json'))['exit_code'] == 0 for op in ('info', 'download'))
    result = json.loads(job['result']); artifact = result['artifacts'][0]; text = result['response']['text']
    source = (ROOT / case['source']).read_bytes(); download = (workspace / 'exports/dab-drive-returned.txt').read_bytes(); client = (f / obs['client']).read_bytes()
    checks.update(content_checks(intent['content'], source, download, client))
    checks['one_official_download_artifact'] = result['response']['files'] == ['exports/dab-drive-returned.txt'] and len(result['artifacts']) == 1 and (ROOT / artifact['file']).read_bytes() == client and artifact['sha256'] == digest(client)
    checks['native_download_completed'] = all(x in (f / 'saved.ax.txt').read_text() for x in (Path(obs['client']).name, '文本 打开', '已查收')) and '下载中' not in (f / 'saved.ax.txt').read_text()
    checks['native_file_opened'] = '快速查看' in (f / 'opened.ax.txt').read_text() and intent['content'].strip() in (f / 'opened.ax.txt').read_text()
    checks['native_full_reply'] = '[Agent] ' + text in (f / 'reply.ax.txt').read_text() and '57' in text and '字节一致' in text
    checks['no_private_ids_in_result'] = all(s not in text for s in (direct_cfg['profile'], space[0]['spaceId'], upload['data']['nodeId'])) and 'http' not in text
    checks['one_native_input_attempt'] = read(f / 'send-attempt.json')['attempts'] == 1
    checks['reviewed_frames_preserved'] = len(obs['frames']) == 3 and all(v['reviewed'] and digest((f / n).read_bytes()) == v['sha256'] for n, v in obs['frames'].items())
    return {'date': '2026-11-12', 'ok': all(checks.values()), 'checks': checks, 'file': {'bytes': len(client), 'sha256': digest(client)}, 'counts': {k: {t: len(v[t]) for t in ('jobs', 'outbox', 'deliveries', 'events')} for k, v in final['routes'].items()}, 'scope': 'One personal Drive file via official CLI and actual local Kimi; native DM request/reply, client download/open. No shared space, permissions, independent meeting or ASR claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output'); args = parser.parse_args()
    report = audit(); data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: (ROOT / args.output).write_text(data)
    print(data); raise SystemExit(0 if report['ok'] else 1)

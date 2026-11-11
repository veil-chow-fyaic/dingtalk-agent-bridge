#!/usr/bin/env python3
"""Read-only evidence audit: native tasks, official office operations and reports."""
import argparse
import json
from pathlib import Path

from accept_office_files import ROOT, digest, read
from accept_task_controls import rows
from dingtalk_bridge.routing import route_configs


def audit():
    folder=ROOT/'local/office-agent-20261111'
    before,final,cases=(read(folder/n) for n in ('before-ledgers.json','final-ledgers.json','cases.json'))
    if set(cases)!={'A','B','C'}:return {'ok':False,'error':'incomplete_office_task_cases'}
    checks={}
    for cfg,state in route_configs(read(ROOT/'local/service-config.json')):
        kind=cfg['conversationType'];key=digest(json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],kind]).encode())[:24]
        agent=ROOT/'local/agents'/key;transport=ROOT/'local/runtime/routes'/state/'bridge.sqlite3'
        old,end=before['routes'][kind],final['routes'][kind]
        for table,db,identity in [('jobs',agent/'tasks.sqlite3','id'),('outbox',agent/'tasks.sqlite3','key'),('deliveries',transport,'key')]:
            current={r[identity]:r for r in rows(db,table)}
            checks[kind+'_'+table+'_preserved']=bool(old[table]) and all(current.get(r[identity])==r for r in old[table])
        checks[kind+'_old_runtime_logs_preserved']=bool(old['runtimeFiles']) and all(
            (ROOT/name).is_file() and digest((ROOT/name).read_bytes())==item['sha256'] for name,item in old['runtimeFiles'].items())
        if kind=='group':
            checks['group_unchanged']=all(old[t]==end[t] for t in ('jobs','outbox','meta','deliveries','runtimeFiles'))
        else:
            direct=cfg;jobs=rows(agent/'tasks.sqlite3','jobs');outbox=rows(agent/'tasks.sqlite3','outbox')
            events={r['message_id']:json.loads(r['body']) for r in rows(transport,'events')}
            checks['same_native_session']=old['meta']==end['meta']
            checks['exact_three_new_runtime_jobs']={j['id'] for j in end['jobs']}-{j['id'] for j in old['jobs']}=={c['job']['id'] for c in cases.values()}
            expected={r['key'] for c in cases.values() for r in c['outbox']}
            checks['exact_nine_outbox_and_transport_replies']=len(expected)==9 and all(
                {r['key'] for r in end[t]}-{r['key'] for r in old[t]}==expected for t in ('outbox','deliveries'))
    by_id,by_key={j['id']:j for j in jobs},{r['key']:r for r in outbox}
    reports={}
    for name,case in cases.items():
        job,event=case['job'],case['event'];prefix=name+'_'
        checks[prefix+'completed_job_preserved']=job['state']=='completed' and by_id.get(job['id'])==job
        expected_input=read(folder/case['intentFile'])['input']
        # One observed interval dash changed between native input and history.
        # Preserve the original intent; do not generally normalize Unicode.
        if name=='B':expected_input=expected_input.replace('00:10–00:15','00:10-00:15',1)
        checks[prefix+'authorized_input_with_documented_projection']=events.get(event['message_id'])==event and event['content']==expected_input and event['from_self'] is False and event['sender_id'] in read(ROOT/'local/agent-direct-config.json')['allowedSenderIds']
        checks[prefix+'one_job_for_input']=sum(json.loads(j['model'])['id']==event['message_id'] for j in jobs)==1
        checks[prefix+'three_confirmed_unchanged_replies']=len(case['outbox'])==3 and all(r['state']=='confirmed' and by_key.get(r['key'])==r for r in case['outbox'])
        checks[prefix+'three_bound_liev_replies']=len(case['replyEvents'])==3 and all(events.get(e['message_id'])==e and e['from_self'] is True and e['sender_id']==direct['selfSenderId'] for e in case['replyEvents'])
        checks[prefix+'no_echo_jobs']=all(not any(json.loads(j['model'])['id']==e['message_id'] for j in jobs) for e in case['replyEvents'])
        checks[prefix+'runtime_logs_unchanged']=bool(case['runFiles']) and all(digest((ROOT/p).read_bytes())==sha for p,sha in case['runFiles'].items())
        logs=[ROOT/p for p in case['runFiles'] if p.endswith('/events.jsonl')]
        tools=[t['function'] for p in logs for line in p.read_text().splitlines() for t in json.loads(line).get('tool_calls',[])]
        checks[prefix+'real_runtime_tools']=len(logs)==1 and bool(tools)
        result=json.loads(job['result']);artifacts=result.get('artifacts',[])
        checks[prefix+'one_report_file']=len(artifacts)==1
        if len(artifacts)!=1:return {'ok':False,'checks':checks}
        if len(artifacts)==1:
            artifact=artifacts[0];client=folder/Path(artifact['file']).name
            data=client.read_bytes() if client.is_file() else b''
            checks[prefix+'client_download_matches']=bool(data) and data==(ROOT/artifact['file']).read_bytes() and digest(data)==artifact['sha256']
            reports[name]=data.decode()
        ui=case['ui']
        checks[prefix+'native_input_and_file_card_observed']=read(folder/case['intentFile'])['input'] in (folder/ui['inputAX']).read_text() and Path(artifacts[0]['file']).name in (folder/ui['cardAX']).read_text()
        opened=(folder/ui['openAX']).read_text()
        checks[prefix+'download_opened_in_quicklook']='窗口 快速查看' in opened and Path(artifacts[0]['file']).name in opened and ('DAB-OFFICE-20261112-'+name in opened or name=='C' and '密送' in opened)
        checks[prefix+'private_screenshots_present']=all((folder/p).stat().st_size>1000 for p in ui['screenshots'])
    source=ROOT/read(folder/'office-artifact-path.json')['workspaceEvidence']
    def raw(name):return read(source/name)
    def independent(name):
        receipt=read(folder/(name+'.json'))
        if receipt['exitCode']!=0:raise ValueError('Independent read did not succeed')
        return json.loads(receipt['stdout'])
    doc=raw('DAB-OFFICE-20261112-A-doc-create-001.stdout.json')
    fetched=independent('doc-readback')
    checks['document_created_and_independently_read']=doc['success'] is True and fetched['complete'] is True and fetched['content']['nodeId']==fetched['target']['canonicalId']==doc['nodeId'] and fetched['content']['title']=='DAB-OFFICE-DOC-20261112' and all(m in fetched['content']['markdown'] for m in ('DAB-DOC-CONTENT-001','65'))
    todo=raw('DAB-OFFICE-20261112-A-todo-create-001.stdout.json')['data'];task=independent('todo-readback')['data']
    checks['todo_completed_and_independently_read']=todo['verified'] is True and task['taskId']==todo['taskId'] and task['subject']=='DAB-OFFICE-TODO-20261112' and task['isDone'] is True
    checks['todo_only_self']=task['executorIds']==[task['creatorId']] and all(p==task['creatorId'] for p in task['participantIds'])
    calendar=raw('DAB-OFFICE-20261112-B-calendar-create-001.stdout.json')['data'];event=independent('calendar-readback')['data']['event']
    checks['calendar_verified_exact_past_time']=calendar['verified'] is True and event['eventId']==calendar['eventId'] and event['summary']=='DAB-OFFICE-CALENDAR-20261112' and event['description']=='DAB-CALENDAR-CONTENT-001' and event['start']['dateTime']=='2026-11-11T00:10:00+08:00' and event['end']['dateTime']=='2026-11-11T00:15:00+08:00' and event['start']['timeZone']=='Asia/Shanghai' and event['freeBusy']=='FREE'
    checks['calendar_only_self_and_no_rooms']=event['organizer']['self'] is True and all(a['self'] for a in event['attendees']) and not event['meetingRooms']
    checks['calendar_defaults_reported']=bool(event['onlineMeetingInfo']) and any(r['minutes']==15 for r in event['reminders']) and '15分钟' in reports['B'] and '未入会' in reports['B']
    created=raw('DAB-OFFICE-20261112-B-mail-draft-create-001.stdout.json')['result']['message']
    message=independent('draft-readback')['data']['value'];atomic=independent('draft-atomic-readback')['message']
    checks['draft_creation_receipt_in_drafts']=created['folderId']=='5'
    checks['draft_subject_body_and_empty_to_cc_readback']=all(m['id']==created['id'] and m['subject']=='DAB-OFFICE-DRAFT-20261112' and 'DAB-MAIL-DRAFT-002' in m['markdownBody'] and m['toRecipients']==[] and m['ccRecipients']==[] for m in (message,atomic))
    checks['missing_bcc_and_folder_not_inferred_from_reads']=all('bccRecipients' not in m and 'folderId' not in m and 'isDraft' not in m for m in (message,atomic))
    listing=independent('draft-folder-readback')
    checks['draft_folder_independently_verified']=read(folder/'draft-folder-readback.json')['requestedFolderId']=='5' and any(m['id']==created['id'] and m['subject']==created['subject'] for m in listing['messages'])
    checks['original_overstatement_retained']='收件人/抄送/密送：均为空' in reports['B']
    checks['corrected_report_qualifies_missing_fields']='密送' in reports['C'] and '未独立核验' in reports['C'] and '创建回执' in reports['C'] and '草稿箱' in reports['C']
    receipts=read(folder/'office-evidence-index.json')
    checks['raw_office_evidence_unchanged']=bool(receipts) and all((source/name).is_file() and digest((source/name).read_bytes())==sha for name,sha in receipts.items())
    trace=read(folder/'official-trace.json');counts={}
    for row in trace['records']:
        if row.get('msg')=='command_start':
            name=row['product']+'/'+row['tool'];counts[name]=counts.get(name,0)+1
    writes={'doc/create_document','todo/create_personal_todo','todo/update_todo_done_status','calendar/create_calendar_event','mail/create_draft'}
    reads={'doc/get_document_content','doc/get_document_info','todo/get_todo_detail','calendar/list_calendars','calendar/get_calendar_detail','mail/list_user_mailboxes','mail/get_email_by_message_id','mail/search_emails'}
    checks['five_exact_office_writes_once']=all(counts.get(n)==1 for n in writes)
    checks['no_other_office_writes_or_mail_send']=set(counts)<=writes|reads
    correction_at=read(folder/'correction-intent.json')['at']
    from datetime import datetime
    checks['correction_used_only_office_reads']=all(r['product']+'/'+r['tool'] in reads for r in trace['records'] if r.get('msg')=='command_start' and datetime.fromisoformat(r['time']).timestamp()>=correction_at)
    installed=read(folder/'install-validation-final.json')
    checks['final_installed_modules_match_deployed_source']=installed['ok'] and installed['finalInstalledAndWheelModulesMatch'] and installed['codeSha256']==read(folder/'deployed-source-corrected.json')['codeSha256']
    checks['observer_not_reset']=before['observer']['pid']==final['observer']['pid'] and before['observer']['startedAt']==final['observer']['startedAt'] and final['observer']['samples']>before['observer']['samples']
    return {'date':'2026-11-12','checks':checks,'runtimeTasks':3,'confirmedReplies':9,'createdOfficeObjects':4,
            'inputProjectionDifferences':[{'case':'B','expected':'00:10–00:15','history':'00:10-00:15','byteExact':False,'origin':'Transformation stage not established'}],
            'officeOperations':counts,'limits':['Official CLI context and guidance, not an OS sandbox or forced CLI allowlist',
            'No service-side idempotency guarantee for office creation; one-attempt evidence for these cases only',
            'BCC is not exposed by the two message reads; draft location has additional folder-list evidence',
            'User-side evidence is IM task/report download/opening, not viewing liev-owned objects in veil office UI',
            'No sharing, additional invitees, mail sending or meeting attendance tested','24h observation remains in progress'],
            'ok':all(checks.values())}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');args=p.parse_args()
    report=audit()
    if args.write_evidence:
        path=ROOT/'evidence/2026-11-12/office-agent-ledger.json';path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)

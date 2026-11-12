#!/usr/bin/env python3
"""Preview local intake candidates against an immutable deployment review.

No worker construction, download, task execution, cursor update, or network.
Remote messages not yet synced remain unknown, even when every local count is 0.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_history_deployment import Snapshot, check_snapshot, digest, meta_value
from dingtalk_bridge.agent_gateway import command_for, file_request
from dingtalk_bridge.message_model import normalize, media_parts
from dingtalk_bridge.routing import route_configs


def classify(model, settings, route_key, jobs):
    if not isinstance(model, dict):return {'classification': 'quarantined'}
    mid=model.get('id')
    if not isinstance(mid,str) or not mid:raise ValueError('invalid_saved_model')
    job_id=hashlib.sha256((route_key+'\0'+mid).encode()).hexdigest()[:24]
    if job_id in jobs:
        return {'classification':'existing_job','jobId':job_id,'priorJobState':jobs[job_id]}
    command=command_for(model, settings)
    if command is None:return {'classification':'ignored_by_task_policy'}
    if file_request(model,command):kind='file_selection_review'
    elif model['issues']:kind='blocked_content_review'
    elif command in {'status','状态','cancel','取消','new','新会话'}:
        kind='control_review'
    elif list(media_parts(model)):kind='media_task_review'
    else:kind='text_task_review'
    return {'classification':kind,'jobId':job_id}


def preview(root, deployment_review, config='local/service-config.json'):
    snap=Snapshot(root);root=snap.root
    plan=snap.json(deployment_review)
    check_snapshot(root,plan)
    # Every ledger/config must belong to the frozen deployment inventory.
    snap.inputs.update(plan['inputSnapshot'])
    def frozen(name):
        if name not in plan['inputSnapshot']:raise ValueError('input_not_in_deployment_review')
        return name
    rows=[]
    with ExitStack() as locks:
        for name in ('local/runtime/manager.lock','local/runtime/dws-access.lock'):
            locks.enter_context(snap.owner_lock(name))
        if snap.json('local/runtime/dws-suspended.json')!={'reason':'operator_suspended'}:
            raise ValueError('operator_suspension_required')
        routes=list(route_configs(snap.json(frozen(config))))
        if len(routes)!=len(plan['routes']):raise ValueError('route_review_mismatch')
        for index,((route,state),saved) in enumerate(zip(routes,plan['routes'])):
            if saved['routeIndex']!=index or saved['conversationType']!=route['conversationType']:
                raise ValueError('route_review_mismatch')
            settings=snap.json(frozen(saved['agentConfig']))
            if (settings['accountId'],settings['conversationId'])!=(route['accountId'],route['group']):
                raise ValueError('agent_route_mismatch')
            scope=json.dumps([route['accountId'],route['profile'],route['group'],route['conversationType']])
            key=hashlib.sha256(scope.encode()).hexdigest()[:24]
            base='local/runtime'+('/routes/'+state if state else '')
            inbox='local/consumers/agent-'+key
            for name in (base+'/process.lock',inbox+'/process.lock'):
                locks.enter_context(snap.owner_lock(name))
            with snap.database(frozen(base+'/bridge.sqlite3')) as bridge, \
                 snap.database(frozen('local/agents/'+key+'/tasks.sqlite3')) as tasks, \
                 snap.database(frozen(inbox+'/inbox.sqlite3')) as consumer:
                cursor_raw=meta_value(consumer,'cursor')
                if cursor_raw is not None and not re.fullmatch(r'0|[1-9][0-9]*',cursor_raw):
                    raise ValueError('invalid_consumer_cursor')
                cursor=int(cursor_raw or 0)
                jobs=dict(tasks.execute('SELECT id,state FROM jobs'))
                maximum=bridge.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]
                # Explicit initialCursor may intentionally precede future events;
                # no guessed correction of a cursor that exceeds local max.
                entries=[];seqs=set();mids=set()
                for row in consumer.execute('SELECT seq,message_id,model,state FROM inbox ORDER BY seq'):
                    if row['seq']>cursor:raise ValueError('inbox_ahead_of_cursor')
                    model=json.loads(row['model'])
                    if isinstance(model,dict) and model.get('id')!=row['message_id']:
                        raise ValueError('saved_model_identity_mismatch')
                    if isinstance(model,dict) and (model.get('accountId'),model.get('conversationId'),model.get('conversationType'))!=(route['accountId'],route['group'],route['conversationType']):
                        raise ValueError('saved_model_scope_mismatch')
                    item={'seq':row['seq'],'messageId':row['message_id'],'origin':'stored_inbox',
                          'inboxState':row['state'],'modelSha256':digest(row['model'].encode()),
                          **classify(model,settings,key,jobs)}
                    entries.append(item);seqs.add(row['seq']);mids.add(row['message_id'])
                for row in bridge.execute('SELECT seq,message_id,body FROM events WHERE seq>? ORDER BY seq',(cursor,)):
                    if row['seq'] in seqs or row['message_id'] in mids:raise ValueError('duplicate_intake_identity')
                    item={'seq':row['seq'],'messageId':row['message_id'],'origin':'unconsumed_transport',
                          'eventSha256':digest(row['body'].encode())}
                    try:
                        value=json.loads(row['body'])
                        if not isinstance(value,dict) or value.get('seq',row['seq'])!=row['seq'] or value.get('message_id')!=row['message_id']:
                            raise ValueError('event_identity_mismatch')
                        model=normalize({'seq':row['seq'],**value},route)
                    except (ValueError,KeyError,TypeError):
                        item['classification']='quarantined'
                    else:item.update(classify(model,settings,key,jobs))
                    entries.append(item);seqs.add(row['seq']);mids.add(row['message_id'])
                counts={}
                for item in entries:counts[item['classification']]=counts.get(item['classification'],0)+1
                rows.append({'routeIndex':index,'conversationType':route['conversationType'],
                    'consumerCursor':cursor,'localTransportMaxSeq':maximum,'cursorExceedsLocalMax':cursor>maximum,
                    'unconsumedLocalEvents':sum(e['origin']=='unconsumed_transport' for e in entries),
                    'candidateTasksOrNotices':sum(n for k,n in counts.items() if k.endswith('_review')),
                    'classificationCounts':counts,'entries':entries})
        snap.verify()
    return {'schemaVersion':1,'executable':False,'purpose':'local_backlog_preview_only',
            'deploymentReviewSha256':digest(snap.path(deployment_review).read_bytes()),
            'reviewerSha256':digest(Path(__file__).read_bytes()),'routes':rows,
            'inputSnapshot':snap.inputs,
            'summary':{'routeCount':len(rows),'unconsumedLocalEvents':sum(r['unconsumedLocalEvents'] for r in rows),
                'candidateTasksOrNotices':sum(r['candidateTasksOrNotices'] for r in rows),
                'quarantinedLocalMessages':sum(r['classificationCounts'].get('quarantined',0) for r in rows),
                'remoteUnsyncedMessages':'unknown','executionAllowed':False,'newDwsCallsAllowed':False},
            'limits':['Only local stored events; remote downtime messages remain unknown',
                      'Candidate classification is not a dry-run of queue controls, file selection, hydration or runtime',
                      'Existing jobs keep original state; no cursor change, execution, resend or session reset',
                      'Private IDs and hashes only; raw message text, commands, models and session values are not exported']}


def publish(root,key,report):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',key):raise ValueError('invalid_review_key')
    snap=Snapshot(root);snap.inputs=dict(report['inputSnapshot']);snap.verify()
    parent=snap.path('local/backlog-reviews');parent.mkdir(exist_ok=True,mode=0o700)
    folder=snap.path('local/backlog-reviews/'+key);folder.mkdir(mode=0o700)
    path=folder/'preview.json'
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as out:
        json.dump(report,out,ensure_ascii=False,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default='.')
    p.add_argument('--deployment-review',required=True)
    p.add_argument('--config',default='local/service-config.json')
    p.add_argument('--key',required=True)
    args=p.parse_args()
    try:
        report=preview(args.root,args.deployment_review,args.config)
        publish(args.root,args.key,report)
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,sqlite3.Error) as exc:
        # Exception text can contain source data: print the type only.
        print(json.dumps({'ok':False,'error':type(exc).__name__,'executionAllowed':False}))
        return 2
    print(json.dumps({'ok':True,**report['summary']}))
    return 0


if __name__=='__main__':raise SystemExit(main())

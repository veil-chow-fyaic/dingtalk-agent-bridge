#!/usr/bin/env python3
"""Read saved native UI repair/quote evidence; never send or contact services."""
import argparse, copy, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(data):return hashlib.sha256(data).hexdigest()
def read_json(path):return json.loads(path.read_text())
def load(folder):
    names=('before-quote','after-quote','quote-source-event','quote-intent','directory-repair','reviewed-frames','ui-observations','managed-identity-after','directory-after-review')
    data={n:read_json(folder/(n+'.json')) for n in names}
    data['files']={p.name:p.read_bytes() for p in folder.iterdir() if p.suffix=='.jpeg' or p.name.endswith('.ax-excerpt.txt')}
    data['image-error-log']=(folder/'image-output-error.log').read_text()
    return data

def validate(data):
    b,a,s,i,u=(data[n] for n in ('before-quote','after-quote','quote-source-event','quote-intent','ui-observations'))
    checks={}
    checks['one_native_send_no_new_dws_send']=i['nativeSendAttempts']==1 and i['newDwsOrHttpSends']==0
    oldids={x['message_id'] for x in b['routes']['direct']['bridge']['events']}
    added=[x for x in a['routes']['direct']['bridge']['events'] if x['message_id'] not in oldids]
    checks['exactly_one_direct_event']=len(added)==1 and len(a['routes']['direct']['bridge']['events'])==len(b['routes']['direct']['bridge']['events'])+1 and len({x['message_id'] for x in a['routes']['direct']['bridge']['events']})==len(a['routes']['direct']['bridge']['events'])
    e=json.loads(added[0]['body']) if len(added)==1 else {}
    checks['existing_quote_source']=any(json.loads(x['body'])==s for x in b['routes']['direct']['bridge']['events']) and s['message_id']==i['sourceMessageId'] and s['from_self'] is True
    checks['incoming_sender_route_and_body']=(e.get('from_self') is False and e.get('conversation_type')=='direct' and e.get('sender_id')==i['expectedNativeSenderId'] and e.get('account_id')==i['accountId'] and e.get('conversation_id')==i['conversationId'] and e.get('content')==i['topLevelText'])
    q=e.get('raw',{}).get('quotedMessage',{})
    checks['official_quote_exact_source']=(q.get('messageId')==s['message_id'] and q.get('conversationId')==s['conversation_id'] and q.get('sender')==s['sender'] and q.get('text')==s['content'])
    checks['sample_flat_quote_no_media']=not e.get('attachments') and not q.get('quotedMessage') and not q.get('resourceRefs') and not q.get('attachments')
    checks['native_message_not_ai_flag']=not e.get('raw',{}).get('messageAiSendFlag')
    rows=[r for r in a['routes']['direct']['inbox']['inbox'] if r['message_id']==e.get('message_id')]
    r=rows[0] if len(rows)==1 else {};model=json.loads(r['model']) if r.get('model') else {};quote=model.get('quote',{})
    cursor=int(next(x['value'] for x in a['routes']['direct']['inbox']['meta'] if x['key']=='cursor'))
    checks['history_consumer_record_binding']=len(added)==len(rows)==1 and added[0]['message_id']==e.get('message_id') and added[0]['seq']==r.get('seq') and json.loads(r.get('raw','{}'))=={'seq':added[0]['seq'],**e}
    checks['consumer_normalized_and_covered']=len(rows)==1 and r.get('state')=='normalized' and r.get('attempts')==0 and r.get('error') is None and r.get('seq',cursor+1)<=cursor
    checks['consumer_top_level_exact']=model.get('id')==e.get('message_id') and model.get('senderId')==i['expectedNativeSenderId'] and model.get('fromSelf') is False and model.get('accountId')==i['accountId'] and model.get('conversationId')==i['conversationId'] and model.get('conversationType')=='direct' and model.get('parts')==[{'type':'text','text':i['topLevelText']}] and model.get('issues')==[]
    checks['consumer_quote_exact']=quote.get('id')==s['message_id'] and quote.get('conversationId')==s['conversation_id'] and quote.get('senderName')==s['sender'] and quote.get('senderId') is None and quote.get('parts')==[{'type':'text','text':s['content']}] and quote.get('issues')==[]
    checks['filter_prefix_without_mention']=i['topLevelText'].startswith('[Agent]') and e.get('content')==i['topLevelText'] and u['draftNoPrecedingMention']
    for route in ('group','direct'):
        before,end=b['routes'][route],a['routes'][route]
        checks[route+'_jobs_outbox_sessions_unchanged']=before['tasks']==end['tasks']
        checks[route+'_all_old_events_preserved']=all(x in end['bridge']['events'] for x in before['bridge']['events'])
        checks[route+'_delivery_upload_rejection_unchanged']=all(before['bridge'][t]==end['bridge'][t] for t in ('deliveries','image_uploads','rejection_audit'))
        checks[route+'_old_inbox_preserved']=all(x in end['inbox']['inbox'] for x in before['inbox']['inbox'])
    checks['group_no_new_history_or_inbox']=b['routes']['group']['bridge']['events']==a['routes']['group']['bridge']['events'] and b['routes']['group']['inbox']['inbox']==a['routes']['group']['inbox']['inbox']
    checks['only_one_new_inbox_record']=len(a['routes']['direct']['inbox']['inbox'])==len(b['routes']['direct']['inbox']['inbox'])+1
    checks['99_jobs_240_outbox_preserved']=sum(len(x['tasks']['jobs']) for x in a['routes'].values())==99 and sum(len(x['tasks']['outbox']) for x in a['routes'].values())==240
    checks['manager_and_product_unchanged']=b['manager']==a['manager'] and b['sourceSha256']==a['sourceSha256'] and len(a['sourceSha256'])==25
    components=a['manager']['components']
    checks['actual_source_equals_deployment']=len(components)==3 and {c['name'] for c in components}=={'transport','agent-1','agent-2'} and len({c['pid'] for c in components})==3 and all(c['launchSourceSha256']==a['sourceSha256'] for c in components)
    identities=data['managed-identity-after']
    checks['three_owned_process_identities']=len(identities)==3 and {(x['name'],x['pid']) for x in identities}=={(c['name'],c['pid']) for c in components} and all(x['present'] and x['identityMatches'] and str(x['pid'])==x['processLine'].split()[0] and ' '.join(x['processLine'].split()[2:])==' '.join(next(c['identity'] for c in components if c['name']==x['name']).split()) for x in identities)
    checks['dws_guard_ready_at_both_reads']=b['access'].get('state')==a['access'].get('state')=='ready'
    rep=data['directory-repair'];log=data['image-error-log']
    checks['missing_directory_observed']=rep['before'][0]['isDirectory'] and not rep['before'][0]['isSymlink'] and rep['before'][1]['exists'] is False
    checks['same_user_private_directory_created']=rep['after']['isDirectory'] and not rep['after'].get('isSymlink',False) and rep['after']['mode']=='0o700' and rep['after']['uid']==rep['before'][0]['uid'] and rep['existingPermissionsChanged'] is False and rep['processesRestarted'] is False
    post=data['directory-after-review']
    checks['post_repair_directory_lstat']=post['path']==rep['after']['path'] and post['isDirectory'] and post['isSymlink'] is False and post['uid']==rep['after']['uid'] and post['mode']=='0o700'
    checks['native_imageio_enoent_evidence']='IIOImageWriteSession' in log and 'error = 2 (No such file or directory)' in log and 'CGImageDestinationCreateWithURL' in log
    required={'ui-restored','direct-composition','group-composition','quote-source-and-entry','quote-opened','quote-draft','quote-sent'}
    frames=data['reviewed-frames']
    checks['seven_original_native_frames']=set(frames)==required and len({x['file'] for x in frames.values()})==len(required) and all(len(data['files'].get(x['file'],b''))==x['sizeBytes'] and digest(data['files'].get(x['file'],b''))==x['sha256'] and data['files'].get(x['file'],b'').startswith(b'\xff\xd8') for x in frames.values())
    checks['native_ui_review_recorded']=all(u[k] for k in ('originalInterfaceRestored','clickAndScrollVerified','directCompositionTextOrderSenderAndAiVisible','groupCompositionTextOrderSenderAndAiVisible','quoteEntryVisible','quoteDraftTargetVisible','quoteSentTargetAndBodyVisible'))
    checks['save_limit_not_promoted']=u['compositionClientOriginalsSaved']==0 and u['compositionResends']==0 and u['compositionSavePassed'] is False
    checks['draft_ax_excerpt_matches']=i['topLevelText'] in data['files']['quote-draft.ax-excerpt.txt'].decode() and s['content'] in data['files']['quote-draft.ax-excerpt.txt'].decode()
    checks['sent_ax_excerpt_matches']=i['topLevelText'] in data['files']['quote-sent.ax-excerpt.txt'].decode() and s['content'] in data['files']['quote-sent.ax-excerpt.txt'].decode()
    return checks

def audit(folder):
    data=load(folder);checks=validate(data)
    negative=[]
    def corrupt_model_route(d):
        before={x['message_id'] for x in d['before-quote']['routes']['direct']['inbox']['inbox']}
        r=next(x for x in d['after-quote']['routes']['direct']['inbox']['inbox'] if x['message_id'] not in before)
        model=json.loads(r['model']);model['conversationId']='wrong-route';r['model']=json.dumps(model)
    for name,mutate in [
        ('wrong_source',lambda d:d['quote-source-event'].__setitem__('message_id','wrong-source')),
        ('wrong_body',lambda d:d['quote-intent'].__setitem__('topLevelText','changed-body')),
        ('extra_job',lambda d:d['after-quote']['routes']['direct']['tasks']['jobs'].append({'synthetic':'extra'})),
        ('changed_frame',lambda d:d['files'].__setitem__('quote-sent.jpeg',b'changed')),
        ('empty_manager_components',lambda d:(d['before-quote']['manager'].__setitem__('components',[]),d['after-quote']['manager'].__setitem__('components',[]))),
        ('wrong_model_route',corrupt_model_route),
        ('duplicate_history_id',lambda d:d['after-quote']['routes']['direct']['bridge']['events'].append(copy.deepcopy(d['before-quote']['routes']['direct']['bridge']['events'][0]))),
        ('aliased_frames',lambda d:d.__setitem__('reviewed-frames',{k:d['reviewed-frames']['quote-sent'] for k in d['reviewed-frames']})),
        ('symlink_directory',lambda d:d['directory-after-review'].__setitem__('isSymlink',True)),
        ('wrong_history_envelope',lambda d:d['after-quote']['routes']['direct']['bridge']['events'][-1].__setitem__('message_id','wrong-envelope')),
        ('unrelated_process_identity',lambda d:d['managed-identity-after'][0].__setitem__('pid',1)),
        ('false_directory_precondition',lambda d:d['directory-repair']['before'][1].__setitem__('exists',True)),
    ]:
        changed=copy.deepcopy(data);mutate(changed);negative.append({'case':name,'rejected':not all(validate(changed).values())})
    ok=all(checks.values()) and all(x['rejected'] for x in negative)
    return {'schemaVersion':1,'evidence':'E146','date':'2026-11-17','ok':ok,'checks':checks,'negativeChecks':negative,'newMatrixCells':['direct_inbound_quote'] if ok else [],'matrix':{'passed':52,'blocked':10,'partial':2} if ok else None,'remainingMust':['R01','R06','R07','R13'] if ok else None,'newNativeMessages':1,'newRuntimeJobs':0,'newAgentOutbox':0,'compositionClientSaves':0,'deployedProduct':'2b479a8','dwsVersion':'v1.0.67','privateEvidence':'local/ui-repair-20261117','evidenceSha256':{name:digest((folder/name).read_bytes()) for name in ('directory-repair.json','image-output-error.log','reviewed-frames.json','before-quote.json','after-quote.json','quote-source-event.json','quote-intent.json','ui-observations.json','managed-identity-after.json','directory-after-review.json')},'limitations':['Directory disappearance mechanism unknown; recovery is not proof against recurrence or a Keychain fix','Native tool screenshots visually reviewed; AX excerpts are copied from actual tool output, not full-tree exports','Composition rendering passed; original per-image client save/open remains unverified','One flat text quote only; no arbitrary nesting, attachment reply or model execution claim','Per-database read transactions are not a common cutoff snapshot','No deployment, collector change, new natural refresh or 24-hour reliability success claim']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private',type=Path,default=ROOT/'local/ui-repair-20261117');parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=audit(args.private);body=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(body)
    print(body);raise SystemExit(0 if result['ok'] else 1)

"""Conservative DWS history projection. Unknown structure never becomes a ready turn."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

# Fixed DWS history preserves this exact voice marker beside any transcription.
# A marker still needs its resourceRef and verified original before readiness.
MEDIA = re.compile(r'\[(图片|语音)消息\]\(mediaId=([^\s)]+)\)')
FILE = re.compile(r'^\[文件\]\s*(.*?)\s+fileId:\s*(\S+)\s*$')


def ref_key(ref):
    if not isinstance(ref,dict):raise ValueError('invalid_resource_reference')
    kind=ref.get('resourceIdType') or ref.get('type') or ref.get('resourceType')
    rid=ref.get('resourceId')
    if kind not in {'fileId','mediaId'} or not isinstance(rid,str) or not rid:
        raise ValueError('unsupported_resource_reference')
    return kind,rid


def resource_refs(raw):
    refs=raw.get('resourceRefs',[])
    if not isinstance(refs,list):raise ValueError('invalid_resource_references')
    return {ref_key(r):r for r in refs}


def project(raw, group, depth=0):
    issues=[]
    if not isinstance(raw,dict) or depth>2:raise ValueError('invalid_or_deep_quote')
    if raw.get('conversationId')!=group:raise ValueError('cross_conversation_message')
    text=raw.get('text')
    if not isinstance(text,str):raise ValueError('missing_text_projection')
    refs=resource_refs(raw)
    quote_raw=raw.get('quotedMessage')
    quote=None
    quoted_keys=set()
    if quote_raw is not None:
        quote=project(quote_raw,group,depth+1)
        # Keep the quoted source distinct from the actual incoming sender.
        # DWS can provide only a display name; never turn it into an identity
        # or infer permissions/fromSelf from it. Missing IDs remain unknown.
        quote['conversationId']=group
        for target,source in (('id','messageId'),('senderId','senderId'),('senderName','sender')):
            value=quote_raw.get(source)
            quote[target]=value if isinstance(value,str) and value.strip() else None
        issues.extend('quote:'+i for i in quote['issues'])
        quoted_keys=set(resource_refs(quote_raw))
    parts=[];used=set()
    def media(kind,rid,media_type,name=None):
        key=(kind,rid)
        if key not in refs:issues.append('text_resource_missing_from_refs')
        used.add(key)
        part={'type':media_type,'resource':{'type':kind,'resourceId':rid}}
        if name:part['name']=name
        parts.append(part)
    file_match=FILE.fullmatch(text)
    if file_match:
        media('fileId',file_match[2],'file',file_match[1])
    else:
        offset=0
        for match in MEDIA.finditer(text):
            if match.start()>offset:parts.append({'type':'text','text':text[offset:match.start()]})
            media('mediaId',match[2],'image' if match[1]=='图片' else 'audio');offset=match.end()
        if offset<len(text):parts.append({'type':'text','text':text[offset:]})
        # Every marker must be parsed, even beside another complete media part.
        remaining=MEDIA.sub('',text)
        if any(marker in remaining for marker in ('[图片消息]','[语音消息]')) or ('[文件]' in text and not file_match):
            issues.append('unparsed_media_marker')
    # The native client can expose a second mediaId for the same image. Do not
    # discard it or guess its placement. Hydration must prove byte equality with
    # a positioned image before this candidate can reach the runtime.
    extra=set(refs)-used-quoted_keys
    candidates=[]
    if any(p['type']=='image' for p in parts):
        for key in sorted(extra):
            if key[0]=='mediaId' and refs[key].get('contentType')=='image':
                candidates.append({'resource':{'type':key[0],'resourceId':key[1]}})
    unresolved=extra-{ref_key(x['resource']) for x in candidates}
    # DWS aggregates quoted resources at the top level. They belong in quote only.
    if unresolved:issues.append('unpositioned_resources')
    if not parts:issues.append('empty_projection')
    for flag in ('partial','truncated'):
        if raw.get(flag):issues.append(flag)
    result={'parts':parts,'issues':sorted(set(issues)),'fidelity':'dws_text_projection'}
    if candidates:result['imageAliasCandidates']=candidates
    if quote is not None:result['quote']=quote
    return result


def normalize(event,config):
    if event.get('conversation_id')!=config['group']:raise ValueError('unexpected_conversation')
    if event.get('account_id',config.get('accountId','default'))!=config.get('accountId','default'):
        raise ValueError('unexpected_account')
    raw=event.get('raw',{})
    if not isinstance(raw,dict):raise ValueError('invalid_message_payload')
    if raw.get('messageId')!=event.get('message_id'):raise ValueError('message_identity_mismatch')
    sender=raw.get('senderId')
    own=config.get('selfSenderId')
    from_self=sender==own if own and sender else None
    if event.get('from_self') is not from_self:raise ValueError('sender_classification_mismatch')
    model=project(raw,config['group'])
    try:
        time=datetime.fromisoformat(raw['createTime'])
        if time.tzinfo is None:
            time=time.replace(tzinfo=ZoneInfo(config.get('historyTimezone','Asia/Shanghai')))
            model['timeZoneAssumed']=True
        timestamp=time.isoformat()
    except (ValueError,KeyError,TypeError):
        timestamp=None;model['issues'].append('invalid_timestamp')
    return {'schemaVersion':1,'id':event['message_id'],'accountId':config.get('accountId','default'),
        'conversationId':config['group'],'conversationType':config.get('conversationType','group'),'senderId':sender,
        'receivedAt':timestamp,'fromSelf':from_self,'source':event.get('source'),**model}


def media_parts(model):
    for part in model['parts']:
        if part['type']!='text':yield part
    if model.get('quote'):yield from media_parts(model['quote'])


def materialize(model,ledger,root,cache_root=None):
    if ledger.get('ok') is not True or ledger.get('partial') or ledger.get('failedCount'):
        raise ValueError('partial_download')
    root=Path(root).resolve();allowed=(cache_root or root/'local/runtime/downloads').resolve()
    records={}
    for entry in ledger.get('downloads',[]):
        key=ref_key(entry)
        if key in records:raise ValueError('ambiguous_resource_download')
        path=(root/entry['localPath']).resolve()
        if not path.is_relative_to(allowed) or not path.is_file():raise ValueError('unsafe_or_missing_download')
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest!=entry.get('sha256') or len(data)!=entry.get('sizeBytes'):raise ValueError('download_integrity_mismatch')
        records[key]={'path':str(path),'sha256':digest,'sizeBytes':len(data)}
    needed={ref_key(p['resource']) for p in media_parts(model)}
    aliases=[]
    def collect(node):
        for candidate in node.get('imageAliasCandidates',[]):aliases.append((node,candidate))
        if node.get('quote'):collect(node['quote'])
    collect(model)
    needed.update(ref_key(a['resource']) for _,a in aliases)
    if not needed.issubset(records):raise ValueError('missing_downloaded_resource')
    verified=[]
    for node,candidate in aliases:
        record=records[ref_key(candidate['resource'])]
        matches=[p for p in node['parts'] if p['type']=='image' and
                 records[ref_key(p['resource'])]['sha256']==record['sha256']]
        if not matches:raise ValueError('unpositioned_image_not_alias')
        verified.append((candidate,record,matches[0]['resource']))
    # Assign only after all resources have passed validation (no partial ready payload).
    for part in media_parts(model):part.update(records[ref_key(part['resource'])])
    for candidate,record,resource in verified:
        candidate.update(record,verified=True,aliasOf=dict(resource))
    return model


def file_request(model,command):
    return model['conversationType']=='group' and command is not None and (command=='--files' or command.startswith('--files '))


def select_file_sources(model,command,previous,*,allow_images=False):
    """Bind explicit selectors to the command's preceding route history (newest first)."""
    try:
        option = '--attachments' if allow_images else '--files'
        raw = command[len(option):].lstrip()
        requested, end = json.JSONDecoder().raw_decode(raw)
        task = raw[end:].strip()
        if (not isinstance(requested, list) or not 1 <= len(requested) <= 8 or not task
                or task in {'status','状态','cancel','取消','new','新会话'}
                or model['issues'] or model.get('quote') or list(media_parts(model))):
            raise ValueError('file_selection_invalid')
        selectors = []
        for value in requested:
            if (isinstance(value, str) and value and len(value) <= 255
                    and not any(c in value for c in '/\\\x00\r\n')):
                selectors.append(('file', value))
            elif (allow_images and isinstance(value, dict) and set(value) == {'image'}
                  and type(value['image']) is int and value['image'] > 0):
                selectors.append(('image', value['image']))
            else:
                raise ValueError('file_selection_invalid')
        if len(set(selectors)) != len(selectors):
            raise ValueError('file_selection_invalid')
        requested_at = datetime.fromisoformat(model['receivedAt'])
    except (ValueError, TypeError) as exc:
        raise ValueError('file_selection_invalid') from exc

    files = {}
    images = []
    image_order_known = True
    for candidate in previous:
        if candidate is None:
            # A malformed projection can hide images. Never silently renumber an older photo.
            image_order_known = False
            continue
        if (candidate['senderId'] != model['senderId'] or candidate['fromSelf'] is not model['fromSelf']
                or candidate['accountId'] != model['accountId'] or candidate['conversationId'] != model['conversationId']):
            continue
        try:
            age = (requested_at - datetime.fromisoformat(candidate['receivedAt'])).total_seconds()
        except (TypeError, ValueError):
            image_order_known = False
            continue
        if not 0 <= age <= 1800:
            continue
        if candidate['issues']:
            image_order_known = False
            continue
        # Only top-level originals count. Within an image strip, the rightmost
        # (last) positioned image is the most recent. Quoted photos never count.
        for idx in range(len(candidate['parts']) - 1, -1, -1):
            part = candidate['parts'][idx]
            if part['type'] == 'file':
                name = part.get('name')
                files.setdefault(name, []).append({'messageId':candidate['id'],'resource':part['resource'],'name':name})
            elif part['type'] == 'image' and image_order_known:
                images.append({'messageId':candidate['id'],'resource':part['resource'],'imagePartIndex':idx})
    sources = []
    for kind, value in selectors:
        if kind == 'image':
            if value > len(images):
                raise ValueError('file_selection_missing_or_ambiguous')
            sources.append(images[value - 1])
        else:
            matches = files.get(value, [])
            if len(matches) != 1:
                raise ValueError('file_selection_missing_or_ambiguous')
            sources.append(matches[0])
    return task, sources

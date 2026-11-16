"""Generic Agent-facing CLI over the local bridge HTTP API; no runtime dependency."""
import argparse,json
from pathlib import Path
import sys
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--account-id');p.add_argument('--conversation-id')
    # Match the service/gateway workspace cwd, including when installed in a venv.
    p.add_argument('--token-file',default='local/runtime/http-token')
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('health');sub.add_parser('conversations')
    discovery=sub.add_parser('discovery');discovery.add_argument('--cursor',type=int,default=0);discovery.add_argument('--limit',type=int,default=50)
    events=sub.add_parser('events');events.add_argument('--after',type=int,default=0);events.add_argument('--limit',type=int,default=100)
    events.add_argument('--wait-seconds',type=float,default=0)
    send=sub.add_parser('send');send.add_argument('--key',required=True)
    send.add_argument('--reply-to',help='Quote an observed message in this route; text only')
    send.add_argument('--expected-sha256',help='Require these exact file/image bytes before a new send (lowercase SHA256)')
    content=send.add_mutually_exclusive_group(required=True)
    content.add_argument('--text');content.add_argument('--text-stdin',action='store_true');content.add_argument('--file');content.add_argument('--image')
    content.add_argument('--composition-json', help='JSON file with literal text and 1-9 ordered images: path + expected sha256 (experimental rich text)')
    for action in ['status','reconcile']:
        command=sub.add_parser(action);command.add_argument('--key',required=True)
        if action=='reconcile':command.add_argument('--rejection-evidence',help='Private local official-log JSON; never resends')
    attachment=sub.add_parser('attachments');attachment.add_argument('--message-id',required=True);attachment.add_argument('--repair',action='store_true')
    sync=sub.add_parser('sync');sync.add_argument('--deep',action='store_true')
    a=p.parse_args();selector={}
    if a.account_id is not None:selector['account_id']=a.account_id
    if a.conversation_id is not None:selector['conversation_id']=a.conversation_id
    data=None
    if a.action=='send':
        data={**selector,'idempotency_key':a.key}
        for field in ('text','file','image','reply_to','expected_sha256'):
            if getattr(a,field,None) is not None:data[field]=getattr(a,field)
        if a.text_stdin:data['text']=sys.stdin.read(65537)
        if a.composition_json:
            with Path(a.composition_json).open('rb') as handle:raw=handle.read(1024*1024+1)
            if len(raw)>1024*1024:p.error('Composition JSON exceeds 1 MiB')
            data['composition']=json.loads(raw)
        path='/v1/send'
    elif a.action=='reconcile':
        path='/v1/reconcile';data={**selector,'idempotency_key':a.key}
        if a.rejection_evidence:data['rejection_evidence']=a.rejection_evidence
    elif a.action=='attachments':path='/v1/attachments';data={**selector,'message_id':a.message_id,'repair':a.repair}
    elif a.action=='sync':path='/v1/sync';data={**selector,'deep':a.deep}
    else:
        path='/v1/'+('deliveries/'+quote(a.key,safe='') if a.action=='status' else a.action)
        if a.action=='events':selector.update(after=a.after,limit=a.limit,wait_seconds=a.wait_seconds)
        if a.action=='discovery':selector.update(cursor=a.cursor,limit=a.limit)
        if selector:path+='?'+urlencode(selector)
    token=Path(a.token_file).read_text().strip()
    req=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},
        data=None if data is None else json.dumps(data).encode())
    try:
        with urlopen(req,timeout=120) as response: result=json.load(response)
    except HTTPError as exc:
        print(exc.read().decode());raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()

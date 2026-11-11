"""Run one bounded durable shadow intake; no model calls or messages sent."""
import argparse,json,os
from pathlib import Path
from urllib.request import Request,urlopen
from .consumer import Inbox
from .routing import route_configs
from urllib.parse import urlencode

def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name',default='shadow');p.add_argument('--hydrate-self',action='store_true')
    p.add_argument('--account-id');p.add_argument('--conversation-id');p.add_argument('--config',default='local/service-config.json')
    p.add_argument('--follow',action='store_true',help='Continue intake with durable cursor and bounded long polling')
    p.add_argument('--max-batches',type=int,default=0,help='Follow batch limit; 0 means until interrupted')
    p.add_argument('--wait-seconds',type=int,default=25)
    a=p.parse_args();root=Path.cwd();settings=json.loads((root/a.config).read_text())
    if not 1<=a.wait_seconds<=30 or a.max_batches<0:p.error('wait-seconds must be 1..30; max-batches must be nonnegative')
    routes=list(route_configs(settings))
    if a.account_id is not None or a.conversation_id is not None:
        routes=[r for r in routes if r[0]['accountId']==a.account_id and r[0]['group']==a.conversation_id]
    if len(routes)!=1:p.error('Select exactly one route using --account-id and --conversation-id')
    config,state_name=routes[0]
    selector={'account_id':config['accountId'],'conversation_id':config['group']}
    token=(root/'local/runtime/http-token').read_text().strip()
    def api(path,data=None):
        req=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},
            data=None if data is None else json.dumps(data).encode())
        with urlopen(req,timeout=120) as r:return json.load(r)
    inbox=Inbox(root,config,a.name,state_name)
    try:
        batches=0
        while True:
            fetched=inbox.ingest(api('/v1/events?'+urlencode({**selector,'limit':200,'after':inbox.cursor,
                'wait_seconds':a.wait_seconds if a.follow else 0})))
            hydrated=inbox.hydrate(lambda mid:api('/v1/attachments',{**selector,'message_id':mid}),include_self=a.hydrate_self)
            print(json.dumps({'fetched':fetched,'hydration':hydrated,**inbox.summary()},ensure_ascii=False),flush=True)
            batches+=1
            if not a.follow or (a.max_batches and batches>=a.max_batches):break
    except KeyboardInterrupt:
        pass
    finally:inbox.close()
if __name__=='__main__':main()

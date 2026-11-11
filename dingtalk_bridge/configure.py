"""Prepare configuration offline; never starts monitoring or sends a message."""
import argparse
import json
import os
from pathlib import Path
from .routing import route_configs
from .core import DWS, BridgeError


def migrate(config):
    if 'routes' in config:
        list(route_configs(config))
        return config
    if not isinstance(config.get('group'),str) or not config['group']:
        raise ValueError('Legacy config requires a stable group ID')
    route={**config,'accountId':config.get('accountId','default'),
           'conversationId':config['group'],'conversationType':'group','stateStorage':'legacy'}
    route.pop('group')
    result={'schemaVersion':2,'routes':[route]}
    list(route_configs(result))
    return result


def select(config,account_id,conversation_id,kind,peer_id=None,*,dws_factory=DWS,root=Path('.')):
    result=migrate(config)
    accounts=[c for c,_ in route_configs(result) if c['accountId']==account_id]
    if not accounts:raise ValueError('Unknown account; configure its authentication profile first')
    if any(c['group']==conversation_id for c in accounts):raise ValueError('Conversation already configured')
    base=accounts[0]
    if kind=='group':args=['--group',conversation_id]
    elif kind=='direct' and peer_id:args=['--open-dingtalk-id',peer_id]
    else:raise ValueError('Direct route needs an explicitly resolved peer openDingTalkId')
    info=dws_factory(root,base).call(['chat','+conversation-info',*args]).get('result',{}).get('conversationInfo',{})
    if info.get('openConversationId')!=conversation_id:raise BridgeError('Resolved conversation identity mismatch')
    route={key:base[key] for key in ('accountId','profile','binary','selfSenderId','historyTimezone') if key in base}
    route.update(conversationId=conversation_id,conversationType=kind,name=info.get('name',''))
    if kind=='direct':route['peerOpenDingTalkId']=peer_id
    result={**result,'routes':[*result['routes'],route]}
    list(route_configs(result))
    return result


def write_config(path,config):
    # Exclusive create: live config/credentials cannot accidentally be overwritten.
    with Path(path).open('x') as f:
        os.chmod(path,0o600)
        json.dump(config,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default='local/service-config.json');p.add_argument('--output',required=True)
    sub=p.add_subparsers(dest='action',required=True);sub.add_parser('migrate')
    s=sub.add_parser('select');s.add_argument('--account-id',required=True);s.add_argument('--conversation-id',required=True)
    s.add_argument('--type',choices=['group','direct'],required=True);s.add_argument('--peer-id')
    a=p.parse_args();config=json.loads(Path(a.config).read_text())
    result=migrate(config) if a.action=='migrate' else select(config,a.account_id,a.conversation_id,a.type,a.peer_id)
    write_config(a.output,result)
    print(json.dumps({'prepared':True,'route_count':len(result['routes']),'activated':False,'state_moved':False}))


if __name__=='__main__':main()

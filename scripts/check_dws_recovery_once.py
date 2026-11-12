#!/usr/bin/env python3
"""Prepare, then explicitly authorize ONE supervised conversation-info read.

The workspace stays suspended. No login, reset, Stream, sending, or service start.
The prepared key is consumed even when the result is unknown; it never auto-retries.
"""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge import dws_access
from dingtalk_bridge.agent_runtime import timeout_seconds
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.official_tools import private_file


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_private(path, value):
    private_file(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def directory(root,key):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',key):raise ValueError('Invalid recovery key')
    path=Path(root).resolve()/'local/recovery-checks'/key
    if path.is_symlink():raise ValueError('Recovery directory cannot be a symlink')
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    return path


def current_plan(root, config, index, timeout):
    if os.environ.get('DWS_DISABLE_KEYCHAIN'):raise ValueError('File-key mode is not allowed for this recovery check')
    root=Path(root).resolve();config=(root/config).resolve()
    config.relative_to(root)
    timeout_seconds({'timeoutSeconds':timeout})
    if timeout>15:raise ValueError('Read check timeout must not exceed 15 seconds')
    routes=list(route_configs(json.loads(config.read_text())))
    if type(index) is not int or not 0<=index<len(routes):raise ValueError('Invalid route index')
    route=routes[index][0];binary=(root/route['binary']).resolve()
    if not binary.is_file() or not os.access(binary,os.X_OK):raise ValueError('Configured binary unavailable')
    package=Path(dws_access.__file__).parent
    plan={'schemaVersion':1,'config':str(config.relative_to(root)),'configSha256':digest(config),
          'routeIndex':index,'binarySha256':digest(binary),'timeoutSeconds':timeout,
          'packageSha256':{p.name:digest(p) for p in sorted(package.glob('*.py'))},
          'checkerSha256':digest(__file__),
          'dwsEnvironmentSha256':hashlib.sha256(json.dumps({k:v for k,v in os.environ.items() if k.startswith('DWS_')},sort_keys=True).encode()).hexdigest(),
          'operation':'chat +conversation-info','maxInvocations':1,'keepsSuspended':True}
    return plan,route,binary


def prepare(root,key,config='local/service-config.json',index=0,timeout=15):
    plan,_,_=current_plan(root,config,index,timeout)
    folder=directory(root,key);path=folder/'plan.json'
    if path.exists():
        if json.loads(path.read_text())!=plan:raise ValueError('Prepared plan differs; refusing overwrite')
    else:write_private(path,plan)
    return plan


def execute(root,key,*,allow_credential_read=False):
    if not allow_credential_read:raise ValueError('Explicit permission for one credential-backed read is required')
    root=Path(root).resolve();folder=directory(root,key)
    plan=json.loads((folder/'plan.json').read_text());receipt=folder/'receipt.json'
    with (folder/'attempt.lock').open('a') as lock:
        os.chmod(folder/'attempt.lock',0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if receipt.exists():
            prior=json.loads(receipt.read_text())
            if prior['state']=='checking':
                prior={'state':'outcome_unknown','attempted':True,'automaticRetry':False};write_private(receipt,prior)
            return {**prior,'replayed':True}
        current,route,binary=current_plan(root,plan['config'],plan['routeIndex'],plan['timeoutSeconds'])
        if current!=plan:raise ValueError('Config, binary or guard changed since preparation')
        access=dws_access.DWSAccess(root)
        with access.lock(timeout=0),ExitStack() as stack:
            if access.status()['state']!='suspended':raise ValueError('Workspace must remain suspended during the check')
            # Exclude all managed RPCs and explicit resume while this one read
            # bypasses the pause. Other callers continue seeing the pause.
            for index in range(2):
                handle=stack.enter_context((access.directory/f'dws-call-{index}.lock').open('a'))
                os.chmod(handle.name,0o600);fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            before=access.status()
            write_private(receipt,{'state':'checking','attempted':True,'automaticRetry':False})
            target=['--open-dingtalk-id',route['peerOpenDingTalkId']] if route.get('conversationType')=='direct' else ['--group',route['group']]
            command=[str(binary),'chat','+conversation-info',*target,'--profile',route['profile'],'--as','user','--format','json']
            try:
                result=dws_access.run_dws(command,cwd=root,timeout=plan['timeoutSeconds'],text=False)
                raw=folder/'raw-result.json'
                write_private(raw,{'exitCode':result.returncode,'stdout':result.stdout.decode('utf-8',errors='replace'),
                                   'stderr':result.stderr.decode('utf-8',errors='replace')})
                try:data=json.loads(result.stdout or result.stderr)
                except (ValueError,UnicodeError):data=None
                failed=(result.returncode!=0 or not isinstance(data,dict) or data.get('ok') in (False,'false')
                        or data.get('success') in (False,'false') or bool(data.get('error')))
                if isinstance(data,dict) and 'outcome' in data and isinstance(data.get('data'),dict):data=data['data']
                info=data.get('result',{}).get('conversationInfo',{}) if isinstance(data,dict) and isinstance(data.get('result',{}),dict) else {}
                healthy=(not failed and isinstance(data,dict) and data.get('ok') not in (False,'false')
                         and data.get('success') not in (False,'false') and isinstance(info,dict)
                         and info.get('openConversationId')==route['group'])
                outcome={'state':'readable' if healthy else 'failed','attempted':True,'automaticRetry':False,
                         'exitCode':result.returncode,'targetMatched':healthy}
            except Exception as exc:
                outcome={'state':'outcome_unknown','attempted':True,'automaticRetry':False,
                         'error':exc.reason if isinstance(exc,dws_access.DWSAccessSuspended) else type(exc).__name__}
            outcome['suspensionUnchanged']=access.status()==before
            write_private(receipt,outcome)
            return outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.')
    parser.add_argument('--key',required=True)
    parser.add_argument('--config',default='local/service-config.json')
    parser.add_argument('--route-index',type=int,default=0)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--allow-credential-read',action='store_true')
    args=parser.parse_args()
    result=execute(args.root,args.key,allow_credential_read=args.allow_credential_read) if args.execute else prepare(args.root,args.key,args.config,args.route_index)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.execute:raise SystemExit(0 if result['state']=='readable' else 1)


if __name__=='__main__':main()

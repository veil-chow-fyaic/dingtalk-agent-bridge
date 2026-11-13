"""Thin runtime-facing office CLI supervisor, not an office API implementation."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge.dws_access import (BridgeError, DWSAccess, DWSAccessSuspended,
                                       credential_failure, response_failed, run_dws)
from dingtalk_bridge.agent_runtime import timeout_seconds

OFFICE_COMMANDS=('doc','todo','calendar','mail','drive','minutes')


def pinned_arguments(arguments, profile):
    args=list(arguments)
    if (not args or '--' in args or not isinstance(profile,str) or ':' not in profile
            or any(c.isspace() or c==',' for c in profile)):
        raise ValueError('official_proxy_invalid_arguments')
    if args[0] not in OFFICE_COMMANDS:
        if args not in (['--help'],['-h'],['--version']) and not (
                len(args)==2 and args[0]=='help' and args[1] in OFFICE_COMMANDS):
            raise ValueError('official_proxy_command_not_enabled')
    # No account/credential mutation or detached event/dev/mcp process is an
    # office command. Explicit identity always stays bound to this task route.
    # v1.0.67 office commands inherit --profile, but not event's --as flag.
    # Reject an explicit --as rather than silently changing the caller's intent.
    forbidden={'--token','--access-token','--client-id','--client-secret','--as'}
    if any(arg.split('=',1)[0] in forbidden for arg in args):
        raise ValueError('official_proxy_credential_override_forbidden')
    for flag,expected in (('--profile',profile),('--format','json')):
        found=[]
        for index,arg in enumerate(args):
            if arg==flag:
                if index+1==len(args):raise ValueError('official_proxy_invalid_arguments')
                found.append(args[index+1])
            elif arg.startswith(flag+'='):found.append(arg.split('=',1)[1])
        if len(found)>1 or (found and found[0]!=expected):raise ValueError('official_proxy_identity_or_format_mismatch')
        if not found:args.extend((flag,expected))
    return args


def execute(root, binary, profile, arguments, *, timeout=600, stop=None):
    try:timeout_seconds({'timeoutSeconds':timeout})
    except ValueError:raise ValueError('official_proxy_invalid_timeout') from None
    args=pinned_arguments(arguments,profile)
    access=DWSAccess(root)
    with access.lease(stop,operation='office') as lease:
        started=time.monotonic()
        try:
            lease.stage('invoking')
            # Preserve the runtime's working directory for local file paths;
            # root selects only the bridge-wide circuit and concurrency slots.
            result=run_dws([str(Path(binary).resolve()),*args],cwd=Path.cwd(),
                           timeout=timeout,stop=stop,text=False)
        except DWSAccessSuspended as exc:
            lease.result(None,None,started,phase='process',reason=exc.reason)
            lease.block(exc.reason);raise
        except OSError:
            lease.result(None,None,started,phase='spawn',reason='spawn_failed')
            raise
        try:data=json.loads(result.stdout or result.stderr)
        except (ValueError,UnicodeError):data=None
        observed=data
        if isinstance(data,dict) and 'outcome' in data and isinstance(data.get('data'),dict) and not response_failed(data,result.returncode):
            observed=data['data']
        lease.result(observed,result.returncode,started,phase='response' if isinstance(observed,dict) else 'decode')
        if credential_failure(observed):lease.block('credential_store_unavailable')
        lease.complete()
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--binary',required=True)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--timeout',type=float,default=600)
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args();forward=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    stop=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stop.set())
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    try:
        result=execute(args.root,args.binary,args.profile,forward,timeout=args.timeout,stop=stop)
    except (BridgeError,ValueError,OSError) as exc:
        reason=exc.reason if isinstance(exc,DWSAccessSuspended) else (
            str(exc) if isinstance(exc,ValueError) else 'official_proxy_unavailable')
        print(json.dumps({'error':{'category':'bridge','code':'official_proxy_blocked','reason':reason},
                          'automaticRetry':False}),file=sys.stderr)
        raise SystemExit(75)
    sys.stdout.buffer.write(result.stdout);sys.stdout.buffer.flush()
    sys.stderr.buffer.write(result.stderr);sys.stderr.buffer.flush()
    raise SystemExit(result.returncode if result.returncode>=0 else 128-result.returncode)


if __name__=='__main__':main()

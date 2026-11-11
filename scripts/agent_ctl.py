#!/usr/bin/env python3
"""Manage this project's local Agent task worker; no login or boot service changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dingtalk_bridge.routing import route_configs

PID=ROOT/'local/agent-worker.pid'
CONFIG=ROOT/'local/agent-config.json'
LOG=ROOT/'local/agent-worker.log'


def select_config(path):
    global CONFIG,PID,LOG
    CONFIG=(ROOT/path).resolve()
    if CONFIG != (ROOT/'local/agent-config.json').resolve():
        key=hashlib.sha256(str(CONFIG).encode()).hexdigest()[:24]
        PID=ROOT/'local'/('agent-worker-'+key+'.pid')
        LOG=ROOT/'local'/('agent-worker-'+key+'.log')
    else:
        PID=ROOT/'local/agent-worker.pid';LOG=ROOT/'local/agent-worker.log'


def owned_pid():
    if not PID.exists():return None
    pid=int(PID.read_text());r=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
    if r.returncode:return None
    if '-m dingtalk_bridge.agent_gateway --config '+str(CONFIG) not in r.stdout:
        raise RuntimeError('PID does not belong to this Agent worker')
    return pid


def status():
    settings=json.loads(CONFIG.read_text())
    routes=list(route_configs(json.loads((ROOT/settings.get('bridgeConfig','local/service-config.json')).read_text())))
    route=next(c for c,_ in routes if c['accountId']==settings['accountId'] and c['group']==settings['conversationId'])
    scope=json.dumps([route['accountId'],route['profile'],route['group'],route.get('conversationType','group')])
    key=hashlib.sha256(scope.encode()).hexdigest()[:24];path=ROOT/'local/agents'/key/'tasks.sqlite3'
    result={'running':owned_pid() is not None,'runtime':settings['runtime']['kind'],'prefix':settings.get('prefix','/agent'),
        'authorized_senders':len(settings['allowedSenderIds']),'allow_self_commands':settings.get('allowSelfCommands',False)}
    if path.exists():
        c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
        try:
            result.update(jobs=dict(c.execute('SELECT state,count(*) FROM jobs GROUP BY state')),
                delivery=dict(c.execute('SELECT state,count(*) FROM outbox GROUP BY state')),
                session_bound=c.execute('SELECT count(*) FROM meta WHERE key="session_id"').fetchone()[0]>0)
        finally:c.close()
    return result


def main():
    os.umask(0o077);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default='local/agent-config.json')
    p.add_argument('action',choices=['start','stop','status']);a=p.parse_args();select_config(a.config)
    if a.action=='status':print(json.dumps(status(),ensure_ascii=False));return
    pid=owned_pid()
    if a.action=='stop':
        if pid:
            os.kill(pid,signal.SIGTERM)
            for _ in range(140):
                if owned_pid() is None:break
                time.sleep(.5)
            else:raise RuntimeError('Worker shutdown still pending')
        print('stopped');return
    if pid:print(json.dumps(status(),ensure_ascii=False));return
    with LOG.open('ab') as log:
        child=subprocess.Popen([sys.executable,'-m','dingtalk_bridge.agent_gateway','--config',str(CONFIG)],cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    PID.write_text(str(child.pid));PID.chmod(0o600)
    time.sleep(.7)
    if child.poll() is not None:raise RuntimeError('Worker exited; inspect '+str(LOG.relative_to(ROOT)))
    print(json.dumps(status(),ensure_ascii=False))


if __name__=='__main__':main()

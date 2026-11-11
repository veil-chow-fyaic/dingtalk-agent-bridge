#!/usr/bin/env python3
"""Start/stop/status of this project's loopback-only experimental bridge."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'local/runtime'
PID = STATE / 'service.pid'


def owned_pid():
    if not PID.exists(): return None
    pid = int(PID.read_text())
    p = subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
    if p.returncode: return None
    if '-m dingtalk_bridge --port 18768' not in p.stdout:
        raise RuntimeError('PID belongs to an unexpected process; refusing to signal it')
    return pid


def status():
    req = urllib.request.Request('http://127.0.0.1:18768/v1/health',headers={
        'Authorization':'Bearer '+(STATE/'http-token').read_text().strip()})
    with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)


def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['start','stop','status'])
    a=p.parse_args()
    if a.action=='status':
        print(json.dumps(status(),ensure_ascii=False));return
    if a.action=='stop':
        pid=owned_pid()
        if pid:
            os.kill(pid,signal.SIGTERM)
            for _ in range(100):
                if owned_pid() is None:break
                time.sleep(1)
            else:raise RuntimeError('Graceful shutdown pending; no force-kill performed')
        print('stopped');return
    if owned_pid():
        print(json.dumps(status(),ensure_ascii=False));return
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (STATE/'service.log').open('ab') as log:
        child=subprocess.Popen([sys.executable,'-m','dingtalk_bridge','--port','18768'],cwd=ROOT,
            stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)
    PID.write_text(str(child.pid));PID.chmod(0o600)
    for _ in range(60):
        if child.poll() is not None:raise RuntimeError('Service exited; inspect local/runtime/service.log')
        try:
            print(json.dumps(status(),ensure_ascii=False));return
        except (OSError,ValueError):time.sleep(.5)
    raise RuntimeError('Startup still pending; inspect service log')


if __name__=='__main__':main()

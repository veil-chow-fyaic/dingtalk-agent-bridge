"""Reusable explicit probes: durable request intent, private raw replies, no blind retries."""
import json
import os
from pathlib import Path
import subprocess
import hashlib

ROOT = Path(__file__).resolve().parents[1]

class Probe:
    def __init__(self, run_id):
        if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
            raise ValueError('Use a simple run ID')
        os.umask(0o077)
        self.config = json.loads((ROOT/'local/service-config.json').read_text())
        if 'routes' in self.config:
            routes=self.config['routes']
            if len(routes)!=1 or routes[0].get('conversationType')!='group':
                raise ValueError('Historical solo probes require exactly one configured group; never choose first')
            self.config={**routes[0],'group':routes[0]['conversationId']}
        self.dir = ROOT/'local/probes'/run_id
        self.dir.mkdir(parents=True,exist_ok=True)
    def call(self, label, args):
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in label):
            raise ValueError('Use a simple probe label')
        path = self.dir/(label+'.json')
        fingerprint=hashlib.sha256(json.dumps([self.config['profile'],self.config['binary'],args],ensure_ascii=False).encode()).hexdigest()
        if path.exists():
            saved=json.loads(path.read_text())
            if saved.get('state') != 'returned' or saved.get('exit') != 0:
                raise RuntimeError(f'{label}: existing failed/unknown request; reconcile, do not replay')
            if saved.get('fingerprint') != fingerprint:
                raise RuntimeError(f'{label}: request changed; refusing cached result or repeat')
            if saved['data'].get('ok') is False or saved['data'].get('success') in (False,'false'):
                raise RuntimeError(f'{label}: cached business failure; reconcile, do not replay')
            return saved['data']
        with path.open('x') as f:
            json.dump({'state':'started','command':args[:2],'fingerprint':fingerprint},f)
        path.chmod(0o600)
        try:
            r=subprocess.run([str(ROOT/self.config['binary']),*args,'--profile',self.config['profile'],'--format','json'],cwd=ROOT,capture_output=True,text=True,timeout=120)
        except subprocess.TimeoutExpired:
            path.write_text(json.dumps({'state':'outcome_unknown','reason':'timeout'}))
            raise
        try:data=json.loads(r.stdout or r.stderr)
        except ValueError:data={'invalidJson':True}
        path.write_text(json.dumps({'state':'returned','exit':r.returncode,'data':data,'stderr':r.stderr,'fingerprint':fingerprint},ensure_ascii=False,indent=2))
        if r.returncode or data.get('ok') is False or data.get('success') in (False,'false'):
            raise RuntimeError(f'{label}: business/CLI failure; see private record')
        return data

def unwrap(data):
    return data['data'] if 'outcome' in data and isinstance(data.get('data'),dict) else data

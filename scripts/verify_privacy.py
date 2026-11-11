#!/usr/bin/env python3
"""Scan staged Git blobs, not the working tree. Reports paths/reasons, never secret values."""
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def known_private_values(root):
    values=set()
    for name in ('service-config.json','agent-config.json','agent-direct-config.json'):
        path=root/'local'/name
        if not path.exists():continue
        def walk(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in {'profile','conversationId','group','selfSenderId','peerOpenDingTalkId','allowedSenderIds'}:
                        parts=item if isinstance(item,list) else [item]
                        for part in parts:
                            if isinstance(part,str):
                                values.add(part)
                                if key=='profile':values.update(part.split(':'))
                    walk(item)
            elif isinstance(value,list):
                for item in value:walk(item)
        walk(json.loads(path.read_text()))
    token=root/'local/runtime/http-token'
    if token.exists():values.add(token.read_text().strip())
    return {v.encode() for v in values if len(v)>=8}

def scan(root):
    values=known_private_values(root);errors=[]
    def git(*args):return subprocess.check_output(['git',*args],cwd=root)
    entries=git('ls-files','--stage','-z').split(b'\0')
    for entry in entries:
        if not entry:continue
        info,name=entry.split(b'\t',1);mode,oid,stage=info.split();name=name.decode()
        path=Path(name)
        if path.parts[0] in {'local','.git'} or path.name.startswith('.env') and path.name!='.env.example' or path.suffix in {'.sqlite','.sqlite3','.db'}:
            errors.append({'path':name,'reason':'private_path'});continue
        if stage!=b'0' or mode==b'120000':
            errors.append({'path':name,'reason':'unmerged_or_symlink'});continue
        data=git('cat-file','blob',oid.decode())
        if any(value in data for value in values):errors.append({'path':name,'reason':'known_private_value'})
        if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',data):
            errors.append({'path':name,'reason':'private_key'})
    return errors

if __name__=='__main__':
    errors=scan(ROOT);print(json.dumps({'ok':not errors,'scope':'all staged blobs','errors':errors}))
    raise SystemExit(bool(errors))

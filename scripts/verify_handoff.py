#!/usr/bin/env python3
"""Offline handoff integrity: local links, JSON, and public-file digests. No network/writes by default."""
import argparse,hashlib,json,re,tomllib
from datetime import date
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'evidence/handoff-manifest.json'

def files():
    chosen=[ROOT/x for x in ['.gitignore','pyproject.toml','config.example.json','config.routes.example.json','config.agent.example.json']]
    chosen.extend(ROOT.glob('*.md'))
    # Optional for historical unlicensed snapshots; new MIT snapshots bind this file.
    project = tomllib.loads((ROOT/'pyproject.toml').read_text()).get('project', {}) if (ROOT/'pyproject.toml').is_file() else {}
    if (ROOT/'LICENSE').exists() or 'LICENSE' in project.get('license-files', []):chosen.append(ROOT/'LICENSE')
    for folder in ['.github','docs','evidence','scripts','tests','dingtalk_bridge','fixtures','api','plans','.githooks','integrations']:
        chosen.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=MANIFEST)
    return sorted(chosen)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-manifest',action='store_true',help='Explicitly regenerate digest ledger after reviewed changes')
    opt=parser.parse_args(); errors=[]; all_files=files()
    for p in all_files:
        if not p.is_file():
            errors.append(f'Missing public file: {p.relative_to(ROOT)}');continue
        if p.suffix=='.json':
            try:json.loads(p.read_text())
            except (ValueError,UnicodeError) as e:errors.append(f'Invalid JSON: {p.relative_to(ROOT)}: {e}')
        if p.suffix=='.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
                target=target.strip('<>');url=urlsplit(target)
                if url.scheme or target.startswith('#') or not url.path:continue
                local=(p.parent/unquote(url.path)).resolve()
                if not local.exists():errors.append(f'Broken link: {p.relative_to(ROOT)} -> {target}')
    current={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in all_files if p.is_file()}
    if opt.write_manifest and not errors:
        MANIFEST.write_text(json.dumps({'schemaVersion':1,'date':date.today().isoformat(),'excluded':['local/','__pycache__/','evidence/handoff-manifest.json'],'sha256':current},ensure_ascii=False,indent=2)+'\n')
    if MANIFEST.exists():
        expected=json.loads(MANIFEST.read_text())['sha256']
        for name in sorted(set(expected)|set(current)):
            if expected.get(name)!=current.get(name):errors.append(f'Changed/missing/untracked handoff file: {name}')
    else:errors.append('Missing handoff manifest')
    print(json.dumps({'ok':not errors,'files':len(all_files),'documents':len(list((ROOT/'docs').glob('*.md'))),'errors':errors},ensure_ascii=False,indent=2))
    raise SystemExit(1 if errors else 0)
if __name__=='__main__':main()

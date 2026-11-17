#!/usr/bin/env python3
"""Check the installed wheel against this checkout, without running any CLI or business call."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def verify(root, distribution):
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    expected = {str(p.relative_to(root / 'dingtalk_bridge')): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (root / 'dingtalk_bridge').rglob('*')
                if p.is_file() and (p.suffix == '.py' or p.parent.name == 'licenses')}
    package = Path(distribution.locate_file('dingtalk_bridge')).resolve()
    if package == (root / 'dingtalk_bridge').resolve():
        raise ValueError('source_checkout_is_not_an_installed_wheel')
    actual = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in package.rglob('*') if p.is_file() and (p.suffix == '.py' or p.parent.name == 'licenses')}
    scripts = {ep.name: ep.value for ep in distribution.entry_points if ep.group == 'console_scripts'}
    checks = {'version': distribution.version == project['version'],
              'requires_python': distribution.metadata['Requires-Python'] == project['requires-python'],
              'runtime_dependencies': (distribution.requires or []) == project['dependencies'],
              'entry_points': scripts == project['scripts'],
              'package_bytes': bool(expected) and actual == expected}
    return {'ok': all(checks.values()), 'checks': checks,
            'scope': 'Installed metadata/package bytes only; no CLI/auth/DWS execution'}

if __name__ == '__main__':
    try:
        result = verify(ROOT, importlib.metadata.distribution('dingtalk-agent-bridge'))
    except (OSError, ValueError, KeyError, importlib.metadata.PackageNotFoundError) as exc:
        result = {'ok': False, 'error': type(exc).__name__}
    print(json.dumps(result))
    raise SystemExit(0 if result['ok'] else 1)

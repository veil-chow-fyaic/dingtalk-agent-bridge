#!/usr/bin/env python3
"""Check the installed wheel against this checkout, without running any CLI or business call."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def license_checks(root, distribution, project):
    metadata = distribution.metadata
    get_all = getattr(metadata, 'get_all', lambda key: [metadata[key]] if key in metadata else None)
    dist = 'dingtalk_agent_bridge-' + project['version'] + '.dist-info/'
    entries = {str(p) for p in (getattr(distribution, 'files', None) or [])
               if str(p).startswith(dist + 'licenses/')}
    expression, names = project.get('license'), project.get('license-files', [])
    if expression is None and not names:
        legacy = not (root / 'LICENSE').exists() and not get_all('License-Expression') and not get_all('License-File') and not entries
        return {'license_metadata': legacy, 'license_bytes': legacy}
    versions = get_all('Metadata-Version') or []
    shape = expression == 'MIT' and names == ['LICENSE']
    header = (shape and len(versions) == 1 and re.fullmatch(r'2\.\d+', versions[0]) is not None
              and int(versions[0].split('.')[1]) >= 4
              and get_all('License-Expression') == ['MIT'] and get_all('License-File') == ['LICENSE']
              and not get_all('License'))
    original = root / 'LICENSE'
    target = Path(distribution.locate_file(dist + 'licenses/LICENSE'))
    content = (shape and entries == {dist + 'licenses/LICENSE'}
               and original.is_file() and not original.is_symlink()
               and target.is_file() and not target.is_symlink()
               and bool(original.read_bytes().strip()) and target.read_bytes() == original.read_bytes())
    return {'license_metadata': header, 'license_bytes': content}


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
    checks.update(license_checks(root, distribution, project))
    return {'ok': all(checks.values()), 'checks': checks,
            'scope': 'Installed metadata/package bytes only; no CLI/auth/DWS execution'}

if __name__ == '__main__':
    try:
        result = verify(ROOT, importlib.metadata.distribution('dingtalk-agent-bridge'))
    except (OSError, ValueError, KeyError, importlib.metadata.PackageNotFoundError) as exc:
        result = {'ok': False, 'error': type(exc).__name__}
    print(json.dumps(result))
    raise SystemExit(0 if result['ok'] else 1)

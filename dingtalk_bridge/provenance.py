"""Startup source/config provenance for managed services; never authentication data.

This records source files at startup and module origins, not a memory dump or an
OS attestation. The manager checks the source set before launch and at readiness.
"""
import hashlib
from pathlib import Path
import os
import sys
import time


def source_manifest(package=None):
    package = Path(package or Path(__file__).parent).resolve()
    files = sorted(package.glob('*.py'))
    if not files:
        raise ValueError('Missing service source files')
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def startup_evidence(config_bytes):
    package = Path(__file__).resolve().parent
    sources = source_manifest(package)
    origins = {}
    for name, module in list(sys.modules.items()):
        spec = getattr(module, '__spec__', None)
        canonical = getattr(spec, 'name', name)
        if canonical == 'dingtalk_bridge' or canonical.startswith('dingtalk_bridge.'):
            path = getattr(module, '__file__', None)
            if not path or Path(path).resolve().parent != package:
                raise ValueError('Mixed service module origins')
            filename = Path(path).name
            if filename not in sources:
                raise ValueError('Service source unavailable')
            origins[canonical] = filename
    return {'schemaVersion': 1, 'pid': os.getpid(), 'at': time.time(),
            'python': sys.version.split()[0], 'sourceSha256': sources, 'moduleOrigins': origins,
            'configSha256': {str(Path(path).resolve()): hashlib.sha256(data).hexdigest()
                             for path, data in config_bytes.items()}}


def verify_startup(record, sources, configs):
    """Missing legacy evidence stays unverified; it does not prevent legacy stop."""
    evidence = record.get('startupEvidence', {})
    try:
        origins = evidence['moduleOrigins']
        module = 'dingtalk_bridge.__main__' if record['module'] == 'dingtalk_bridge' else record['module']
        return (evidence['schemaVersion'] == 1 and evidence['pid'] == record['pid']
            and evidence['sourceSha256'] == record['launchSourceSha256'] == sources
            and bool(sources) and bool(origins)
            and origins.get(module) == module.rsplit('.', 1)[-1] + '.py'
            and all(name in sources for name in origins.values())
            and evidence['configSha256'] == configs
            and configs[record['config']] == record['configSha256'])
    except (KeyError, TypeError, AttributeError):
        return False

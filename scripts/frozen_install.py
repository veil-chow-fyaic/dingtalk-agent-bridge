"""Verify a historical install from its frozen artifacts, independent of HEAD."""
import hashlib
from pathlib import Path
import re
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def module_sources_match(report, package):
    """Informational for current source; authoritative only for the frozen set."""
    try:
        code=report['codeSha256']
        if not isinstance(code,dict) or not code:return False
        if not all(isinstance(n,str) and Path(n).name==n and n.endswith('.py') and
                   isinstance(sha,str) and re.fullmatch('[a-f0-9]{64}',sha) for n,sha in code.items()):return False
        return ({p.name for p in Path(package).glob('*.py')}==set(code) and
                all(digest((Path(package)/n).read_bytes())==sha for n,sha in code.items()))
    except (KeyError,OSError,TypeError):
        return False


def frozen_install_matches(report, folder):
    """Read only. Missing, changed or ambiguous frozen artifacts fail closed."""
    try:
        folder=Path(folder)
        if not isinstance(report,dict):return False
        if report.get('ok') is not True:return False
        entries=report['entrypoints']
        if not isinstance(entries,dict) or set(entries)!={'dab','dab-bridge','dab-agent','dab-consume','dab-doctor','dab-service'} or not all(v is True for v in entries.values()):return False
        if not module_sources_match(report,folder/'clean-source/dingtalk_bridge'):return False
        installed=list((folder/'venv/lib').glob('python*/site-packages/dingtalk_bridge'))
        if len(installed)!=1 or not module_sources_match(report,installed[0]):return False
        wheels=list((folder/'wheels').glob('*.whl'))
        if len(wheels)!=1 or digest(wheels[0].read_bytes())!=report['wheelSha256']:return False
        with zipfile.ZipFile(wheels[0]) as archive:
            expected={'dingtalk_bridge/'+n for n in report['codeSha256']}
            names=[n for n in archive.namelist() if n.startswith('dingtalk_bridge/') and n.endswith('.py')]
            if len(names)!=len(expected) or set(names)!=expected:return False
            return all(digest(archive.read('dingtalk_bridge/'+n))==sha for n,sha in report['codeSha256'].items())
    except (KeyError,OSError,TypeError,ValueError,zipfile.BadZipFile):
        return False

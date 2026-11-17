#!/usr/bin/env python3
"""Export a frozen source commit and a previously tested wheel, entirely offline.

Reads Git objects and the supplied wheel, never local account/credential files.
Checks declared validation evidence; does not rerun or certify those tests.
"""
import argparse
import base64
import configparser
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import tomllib
import zipfile

MANIFEST = 'evidence/handoff-manifest.json'
PACKAGE = 'dingtalk_bridge/'
PRIVATE_KEY = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')


class ReleaseError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    require(bool(name) and not path.is_absolute() and '\\' not in name and
            all(p not in ('', '.', '..') for p in name.split('/')), 'Unsafe archive path')
    require(not any(p in {'local', '.git', '.ssh', '.aws', '__pycache__'} for p in path.parts)
            and not any(p.startswith('.env') and p != '.env.example' for p in path.parts),
            'Private runtime path in export')
    require(path.suffix.lower() not in {'.sqlite', '.sqlite3', '.db'}, 'Database path in export')
    return name


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    require(result.returncode == 0, 'Git export failed (details suppressed)')
    return result.stdout


def source_files(archive):
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        for member in tar.getmembers():
            name = safe_name(member.name.rstrip('/') if member.isdir() else member.name)
            require(member.isfile() or member.isdir(), 'Source links/special files are not allowed')
            if member.isfile():
                require(name not in files, 'Duplicate source path')
                files[name] = tar.extractfile(member).read()
    require(MANIFEST in files, 'Missing handoff manifest')
    manifest = json.loads(files[MANIFEST])
    require(manifest.get('schemaVersion') == 1 and isinstance(manifest.get('sha256'), dict),
            'Unsupported handoff manifest')
    expected = manifest['sha256']
    require(set(files) == set(expected) | {MANIFEST}, 'Source files differ from manifest inventory')
    require(all(digest(files[n]) == h for n, h in expected.items()), 'Source digest differs from manifest')
    require(not any(PRIVATE_KEY.search(data) for data in files.values()), 'Private key marker in source')
    return files


def validation_record(files, name, wheel_hash, modules):
    safe_name(name)
    require(name.startswith('evidence/') and name.endswith('.json') and name in files,
            'Validation must be a manifest-bound public evidence JSON in the selected commit')
    report = json.loads(files[name])
    require(all(report.get(k, True) is True for k in ('ok', 'wheelModulesMatch', 'licensesMatch')),
            'Validation records failed package checks')
    hashes = [report[k] for k in ('wheelSha256', 'candidateWheelSha256') if k in report]
    require(bool(hashes) and all(h == wheel_hash for h in hashes), 'Wheel does not match validation digest')
    if 'codeSha256' in report:
        require(report['codeSha256'] == modules, 'Validation module digests differ from source')
    if 'candidateModules' in report:
        require(report['candidateModules'] == len(modules), 'Validation module inventory differs from source')
    rows = report.get('validation', report.get('results'))
    require(isinstance(rows, list) and bool(rows), 'No declared test results in validation')
    require(all(isinstance(row, dict) and row.get('ok') is True and
                type(row.get('exitCode')) is int and row['exitCode'] == 0 and
                type(row.get('testsRun')) is int and row['testsRun'] > 0 for row in rows),
            'Validation contains missing or failed test results')
    labels = [row.get('label') for row in rows]
    require(all(isinstance(label, str) for label in labels) and len(set(labels)) == len(labels)
            and {'source', 'py314', 'py311'} <= set(labels), 'Missing or duplicate supported validation environments')
    require(all(row.get(k, True) is True for row in rows for k in ('modulesMatch', 'sourcePackageAbsent')),
            'Validation records failed installed-package isolation')
    # Preserve actual scopes/counts; do not infer that later scripts/docs had a full rerun.
    return {'path': name, 'sha256': digest(files[name]), 'evidence': report.get('evidence'),
            'declaredResults': [{k: row[k] for k in ('label', 'testsRun', 'exitCode', 'ok') if k in row}
                                for row in rows]}


def wheel_files(wheel):
    files = {}
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        for member in archive.infolist():
            safe_name(member.filename.rstrip('/') if member.is_dir() else member.filename)
            mode = member.external_attr >> 16
            require(not stat.S_ISLNK(mode) and (not stat.S_IFMT(mode) or
                    stat.S_ISREG(mode) or member.is_dir()), 'Wheel links/special files are not allowed')
            if not member.is_dir():
                require(member.filename not in files, 'Duplicate wheel path')
                files[member.filename] = archive.read(member)
    return files


def license_payload(project, source, metadata, dist):
    """Support the historical no-license layout and the explicit MIT/PEP 639 layout."""
    expression = project.get('license')
    names = project.get('license-files', [])
    if expression is None and not names:
        require('LICENSE' not in source and not metadata.get_all('License-Expression')
                and not metadata.get_all('License-File'), 'Unconfigured license metadata or payload')
        return {}
    require(expression == 'MIT' and names == ['LICENSE'], 'Unsupported release license configuration')
    require('LICENSE' in source and bool(source['LICENSE'].strip()), 'Missing or empty source LICENSE')
    versions = metadata.get_all('Metadata-Version') or []
    require(len(versions) == 1 and re.fullmatch(r'2\.\d+', versions[0])
            and int(versions[0].split('.')[1]) >= 4, 'PEP 639 requires Metadata-Version >= 2.4')
    require(metadata.get_all('License-Expression') == ['MIT']
            and metadata.get_all('License-File') == ['LICENSE']
            and not metadata.get_all('License'), 'Wheel license metadata differs from pyproject')
    return {dist + 'licenses/LICENSE': source['LICENSE']}


def verify_wheel(wheel, filename, source):
    files = wheel_files(wheel)
    project = tomllib.loads(source['pyproject.toml'].decode())['project']
    require(project['name'] == 'dingtalk-agent-bridge', 'Unexpected project name')
    version = project['version']
    dist = 'dingtalk_agent_bridge-' + version + '.dist-info/'
    require(filename == 'dingtalk_agent_bridge-' + version + '-py3-none-any.whl',
            'Wheel filename/version/tag differs from project')
    payload = {n: b for n, b in source.items() if n.startswith(PACKAGE)}
    require(bool(payload) and {n: b for n, b in files.items() if n.startswith(PACKAGE)} == payload,
            'Wheel package content differs from frozen source (modules or resources)')
    metadata_names = {dist + n for n in ('METADATA', 'WHEEL', 'entry_points.txt', 'top_level.txt', 'RECORD')}
    require(metadata_names <= set(files), 'Missing wheel metadata files')
    metadata = BytesParser().parsebytes(files[dist + 'METADATA'])
    licenses = license_payload(project, source, metadata, dist)
    require(set(files) == set(payload) | metadata_names | set(licenses), 'Unexpected or missing wheel files')
    require(all(files[n] == expected for n, expected in licenses.items()),
            'Wheel license content differs from frozen source')
    require(metadata.get_all('Name') == [project['name']] and metadata.get_all('Version') == [version]
            and metadata.get_all('Requires-Python') == [project['requires-python']],
            'Wheel name/version/Python constraint differs from pyproject')
    require(project.get('dependencies', []) == [] and not metadata.get_all('Requires-Dist'),
            'Release exporter currently supports the standard-library-only package')
    wheel_metadata = BytesParser().parsebytes(files[dist + 'WHEEL'])
    require(wheel_metadata.get_all('Root-Is-Purelib') == ['true'] and
            wheel_metadata.get_all('Tag') == ['py3-none-any'], 'Unexpected wheel installation layout')
    config = configparser.ConfigParser(interpolation=None);config.optionxform = str
    config.read_string(files[dist + 'entry_points.txt'].decode())
    require(config.sections() == ['console_scripts'] and
            dict(config['console_scripts']) == project['scripts'], 'Wheel CLI entry points differ from pyproject')
    require(files[dist + 'top_level.txt'].decode().strip() == 'dingtalk_bridge', 'Unexpected top-level package')
    records = list(csv.reader(io.StringIO(files[dist + 'RECORD'].decode())))
    require(all(len(row) == 3 for row in records) and len({row[0] for row in records}) == len(records)
            and {row[0] for row in records} == set(files), 'Wheel RECORD inventory differs')
    for name, value, size in records:
        if name == dist + 'RECORD':
            require(value == size == '', 'Wheel RECORD must not self-hash')
        else:
            expected = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).rstrip(b'=').decode()
            require(value == expected and size == str(len(files[name])), 'Wheel RECORD digest/size differs')
    require(not any(PRIVATE_KEY.search(data) for data in files.values()), 'Private key marker in wheel')
    return project


def export(repo, ref, wheel_path, validation_path, output):
    """Validate all inputs before reserving an output directory; never overwrite it."""
    repo, wheel_path, output = Path(repo), Path(wheel_path), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Output already exists')
    require(output.parent.is_dir(), 'Output parent directory must already exist')
    commit = git(repo, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()
    tree = git(repo, 'rev-parse', commit + '^{tree}').decode().strip()
    archive = git(repo, 'archive', '--format=tar.gz', commit)
    source = source_files(archive)
    wheel = wheel_path.read_bytes()
    project = verify_wheel(wheel, wheel_path.name, source)
    modules = {n[len(PACKAGE):]: digest(b) for n, b in source.items() if n.startswith(PACKAGE) and n.endswith('.py')}
    validation = validation_record(source, validation_path, digest(wheel), modules)
    report = {'schemaVersion': 1, 'sourceCommit': commit, 'sourceTree': tree,
              'sourceArchiveSha256': digest(archive), 'wheelSha256': digest(wheel),
              'productModuleSha256': modules, 'packageVersion': project['version'],
              'requiresPython': project['requires-python'], 'entryPoints': project['scripts'],
              'manifestEntries': len(source) - 1, 'sourceFiles': len(source), 'validation': validation,
              'fullProductAcceptance': False,
              'limits': ['Checks committed validation declarations; does not rerun or attest tests',
                         'Source docs/scripts may postdate the tested product; package bytes must match',
                         'Only selected Git objects are exported; uncommitted/untracked files are not inputs',
                         'Private-path/key-marker checks do not replace known-secret staged privacy review',
                         'No credentials, account configuration, live service, deployment or UI validation performed']}
    readme = (f"DingTalk bridge delivery candidate; not final product acceptance.\n"
              f"Source commit: {commit}\nPackage: {project['version']}; Python {project['requires-python']}\n"
              f"Verify SHA256SUMS.txt and CHECKS.json before use.\n"
              f"Install offline in a new virtual environment:\n"
              f"  python3 -m venv .venv\n"
              f"  .venv/bin/python -m pip install --no-index --no-deps ./{wheel_path.name}\n"
              f"Extract source.tar.gz and read docs/15-service-runbook.md and config templates.\n"
              f"Configure your own official DWS binary, authorized account and conversations.\n"
              f"DWS, account data, model credentials and operating-system autostart are not included.\n"
              f"CLI/HTTP/consumer work independently; the agent gateway is optional.\n"
              f"A code rollback must preserve current ledgers and respect runtime/config compatibility.\n"
              f"The validation record applies to the matched wheel, not every later source script or document.\n")
    artifacts = {'source.tar.gz': archive, wheel_path.name: wheel, 'README.txt': readme.encode(),
                 'CHECKS.json': (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode()}
    artifacts['SHA256SUMS.txt'] = ''.join(digest(b) + '  ' + n + '\n' for n, b in sorted(artifacts.items())).encode()
    # mkdir is the exclusive reservation. Completion marker appears only after all files;
    # if writing fails, keep partial evidence without a marker and refuse reuse of that path.
    output.mkdir(mode=0o700)
    for name, data in artifacts.items():
        with (output / name).open('xb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
    with (output / '.completion.tmp').open('x') as handle:
        json.dump({'schemaVersion': 1, 'checksSha256': digest(artifacts['CHECKS.json']),
                   'sumsSha256': digest(artifacts['SHA256SUMS.txt'])}, handle)
        handle.write('\n');handle.flush();os.fsync(handle.fileno())
    os.link(output / '.completion.tmp', output / 'COMPLETE.json')
    (output / '.completion.tmp').unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--commit', required=True, help='Frozen Git commit/ref; never exports the working tree')
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--validation', required=True, help='Public evidence JSON path within that commit')
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing output is refused')
    args = parser.parse_args()
    try:
        result = export(args.repo, args.commit, args.wheel, args.validation, args.output)
    except ReleaseError as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, zipfile.BadZipFile, configparser.Error):
        # Suppress arbitrary input/command text that could contain sensitive data.
        print(json.dumps({'ok': False, 'error': 'Release validation/export failed; no completion should be assumed'}))
        return 1
    print(json.dumps({'ok': True, 'sourceCommit': result['sourceCommit'], 'sourceTree': result['sourceTree'],
                      'wheelSha256': result['wheelSha256'], 'fullProductAcceptance': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

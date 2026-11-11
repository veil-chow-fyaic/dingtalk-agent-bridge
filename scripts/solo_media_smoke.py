#!/usr/bin/env python3
"""Explicitly invoked, scoped media round-trip probe. Never retries a send.

Run from this project: python3 scripts/solo_media_smoke.py --execute
Requires local/target.json from verified target discovery. Raw replies stay local.
Existing send records stop replay; inspect/reconcile them before a new experiment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
CLI = Path.home() / '.local/bin/dws'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Requires --execute: sends five synthetic attachments to the verified test group')
    os.chdir(ROOT)
    os.umask(0o077)
    cfg = json.loads(Path('local/target.json').read_text())
    if cfg['name'] != '深圳市弗忧智能科技有限公司' or cfg['groupType'] != 'INTERNAL_GROUP':
        raise RuntimeError('Unexpected test target; resolve manually')
    version = subprocess.check_output([str(CLI), '--version'], text=True)
    if cfg['cliVersion'] not in version:
        raise RuntimeError('Version changed; refresh baseline before testing')
    work = Path('local/solo-media-20261111')
    work.mkdir(exist_ok=True)
    records = []
    cases = [('image', 'file', 'png'), ('document', 'file', 'pdf'),
             ('archive', 'file', 'zip'), ('audio', 'audio', 'wav'), ('video', 'video', 'mp4')]

    def call(label, params):
        log = work / (label + '.json')
        if log.exists():
            raise RuntimeError(f'Existing record {label}; reconcile instead of replay')
        # Persist intent before launching any request; a crash cannot silently resend.
        save(log, {'state': 'started'})
        try:
            p = subprocess.run([str(CLI), 'chat', *params, '--profile', cfg['profile'],
                                '--format', 'json'], capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            save(log, {'state': 'outcome_unknown', 'reason': 'timeout'})
            raise
        save(log, {'state': 'returned', 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
        if p.returncode:
            raise RuntimeError(f'{label} failed; inspect local record, do not resend')
        return json.loads(p.stdout)

    for name, msg_type, ext in cases:
        source = Path(f'fixtures/dab-{name}-001.{ext}')
        if (work / (name + '-intent.json')).exists() or (work / (name + '-send.json')).exists():
            raise RuntimeError(f'Existing intent for {name}; reconcile instead of replay')
        key = str(uuid.uuid4())
        save(work / (name + '-intent.json'), {'key': key, 'fixture': str(source)})
        sent = call(name + '-send', ['+messages-send', '--as', 'user', '--group', cfg['group'],
                    '--msg-type', msg_type, '--file', str(source), '--idempotency-key', key, '--yes'])
        task = sent['sendReceipt']['openTaskId']
        status = call(name + '-status', ['+messages-query-send-status', '--open-task-id', task])
        if status.get('result', {}).get('sendStatus') != 'SUCCESS':
            raise RuntimeError('Send is not confirmed; reconcile before continuing')
        mid = status['messageRef']['openMessageId']
        output = str(work / (name + '-download'))
        fetched = call(name + '-download', ['+messages-mget', '--msg-ids', mid,
                       '--download-resources', '--output-dir', output])
        downloaded = fetched.get('resourceDownloads', {})
        files = downloaded.get('downloads', [])
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        equal = len(files) == 1 and hashlib.sha256(Path(files[0]['localPath']).read_bytes()).hexdigest() == digest
        text = fetched.get('messages', [{}])[0].get('text', '')
        row = {'case': name, 'requestedType': msg_type, 'fixture': str(source),
               'bytes': source.stat().st_size, 'sha256': digest, 'sendStatus': 'SUCCESS',
               'downloadedCount': downloaded.get('downloadedCount'), 'sha256Equal': equal,
               'historyShowsFile': text.startswith('[文件]'), 'peerDelivery': 'skipped_by_user'}
        records.append(row)
        save(work / 'summary.json', records)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if not equal:
            raise RuntimeError('Attachment integrity mismatch; investigate before continuing')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Probe pinned DWS send parsing/plans, with synthetic targets and mandatory dry-run.

No profile, credentials, confirmation flag, real conversation, upload, or send.
This verifies CLI contracts, not server support or client rendering/downloads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.67'


def cases():
    def images(n, same=False):
        return 'before ' + ' middle '.join(
            f'![image-{i}](./missing-{0 if same else i}.png)' for i in range(n)) + ' after'

    return [
        ('one_file', ['--file', 'a.txt'], {'file': 'a.txt', 'requested': 'file'}),
        ('repeat_file_last_b', ['--file', 'a.txt', '--file', 'b.txt'], {'file': 'b.txt', 'requested': 'file'}),
        ('repeat_file_last_a', ['--file', 'b.txt', '--file', 'a.txt'], {'file': 'a.txt', 'requested': 'file'}),
        ('file_alias_conflict', ['--file', 'a.txt', '--file-path', 'b.txt'], {'reject': '互斥'}),
        ('comma_is_not_file_array', ['--file', 'a.txt,b.txt'], {'reject': 'a.txt,b.txt: no such file', 'code': 5, 'category': 'internal'}),
        ('json_is_not_file_array', ['--file', '["a.txt","b.txt"]'], {'reject': '["a.txt","b.txt"]: no such file', 'code': 5, 'category': 'internal'}),
        ('text_and_file', ['--text', 'caption', '--file', 'a.txt'], {'reject': '互斥'}),
        ('markdown_and_file', ['--markdown', 'caption', '--file', 'a.txt'], {'reject': '互斥'}),
        ('audio_maps_to_file', ['--msg-type', 'audio', '--file', 'a.txt'], {'file': 'a.txt', 'requested': 'audio'}),
        ('video_maps_to_file', ['--msg-type', 'video', '--file', 'a.txt'], {'file': 'a.txt', 'requested': 'video'}),
        ('native_voice_enum_absent', ['--msg-type', 'voice', '--file', 'a.txt'], {'reject': ''}),
        ('two_local_images', ['--markdown', images(2)], {'images': 2, 'unique': 2}),
        ('nine_local_images', ['--markdown', images(9)], {'images': 9, 'unique': 9}),
        ('ten_local_images', ['--markdown', images(10)], {'reject': '单条消息最多支持 9 张本地图片', 'code': 5, 'category': 'internal'}),
        ('nine_repeated_image_refs', ['--markdown', images(9, True)], {'images': 9, 'unique': 1}),
        ('ten_repeated_image_refs', ['--markdown', images(10, True)], {'reject': '单条消息最多支持 9 张本地图片', 'code': 5, 'category': 'internal'}),
        ('reference_image_syntax', ['--markdown', '![image][a]\n\n[a]: ./missing.png'], {'reject': '引用式本地图片暂不支持', 'code': 5, 'category': 'internal'}),
        ('file_links_remain_markdown', ['--markdown', '[A](a.txt) [B](b.txt)'], {'markdown': '[A](a.txt) [B](b.txt)'}),
    ]


def validate_case(result, expected):
    """Fail closed on wrong plans, missing execution flags, or transport/auth errors."""
    data = result.get('data', {})
    if 'reject' in expected:
        error = data.get('error', {})
        # v1.0.67 reports some local-input limits as internal/5. Preserve the
        # precise category and diagnostic; auth/network failures cannot pass.
        return (result['exitCode'] == expected.get('code', 3)
                and error.get('code') == expected.get('code', 3)
                and error.get('category') == expected.get('category', 'validation')
                and expected['reject'] in error.get('message', ''))
    if (result['exitCode'] != 0 or data.get('dry_run') is not True
            or data.get('executed') is not False or data.get('preview_kind') != 'plan'):
        return False
    if 'images' in expected:
        return (data.get('tool') == 'send_personal_message'
                and data.get('imageCount') == expected['images']
                and data.get('uniquePathCount') == expected['unique'])
    actions = data.get('actions', [])
    if 'file' in expected:
        return (len(actions) == data.get('actionCount') == 2
                and actions[0].get('tool') == 'init/commit_conversation_file_upload'
                and actions[0].get('file', {}).get('name') == expected['file']
                and actions[0].get('file', {}).get('path') == expected['file']
                and actions[1].get('tool') == 'send_personal_message'
                and actions[1].get('requestedMessageType') == expected['requested']
                and actions[1].get('effectiveMessageType') == 'file')
    if 'markdown' in expected:
        if len(actions) != 1 or actions[0].get('tool') != 'send_personal_message':
            return False
        args = actions[0].get('arguments', {})
        try:
            content = json.loads(args.get('content', ''))
        except (TypeError, ValueError):
            return False
        return args.get('msgType') == 'markdown' and content.get('text') == expected['markdown']
    return False


def run(binary):
    results = []
    with tempfile.TemporaryDirectory(prefix='dab-dws-send-contract-') as tmp, socket.socket() as blocker:
        work = Path(tmp).resolve()
        blocker.bind(('127.0.0.1', 0))  # Reserved, not listening; never a live proxy.
        proxy = 'http://127.0.0.1:' + str(blocker.getsockname()[1])
        env = {'PATH': os.defpath, 'DWS_CONFIG_DIR': str(work / 'empty-config'),
               'HTTP_PROXY': proxy, 'HTTPS_PROXY': proxy, 'ALL_PROXY': proxy, 'NO_PROXY': ''}
        for name in ('a.txt', 'b.txt'):
            (work / name).write_text('synthetic-' + name + '\n')
        version = subprocess.run([str(binary), '--version'], env=env, cwd=work,
                                 capture_output=True, text=True, timeout=20)
        version_match = re.match(r'^dws version v([^ ]+) \(', version.stdout)
        if version.returncode or not version_match or version_match[1] != VERSION:
            raise ValueError('This probe requires the pinned official DWS ' + VERSION)
        for name, tail, expected in cases():
            argv = ['chat', '+messages-send', '--as', 'user', '--group', 'synthetic-offline-target',
                    '--dry-run', '--format', 'json', *tail]
            proc = subprocess.run([str(binary), *argv], cwd=work, env=env,
                                  capture_output=True, text=True, timeout=20)
            stdout = proc.stdout.replace(str(work), '<temporary-workspace>')
            stderr = proc.stderr.replace(str(work), '<temporary-workspace>')
            try:
                data = json.loads(stdout if proc.returncode == 0 else stderr)
            except ValueError:
                data = {}
            result = {'name': name, 'argv': argv, 'expected': expected,
                      'exitCode': proc.returncode, 'data': data,
                      'stdoutSha256': hashlib.sha256(stdout.encode()).hexdigest(),
                      'stderrSha256': hashlib.sha256(stderr.encode()).hexdigest()}
            result['ok'] = validate_case(result, expected)
            results.append(result)
    return {'version': VERSION, 'binarySha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'ok': all(r['ok'] for r in results), 'caseCount': len(results), 'cases': results,
            'controls': {'everyCaseDryRun': True, 'syntheticTargetOnly': True,
                         'emptyIsolatedConfig': True, 'credentialEnvInherited': False,
                         'confirmationFlagUsed': False, 'proxy': 'reserved-unlistening-loopback'},
            'limits': ['CLI parser/plan evidence only; no server, native UI or download validation',
                       'audio/video use a text fixture to inspect mapping only, not media validity',
                       'missing image paths intentionally prove dry-run is not image validation',
                       'Only the pinned official user send shortcut is covered; no platform-wide impossibility claim']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT / 'local/bin/v1.0.67/dws')
    parser.add_argument('--output', type=Path, help='Optional explicit JSON report destination')
    opt = parser.parse_args()
    report = run(opt.binary.resolve())
    if opt.output:
        opt.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': report['ok'], 'caseCount': report['caseCount'],
                      'failed': [r['name'] for r in report['cases'] if not r['ok']]}, ensure_ascii=False))
    raise SystemExit(0 if report['ok'] else 1)

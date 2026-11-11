#!/usr/bin/env python3
"""Capture version and local help only; no login, subscription or messaging."""
import argparse
import datetime
import hashlib
import json
import plistlib
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cli = shutil.which('dws')
    summary = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
               'scope': 'version-and-help-only', 'dws_found': bool(cli), 'commands': []}
    app_info = Path('/Applications/DingTalk.app/Contents/Info.plist')
    if app_info.exists():
        with app_info.open('rb') as handle:
            info = plistlib.load(handle)
        summary['app'] = {key: info.get(key) for key in
                          ('CFBundleIdentifier', 'CFBundleShortVersionString', 'CFBundleVersion')}
    commands = {
        'dws-version': ['--version'],
        'auth-login-help': ['auth', 'login', '--help'],
        'auth-status-help': ['auth', 'status', '--help'],
        'listen-im-help': ['event', '+listen-im', '--help'],
        'messages-send-help': ['chat', '+messages-send', '--help'],
        'chat-messages-help': ['chat', '+chat-messages', '--help'],
    }
    if cli:
        for label, command in commands.items():
            try:
                result = subprocess.run([cli, *command], capture_output=True, text=True, timeout=20)
                # Only successful local help/version stdout is retained; never retain arbitrary errors.
                row = {'command': ['dws', *command], 'exit_code': result.returncode,
                       'stderr_present': bool(result.stderr)}
                if result.returncode == 0:
                    target = output / (label + '.txt')
                    target.write_text(result.stdout, encoding='utf-8')
                    row['file'] = target.name
                    row['sha256'] = hashlib.sha256(result.stdout.encode()).hexdigest()
                summary['commands'].append(row)
            except subprocess.TimeoutExpired:
                summary['commands'].append({'command': ['dws', *command], 'result': 'timeout'})
    (output / 'baseline.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'commands_captured': len(summary['commands'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build an isolated supplement from a verified DWS checkout. Never replaces DWS."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

UPSTREAM_COMMIT = '63a7c4906c7dee10750011ea309b9eb78abb7eb0'
HERE = Path(__file__).resolve().parent


def read_receipt(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise SystemExit('Refusing non-regular build receipt')
    if not path.exists():
        return {}
    try:
        receipt = json.loads(path.read_text())
        fields = ('addonSha256', 'binarySha256')
        if isinstance(receipt, dict) and 'testSha256' in receipt:
            fields += ('testSha256',)
        if (not isinstance(receipt, dict) or receipt.get('upstreamCommit') != UPSTREAM_COMMIT
                or receipt.get('command') != 'chat bridge-image-upload'
                or any(not isinstance(receipt.get(k), str) or len(receipt[k]) != 64
                       or any(c not in '0123456789abcdef' for c in receipt[k]) for k in fields)):
            raise ValueError('invalid ownership receipt')
        return receipt
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit('Refusing invalid build receipt') from exc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--go', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.is_symlink():
        raise SystemExit('Refusing symlink output')
    source, output = args.source.resolve(), args.output.resolve()
    receipt_path = output.with_suffix('.build.json')
    previous = read_receipt(receipt_path)
    replaced_verified_output = output.exists()
    if replaced_verified_output and (not output.is_file() or not previous
            or hashlib.sha256(output.read_bytes()).hexdigest() != previous['binarySha256']):
        raise SystemExit('Refusing to overwrite unowned or changed output')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    if commit != UPSTREAM_COMMIT:
        raise SystemExit('Expected exact upstream v1.0.67 commit')
    base = subprocess.check_output(['git', 'show', 'HEAD:internal/helpers/chat.go'], cwd=source)
    anchor = b'\troot.AddCommand(chatChmodCmd,'
    if base.count(anchor) != 1:
        raise SystemExit('Unexpected upstream registration')
    patched = base.replace(anchor, b'\troot.AddCommand(newBridgeImageUploadCommand())\n'+anchor)
    chat = source / 'internal/helpers/chat.go'
    addon = source / 'internal/helpers/bridge_image_upload.go'
    addon_test = source / 'internal/helpers/bridge_image_upload_test.go'
    expected_addon = (HERE / 'bridge_image_upload.go').read_bytes()
    expected_test = (HERE / 'bridge_image_upload_test.go').read_bytes()
    if any(p.is_symlink() or (p.exists() and not p.is_file()) for p in (chat, addon, addon_test)):
        raise SystemExit('Refusing non-regular generated source')
    existing_addon_ok = not addon.exists() or addon.read_bytes() == expected_addon or (
        previous.get('upstreamCommit') == commit and
        hashlib.sha256(addon.read_bytes()).hexdigest() == previous.get('addonSha256'))
    existing_test_ok = not addon_test.exists() or addon_test.read_bytes() == expected_test or (
        previous.get('upstreamCommit') == commit and
        hashlib.sha256(addon_test.read_bytes()).hexdigest() == previous.get('testSha256'))
    if chat.read_bytes() not in (base, patched) or not existing_addon_ok or not existing_test_ok:
        raise SystemExit('Refusing to overwrite source edits')
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).splitlines()
    if set(changed) - {'internal/helpers/chat.go'}:
        raise SystemExit('Unexpected upstream modifications')
    chat.write_bytes(patched)
    shutil.copyfile(HERE / 'bridge_image_upload.go', addon)
    shutil.copyfile(HERE / 'bridge_image_upload_test.go', addon_test)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([args.go, 'test', './internal/helpers', '-run', '^TestCrossPlatformCoverageBridgeImage', '-count=1'], cwd=source, check=True)
    subprocess.run([args.go, 'test', './internal/app', '-run', '^TestRuntimeSchemaCompleteness', '-count=1'], cwd=source, check=True)
    subprocess.run([args.go, 'build', '-trimpath', '-ldflags',
                    '-X github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/app.version=1.0.67-bridge-image.1',
                    '-o', str(output), './cmd'], cwd=source, check=True)
    receipt = {'upstreamCommit': commit, 'addonSha256': hashlib.sha256(expected_addon).hexdigest(),
               'testSha256': hashlib.sha256(expected_test).hexdigest(),
               'binarySha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'go': subprocess.check_output([args.go, 'version'], text=True).strip(),
               'command': 'chat bridge-image-upload', 'replacedVerifiedOutput': replaced_verified_output}
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()

"""Public repository boundary checks; synthetic files and Git indexes only."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import review_documentation as docs
import verify_handoff as handoff
import verify_privacy as privacy
import verify_ci_install as installed


class RepositoryGateTests(unittest.TestCase):
    def test_new_root_and_github_documents_enter_both_inventories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md', '.github/PULL_REQUEST_TEMPLATE.md']
            for name in names:
                path = root / name;path.parent.mkdir(parents=True, exist_ok=True);path.write_text('Synthetic public document\n')
            workflow = root / '.github/workflows/ci.yml';workflow.parent.mkdir();workflow.write_text('name: synthetic\n')
            (root / 'local').mkdir();(root / 'local/private.md').write_text('not public')
            self.assertEqual(set(docs.documents(root)), set(names))
            with patch.object(handoff, 'ROOT', root), patch.object(handoff, 'MANIFEST', root / 'evidence/handoff-manifest.json'):
                selected = {str(p.relative_to(root)) for p in handoff.files()}
            self.assertTrue(set(names + ['.github/workflows/ci.yml']) <= selected)
            self.assertNotIn('local/private.md', selected)

    def test_new_public_paths_scan_staged_private_keys_even_after_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);subprocess.run(['git', 'init', '-q', str(root)], check=True)
            names = ['CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md', '.github/workflows/ci.yml']
            # Construct a marker, not an actual private key or credential.
            marker = '-----BEGIN ' + 'PRIVATE KEY-----\nSYNTHETIC-NOT-A-KEY\n'
            for name in names:
                p = root / name;p.parent.mkdir(parents=True, exist_ok=True);p.write_text(marker)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            for name in names:(root / name).write_text('working tree cleaned after staging\n')
            self.assertEqual({(e['path'], e['reason']) for e in privacy.scan(root)}, {(n, 'private_key') for n in names})

    def test_github_symlink_cannot_hide_a_private_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.github').mkdir();(root / 'local').mkdir();(root / 'local/synthetic').write_text('synthetic')
            (root / '.github/SECURITY.md').symlink_to('../local/synthetic')
            subprocess.run(['git', 'add', '.github/SECURITY.md'], cwd=root, check=True)
            self.assertEqual(privacy.scan(root), [{'path': '.github/SECURITY.md', 'reason': 'unmerged_or_symlink'}])


class InstalledWheelGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root = Path(tmp.name)
        self.checkout = self.root / 'checkout';self.checkout.mkdir()
        (self.checkout / 'pyproject.toml').write_text('[project]\nversion="0.1.0"\nrequires-python=">=3.11"\ndependencies=[]\n[project.scripts]\ndab="dingtalk_bridge.cli:main"\n')
        self.package = self.root / 'site-packages/dingtalk_bridge';self.package.mkdir(parents=True)
        for base in [self.checkout / 'dingtalk_bridge', self.package]:
            (base / 'licenses').mkdir(parents=True);(base / '__init__.py').write_text('# synthetic\n');(base / 'licenses/notice.txt').write_text('Synthetic license notice\n')
        self.dist = SimpleNamespace(version='0.1.0', metadata={'Requires-Python': '>=3.11'}, requires=None,
                                    locate_file=lambda name: self.package,
                                    entry_points=[SimpleNamespace(group='console_scripts', name='dab', value='dingtalk_bridge.cli:main')])

    def test_installed_bytes_and_metadata_pass_without_invoking_cli(self):
        self.assertTrue(installed.verify(self.checkout, self.dist)['ok'])

    def test_source_checkout_is_not_accepted_as_installed_wheel(self):
        self.dist.locate_file = lambda name: self.checkout / 'dingtalk_bridge'
        with self.assertRaisesRegex(ValueError, 'source_checkout'):installed.verify(self.checkout, self.dist)

    def test_missing_extra_or_changed_code_and_license_fail(self):
        for name in ['__init__.py', 'extra.py', 'licenses/notice.txt']:
            with self.subTest(name=name):
                p = self.package / name;before = p.read_bytes() if p.exists() else None;p.write_text('unexpected payload\n')
                self.assertFalse(installed.verify(self.checkout, self.dist)['checks']['package_bytes'])
                if before is None:p.unlink()
                else:p.write_bytes(before)
        (self.package / '__init__.py').unlink()
        self.assertFalse(installed.verify(self.checkout, self.dist)['ok'])

    def test_entrypoint_dependency_and_version_mismatch_fail(self):
        for field,value,check in [('version','0.2.0','version'),('requires',['unexpected-runtime-dependency'],'runtime_dependencies'),('entry_points',[],'entry_points')]:
            with self.subTest(field=field):
                old=getattr(self.dist,field);setattr(self.dist,field,value)
                self.assertFalse(installed.verify(self.checkout,self.dist)['checks'][check]);setattr(self.dist,field,old)

if __name__ == '__main__':unittest.main()

"""Offline release checks against synthetic Git objects and actual zip/tar bytes."""
import base64
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_export', ROOT / 'scripts/export_release.py')
release = importlib.util.module_from_spec(spec);spec.loader.exec_module(release)


class ReleaseExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name);self.repo = self.root / 'repo';self.repo.mkdir()
        self.git('init', '-q');self.git('config', 'user.name', 'Synthetic Test');self.git('config', 'user.email', 'test@example.invalid');self.git('config','core.hooksPath',str(self.root/'no-hooks'));self.git('config','commit.gpgsign','false')
        self.scripts = {n: 'dingtalk_bridge.fake:main' for n in ['dab','dab-bridge','dab-agent','dab-consume','dab-doctor','dab-service']}
        self.source = {'__init__.py': b'# synthetic package\n', 'fake.py': b'def main(): pass\n',
                       'licenses/example.txt': b'Synthetic license\n'}
        for n, b in self.source.items():self.write('dingtalk_bridge/' + n, b)
        self.write('pyproject.toml', '[project]\nname = "dingtalk-agent-bridge"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = []\n[project.scripts]\n' + ''.join(f'"{k}" = "{v}"\n' for k,v in self.scripts.items()))
        self.write('README.md', 'Synthetic public source\n')
        self.write('fixtures/sample.png', b'public synthetic image fixture')
        self.wheel = self.root / 'dingtalk_agent_bridge-0.1.0-py3-none-any.whl'
        self.dist = 'dingtalk_agent_bridge-0.1.0.dist-info/'
        self.wheel_data = {'dingtalk_bridge/' + n:b for n,b in self.source.items()}
        self.wheel_data.update({
            self.dist+'METADATA': b'Metadata-Version: 2.4\nName: dingtalk-agent-bridge\nVersion: 0.1.0\nRequires-Python: >=3.11\n\nOld readme can differ from later docs.\n',
            self.dist+'WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
            self.dist+'entry_points.txt': ('[console_scripts]\n'+''.join(f'{k} = {v}\n' for k,v in self.scripts.items())).encode(),
            self.dist+'top_level.txt': b'dingtalk_bridge\n'})
        self.pack_wheel();self.validation='evidence/validation.json';self.bind_validation();self.commit()
        self.out=self.root/'bundle'

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.DEVNULL).decode().strip()

    def write(self,n,data):
        p=self.repo/n;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(data.encode() if isinstance(data,str) else data)

    def pack_wheel(self):
        buffer=io.StringIO();writer=csv.writer(buffer,lineterminator='\n')
        for n,b in self.wheel_data.items():
            writer.writerow([n,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b'=').decode(),str(len(b))])
        writer.writerow([self.dist+'RECORD','',''])
        with zipfile.ZipFile(self.wheel,'w') as z:
            for n,b in self.wheel_data.items():z.writestr(n,b)
            z.writestr(self.dist+'RECORD',buffer.getvalue())

    def bind_validation(self,modern=False):
        rows=[{'label':n,'ok':True,'exitCode':0,'testsRun':4} for n in ['source','py314','py311']]
        if modern:
            report={'ok':True,'wheelSha256':release.digest(self.wheel.read_bytes()),'codeSha256':{n:release.digest(b) for n,b in self.source.items() if n.endswith('.py')},'results':rows,'wheelModulesMatch':True,'licensesMatch':True}
        else:
            report={'evidence':'synthetic','candidateWheelSha256':release.digest(self.wheel.read_bytes()),'candidateModules':2,'wheelModulesMatch':True,'validation':rows}
        self.write(self.validation,json.dumps(report))

    def commit(self):
        files={str(p.relative_to(self.repo)):release.digest(p.read_bytes()) for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts and p!=self.repo/release.MANIFEST}
        self.write(release.MANIFEST,json.dumps({'schemaVersion':1,'sha256':files}))
        self.git('add','.');self.git('commit','-qm','synthetic snapshot');return self.git('rev-parse','HEAD')

    def export(self):return release.export(self.repo,'HEAD',self.wheel,self.validation,self.out)

    def test_frozen_export_ignores_dirty_working_tree_allows_later_docs_and_public_fixtures(self):
        self.write('README.md','Later docs\n');commit=self.commit()
        self.write('dingtalk_bridge/fake.py','uncommitted wrong code\n');self.write('local/secret','untracked fake private data')
        report=self.export();self.assertEqual(report['sourceCommit'],commit)
        self.assertEqual(report['sourceTree'],self.git('rev-parse','HEAD^{tree}'))
        self.assertEqual(report['validation']['declaredResults'][0]['testsRun'],4)
        self.assertFalse(report['fullProductAcceptance'])
        files=release.source_files((self.out/'source.tar.gz').read_bytes())
        self.assertEqual(files['dingtalk_bridge/fake.py'],self.source['fake.py'])
        self.assertIn('fixtures/sample.png',files);self.assertNotIn('local/secret',files)
        self.assertTrue((self.out/'COMPLETE.json').is_file());self.assertFalse((self.out/'.completion.tmp').exists())
        for line in (self.out/'SHA256SUMS.txt').read_text().splitlines():
            sha,name=line.split('  ',1);self.assertEqual(release.digest((self.out/name).read_bytes()),sha)

    def test_modern_validation_schema_matches_modules(self):
        self.bind_validation(modern=True);self.commit();self.export()

    def test_rejects_mixed_product_extra_wheel_code_and_license(self):
        for name in ['dingtalk_bridge/fake.py','dingtalk_bridge/extra.py','dingtalk_bridge/licenses/example.txt']:
            with self.subTest(name=name):
                old=self.wheel_data.copy();self.wheel_data[name]=b'changed';self.pack_wheel();self.bind_validation();self.commit()
                with self.assertRaisesRegex(release.ReleaseError,'package content'):self.export()
                self.assertFalse(self.out.exists());self.wheel_data=old

    def test_rejects_version_python_cli_dependency_and_unknown_wheel_payload(self):
        cases=[(self.dist+'METADATA',b'Metadata-Version: 2.4\nName: dingtalk-agent-bridge\nVersion: 0.2.0\nRequires-Python: >=3.11\n'),
               (self.dist+'METADATA',b'Name: dingtalk-agent-bridge\nVersion: 0.1.0\nRequires-Python: >=3.14\n'),
               (self.dist+'METADATA',b'Name: dingtalk-agent-bridge\nVersion: 0.1.0\nRequires-Python: >=3.11\nRequires-Dist: unexpected\n'),
               (self.dist+'entry_points.txt',b'[console_scripts]\ndab = other:main\n'),('unknown.py',b'not part of product')]
        for name,data in cases:
            with self.subTest(name=name,data=data):
                old=self.wheel_data.copy();self.wheel_data[name]=data;self.pack_wheel();self.bind_validation();self.commit()
                with self.assertRaises(release.ReleaseError):self.export()
                self.assertFalse(self.out.exists());self.wheel_data=old

    def test_rejects_missing_digest_failed_tests_and_changed_module_binding(self):
        for mutate in [lambda r:r.pop('wheelSha256'),lambda r:r.update(wheelSha256='0'*64),lambda r:r['results'][0].update(ok=False),lambda r:r.update(ok=False),lambda r:r['results'][1].update(modulesMatch=False),lambda r:r['results'][1].update(label='source'),lambda r:r.update(codeSha256={'fake.py':'0'*64})]:
            self.bind_validation(modern=True);r=json.loads((self.repo/self.validation).read_text());mutate(r);self.write(self.validation,json.dumps(r));self.commit()
            with self.assertRaises(release.ReleaseError):self.export()
            self.assertFalse(self.out.exists())

    def test_rejects_manifest_tampering_and_unlisted_committed_file(self):
        self.write('README.md','tampered after manifest');self.git('add','.');self.git('commit','-qm','stale manifest')
        with self.assertRaisesRegex(release.ReleaseError,'digest'):self.export()
        self.commit();self.write('extra.txt','unlisted');self.git('add','.');self.git('commit','-qm','unlisted')
        with self.assertRaisesRegex(release.ReleaseError,'inventory'):self.export()

    def test_rejects_committed_private_root_and_symlink(self):
        self.write('local/synthetic','fake private');self.commit()
        with self.assertRaisesRegex(release.ReleaseError,'Private runtime path'):self.export()
        (self.repo/'local/synthetic').unlink();(self.repo/'local').rmdir();self.commit()
        (self.repo/'link').symlink_to('README.md');self.git('add','.');self.git('commit','-qm','symlink')
        with self.assertRaisesRegex(release.ReleaseError,'links'):self.export()

    def test_rejects_committed_manifest_bound_and_wheel_databases(self):
        for suffix in ['.sqlite', '.sqlite3', '.db']:
            with self.subTest(suffix=suffix):
                name='fixtures/synthetic'+suffix
                self.write(name,b'SQLite format 3\x00synthetic bytes');self.commit()
                with self.assertRaisesRegex(release.ReleaseError,'Database path'):self.export()
                (self.repo/name).unlink();self.commit()
                name='dingtalk_bridge/synthetic'+suffix
                self.wheel_data[name]=b'SQLite format 3\x00synthetic bytes'
                self.pack_wheel();self.bind_validation();self.commit()
                with self.assertRaisesRegex(release.ReleaseError,'Database path'):self.export()
                del self.wheel_data[name]
                self.pack_wheel();self.bind_validation();self.commit()
                self.assertFalse(self.out.exists())

    def test_rejects_wheel_record_corruption_and_duplicate_paths(self):
        with zipfile.ZipFile(self.wheel) as z:original={n:z.read(n) for n in z.namelist()}
        with zipfile.ZipFile(self.wheel,'w') as z:
            for n,b in original.items():z.writestr(n,b.replace(b'sha256=',b'sha512=') if n.endswith('/RECORD') else b)
        self.bind_validation();self.commit()
        with self.assertRaisesRegex(release.ReleaseError,'RECORD'):self.export()
        self.pack_wheel()
        with zipfile.ZipFile(self.wheel,'a') as z:
            import warnings
            with warnings.catch_warnings():warnings.simplefilter('ignore');z.writestr('dingtalk_bridge/fake.py',b'duplicate')
        self.bind_validation();self.commit()
        with self.assertRaisesRegex(release.ReleaseError,'Duplicate wheel'):self.export()

    def test_no_overwrite_and_no_completion_on_interrupted_output(self):
        self.out.mkdir();(self.out/'owned-by-user').write_text('keep')
        with self.assertRaisesRegex(release.ReleaseError,'already exists'):self.export()
        self.assertEqual((self.out/'owned-by-user').read_text(),'keep')
        (self.out/'owned-by-user').unlink();self.out.rmdir()
        with patch.object(release.os,'fsync',side_effect=OSError('synthetic write failure')):
            with self.assertRaises(OSError):self.export()
        self.assertFalse((self.out/'COMPLETE.json').exists())
        with self.assertRaisesRegex(release.ReleaseError,'already exists'):self.export()

    def test_cli_is_offline_and_returns_safe_failure(self):
        command=[sys.executable,str(ROOT/'scripts/export_release.py'),'--repo',str(self.repo),'--commit','HEAD','--wheel',str(self.wheel),'--validation',self.validation,'--output',str(self.out)]
        run=subprocess.run(command,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertTrue(json.loads(run.stdout)['ok'])
        repeat=subprocess.run(command,capture_output=True,text=True);self.assertEqual(repeat.returncode,1)
        self.assertEqual(json.loads(repeat.stdout)['error'],'Output already exists')


if __name__ == '__main__':unittest.main()

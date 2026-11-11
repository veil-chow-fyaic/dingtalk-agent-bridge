import copy
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from frozen_install import digest,frozen_install_matches,module_sources_match


class FrozenInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'clean-source/dingtalk_bridge';self.source.mkdir(parents=True)
        self.installed=self.root/'venv/lib/python3.11/site-packages/dingtalk_bridge';self.installed.mkdir(parents=True)
        self.data=b'"""Synthetic frozen package."""\n'
        for p in (self.source,self.installed):(p/'__init__.py').write_bytes(self.data)
        (self.root/'wheels').mkdir();self.wheel=self.root/'wheels/test.whl'
        with zipfile.ZipFile(self.wheel,'w') as z:z.writestr('dingtalk_bridge/__init__.py',self.data)
        self.report={'ok':True,'codeSha256':{'__init__.py':digest(self.data)},'wheelSha256':digest(self.wheel.read_bytes()),
                     'entrypoints':{n:True for n in ('dab','dab-bridge','dab-agent','dab-consume','dab-doctor','dab-service')}}

    def test_frozen_install_does_not_depend_on_current_source_and_is_readonly(self):
        current=self.root/'current/dingtalk_bridge';current.mkdir(parents=True)
        (current/'__init__.py').write_text('new revision')
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertTrue(frozen_install_matches(self.report,self.root))
        self.assertFalse(module_sources_match(self.report,current))
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_tampered_missing_and_ambiguous_frozen_inputs_rejected(self):
        for target in (self.source/'__init__.py',self.installed/'__init__.py',self.wheel):
            original=target.read_bytes();target.write_bytes(b'changed')
            self.assertFalse(frozen_install_matches(self.report,self.root));target.write_bytes(original)
            target.unlink();self.assertFalse(frozen_install_matches(self.report,self.root));target.write_bytes(original)
        extra=self.root/'wheels/extra.whl';extra.write_bytes(self.wheel.read_bytes())
        self.assertFalse(frozen_install_matches(self.report,self.root));extra.unlink()
        extra=self.installed/'unexpected.py';extra.write_bytes(b'extra')
        self.assertFalse(frozen_install_matches(self.report,self.root));extra.unlink()
        self.assertTrue(frozen_install_matches(self.report,self.root))

    def test_invalid_manifest_and_forged_wheel_digest_do_not_bypass_content(self):
        for report in (None,[],True):self.assertFalse(frozen_install_matches(report,self.root))
        for mutation in ({'ok':False},{'codeSha256':{}},{'codeSha256':{'../outside.py':digest(self.data)}},{'entrypoints':{}},{'entrypoints':list(self.report['entrypoints'])},{'wheelSha256':'0'*64}):
            self.assertFalse(frozen_install_matches({**self.report,**mutation},self.root))
        with zipfile.ZipFile(self.wheel,'w') as z:z.writestr('dingtalk_bridge/__init__.py',b'altered wheel module')
        report=copy.deepcopy(self.report);report['wheelSha256']=digest(self.wheel.read_bytes())
        self.assertFalse(frozen_install_matches(report,self.root))


if __name__=='__main__':unittest.main()

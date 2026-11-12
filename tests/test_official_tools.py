import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge.official_tools import prepare, enabled, CONTEXT, GUIDE, WRAPPER
from dingtalk_bridge.official_proxy import OFFICE_COMMANDS


class OfficialToolContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.binary=self.root/'dws';self.binary.write_text('synthetic executable, never invoked');self.binary.chmod(0o700)
        self.route={'binary':'dws','profile':'synthetic-corp:synthetic-user','secret':'must-not-copy'}

    def tearDown(self):self.temp.cleanup()

    def test_opt_in_context_pins_profile_and_only_exposes_cli_metadata(self):
        with patch('subprocess.run',side_effect=AssertionError('must not invoke CLI')):
            prompt=prepare(self.root,self.workspace,self.route,{'officialDwsTools':True})
        self.assertIn(GUIDE,prompt);self.assertNotIn('synthetic-user',prompt)
        self.assertEqual(json.loads((self.workspace/CONTEXT).read_text()),
            {'schemaVersion':2,'binary':str((self.workspace/WRAPPER).resolve()),'profile':self.route['profile'],
             'commands':list(OFFICE_COMMANDS)})
        for name in (CONTEXT,GUIDE,WRAPPER):self.assertEqual((self.workspace/name).stat().st_mode & 0o077,0)
        self.assertEqual((self.workspace/WRAPPER).stat().st_mode & 0o777,0o700)
        self.assertIn('不可自动再创建',(self.workspace/GUIDE).read_text())

    def test_default_is_off_and_disabling_removes_only_generated_context(self):
        self.assertEqual(prepare(self.root,self.workspace,self.route,{}),'')
        self.assertEqual(list(self.workspace.iterdir()),[])
        prepare(self.root,self.workspace,self.route,{'officialDwsTools':True})
        keep=self.workspace/'task-result.txt';keep.write_text('preserve')
        self.assertEqual(prepare(self.root,self.workspace,self.route,{'officialDwsTools':False}),'')
        self.assertEqual(list(self.workspace.iterdir()),[keep])

    def test_ambiguous_profile_and_missing_binary_refuse_before_context_write(self):
        for profile in ('default','corp:user,corp:other','corp:user other'):
            with self.assertRaisesRegex(ValueError,'explicit verified'):
                prepare(self.root,self.workspace,{**self.route,'profile':profile},{'officialDwsTools':True})
        with self.assertRaisesRegex(ValueError,'unavailable'):
            prepare(self.root,self.workspace,{**self.route,'binary':'missing'},{'officialDwsTools':True})
        self.assertEqual(list(self.workspace.iterdir()),[])

    def test_generated_context_cannot_overwrite_symlink_target(self):
        outside=self.root/'outside';outside.write_text('untouched')
        for name in (CONTEXT,GUIDE,WRAPPER):
            with self.subTest(name=name):
                (self.workspace/name).symlink_to(outside)
                with self.assertRaisesRegex(ValueError,'symlink'):
                    prepare(self.root,self.workspace,self.route,{'officialDwsTools':True})
                self.assertEqual(outside.read_text(),'untouched')
                self.assertEqual(list(self.workspace.iterdir()),[self.workspace/name])
                (self.workspace/name).unlink()

    def test_boolean_is_not_coerced_from_strings_or_numbers(self):
        for value in ('false','true',1,None,[]):
            with self.assertRaisesRegex(ValueError,'boolean'):enabled({'officialDwsTools':value})


if __name__=='__main__':unittest.main()

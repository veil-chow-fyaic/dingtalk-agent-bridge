"""The optional image builder must not overwrite unrelated local artifacts."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('image_build', ROOT / 'integrations/dws_image_upload/build.py')
BUILD = importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(BUILD)
BASE = b'package helpers\nfunc register() {\n\troot.AddCommand(chatChmodCmd, other)\n}\n'


class ImageBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name);self.source = self.root / 'source'
        self.helpers = self.source / 'internal/helpers';self.helpers.mkdir(parents=True)
        (self.helpers / 'chat.go').write_bytes(BASE)
        self.output = self.root / 'output';self.receipt = self.output.with_suffix('.build.json')
        self.go = self.root / 'fake-go'
        self.go.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(
            "import pathlib,sys; p=pathlib.Path.cwd()/'go-calls';p.write_text(p.read_text()+'called\\n' if p.exists() else 'called\\n');"
            "pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_bytes(b'built-supplement') if '-o' in sys.argv else None") + ' "$@"\n')
        self.go.chmod(0o700)

    def invoke(self):
        def command(args, **kwargs):
            if args[0] == 'git':
                if args[1] == 'rev-parse':return BUILD.UPSTREAM_COMMIT + '\n'
                if args[1] == 'show':return BASE
                if args[1] == 'diff':return ''
            if args == [str(self.go), 'version']:return 'go version synthetic-test\n'
            raise AssertionError(args)
        with patch.object(sys, 'argv', ['build.py', '--source', str(self.source), '--go', str(self.go), '--output', str(self.output)]), \
                patch.object(BUILD.subprocess, 'check_output', side_effect=command), contextlib.redirect_stdout(io.StringIO()):
            BUILD.main()

    def test_unowned_existing_output_is_rejected_before_source_or_binary_changes(self):
        self.output.write_bytes(b'synthetic-official-binary')
        error = None
        try:self.invoke()
        except SystemExit as exc:error = str(exc)
        self.assertEqual(self.output.read_bytes(), b'synthetic-official-binary')
        self.assertIsNotNone(error)
        self.assertEqual((self.helpers / 'chat.go').read_bytes(), BASE)
        self.assertFalse((self.source / 'go-calls').exists());self.assertFalse(self.receipt.exists())

    def test_tampered_owned_output_and_invalid_receipt_are_rejected(self):
        self.invoke();receipt = self.receipt.read_bytes();self.output.write_bytes(b'unrelated replacement')
        with self.assertRaises(SystemExit):self.invoke()
        self.assertEqual(self.output.read_bytes(), b'unrelated replacement')
        self.assertEqual(self.receipt.read_bytes(), receipt)
        self.output.unlink();self.receipt.write_text('[]')
        with self.assertRaises(SystemExit):self.invoke()
        self.assertFalse(self.output.exists());self.assertEqual(self.receipt.read_text(), '[]')

    def test_symlinks_and_unowned_generated_test_are_not_overwritten(self):
        target = self.root / 'target';target.write_bytes(b'keep')
        self.output.symlink_to(target)
        with self.assertRaises(SystemExit):self.invoke()
        self.assertEqual(target.read_bytes(), b'keep');self.assertTrue(self.output.is_symlink())
        self.output.unlink()
        test_file = self.helpers / 'bridge_image_upload_test.go';test_file.write_bytes(b'user test edits')
        with self.assertRaises(SystemExit):self.invoke()
        self.assertEqual(test_file.read_bytes(), b'user test edits')
        self.assertEqual((self.helpers / 'chat.go').read_bytes(), BASE)

    def test_first_build_and_verified_owned_rebuild_keep_precise_receipt(self):
        self.invoke();first = json.loads(self.receipt.read_text());self.invoke();second = json.loads(self.receipt.read_text())
        self.assertEqual(first['binarySha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertEqual(first['addonSha256'], second['addonSha256'])
        self.assertEqual(first['testSha256'], hashlib.sha256((self.helpers / 'bridge_image_upload_test.go').read_bytes()).hexdigest())
        self.assertFalse(first['replacedVerifiedOutput']);self.assertTrue(second['replacedVerifiedOutput'])
        self.assertNotIn('stockDWSUnchanged', second)


if __name__ == '__main__':unittest.main()

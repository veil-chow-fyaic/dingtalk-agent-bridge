import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_support import Probe

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        (self.root/'local').mkdir()
        (self.root/'local/service-config.json').write_text(json.dumps({'profile':'corp:self','binary':'dws'}))
        self.root_patch=patch('probe_support.ROOT',self.root); self.root_patch.start()
    def tearDown(self):
        self.root_patch.stop(); self.tmp.cleanup()
    def test_replay_and_payload_binding(self):
        with patch('probe_support.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"success":true}',stderr='')) as run:
            p=Probe('test');p.call('send',['chat','send','a']);p.call('send',['chat','send','a'])
            with self.assertRaises(RuntimeError):p.call('send',['chat','send','b'])
            self.assertEqual(run.call_count,1)
    def test_unfinished_request_cannot_replay(self):
        p=Probe('test');(p.dir/'send.json').write_text('{"state":"started"}')
        with patch('probe_support.subprocess.run') as run:
            with self.assertRaises(RuntimeError):p.call('send',['chat','send'])
            run.assert_not_called()
    def test_business_failure_not_reused(self):
        p=Probe('test')
        with patch('probe_support.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"success":"false"}',stderr='')) as run:
            for _ in range(2):
                with self.assertRaises(RuntimeError):p.call('send',['chat','send'])
            self.assertEqual(run.call_count,1)
    def test_v2_keeps_probe_fingerprint_and_rejects_ambiguous_routes(self):
        with patch('probe_support.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"success":true}',stderr='')) as run:
            p=Probe('migration');p.call('send',['chat','send','a'])
            route={'profile':'corp:self','binary':'dws','conversationType':'group','conversationId':'g'}
            path=self.root/'local/service-config.json';path.write_text(json.dumps({'routes':[route]}))
            p=Probe('migration');p.call('send',['chat','send','a'])
            self.assertEqual(p.config['group'],'g');self.assertEqual(run.call_count,1)
            path.write_text(json.dumps({'routes':[route,route]}))
            with self.assertRaises(ValueError):Probe('migration')

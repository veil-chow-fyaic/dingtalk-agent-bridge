"""Synthetic interruption attribution; never touches a real DWS credential."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from dingtalk_bridge.core import DWS
from dingtalk_bridge.dws_access import DWSAccess,DWSAccessSuspended


class DWSCallJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.access=DWSAccess(self.root);self.access.directory.mkdir(parents=True)
    def tearDown(self):self.tmp.cleanup()
    def rows(self):return [json.loads(x) for x in (self.access.directory/'dws-call-audit.ndjson').read_text().splitlines()]

    def test_killed_owner_is_attributed_and_resume_is_explicit(self):
        code='''import os,signal,sys
from dingtalk_bridge.dws_access import DWSAccess
with DWSAccess(sys.argv[1]).lease(operation='history') as lease:
    lease.stage('invoking')
    os.kill(os.getpid(),signal.SIGKILL)
'''
        env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
        # Installed suite has no source package; retain its installed interpreter.
        process=subprocess.run([sys.executable,'-c',code,str(self.root)],env=env,capture_output=True,timeout=10)
        self.assertEqual(process.returncode,-9)
        before=self.rows();owner=before[-1]['pid'];attempt=before[-1]['attempt']
        self.assertEqual([x['event'] for x in before],['reserving','reserved','invoking'])
        with self.assertRaisesRegex(DWSAccessSuspended,'dws_process_interrupted'):
            with self.access.lease(operation='history'):self.fail('stale slot must not execute')
        after=self.rows();self.assertEqual(after[-1]['event'],'stale_reservation')
        self.assertNotEqual(after[-1]['pid'],owner);self.assertNotEqual(after[-1]['attempt'],attempt)
        self.assertEqual(json.loads((self.access.directory/'dws-call-0.json').read_text()),{'state':'active'})
        self.access.resume()
        with self.access.lease(operation='history') as lease:lease.complete()
        self.assertEqual(self.access.status(),{'state':'ready'})
        self.assertEqual(self.rows()[:len(after)],after)
        self.assertIn('explicit_resume',[x['event'] for x in self.rows()])

    def test_synthetic_dws_call_logs_owner_category_and_no_arguments(self):
        binary=self.root/'provider';binary.write_text('#!'+sys.executable+'\nprint(\'{"success":true}\')\n');binary.chmod(0o700)
        DWS(self.root,{'binary':str(binary),'profile':'SECRET_PROFILE:SECRET_CORP'}).call(
            ['chat','+chat-messages','--group','SECRET_CONVERSATION','--text','SECRET_BODY'])
        rows=self.rows();self.assertEqual([x['event'] for x in rows],['reserving','reserved','invoking','released'])
        self.assertEqual(len({x['attempt'] for x in rows}),1)
        self.assertEqual({x['pid'] for x in rows},{os.getpid()});self.assertEqual({x['operation'] for x in rows},{'history'})
        raw=(self.access.directory/'dws-call-audit.ndjson').read_text()
        self.assertNotIn('SECRET_',raw);self.assertNotIn(str(binary),raw)

    def test_release_storage_failure_retains_stale_slot_and_failure_stage(self):
        original=self.access.write
        def fail_ready(value,path=None):
            if path is not None and value=={'state':'ready'}:raise OSError('private filesystem message')
            return original(value,path)
        with patch.object(self.access,'write',side_effect=fail_ready):
            with self.assertRaises(OSError):
                with self.access.lease(operation='history') as lease:lease.complete()
        self.assertEqual(self.access.status()['reason'],'dws_process_interrupted')
        self.assertTrue(any(x['event']=='release_failed' and x['errorType']=='OSError' for x in self.rows()))
        self.assertNotIn('private filesystem message',json.dumps(self.rows()))
        self.assertEqual(json.loads((self.access.directory/'dws-call-0.json').read_text()),{'state':'active'})

    def test_concurrent_slots_have_distinct_attempts_without_interleaved_json(self):
        barrier=threading.Barrier(2);errors=[]
        def call():
            try:
                with DWSAccess(self.root).lease(operation='history') as lease:
                    barrier.wait(timeout=5);lease.complete()
            except Exception as exc:errors.append(exc)
        threads=[threading.Thread(target=call) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(10)
        self.assertFalse(errors);self.assertFalse(any(t.is_alive() for t in threads))
        rows=self.rows();reserved=[x for x in rows if x['event']=='reserved']
        self.assertEqual({x['slot'] for x in reserved},{0,1});self.assertEqual(len({x['attempt'] for x in reserved}),2)
        for x in reserved:self.assertEqual([y['event'] for y in rows if y['attempt']==x['attempt']],['reserving','reserved','released'])

    def test_journal_io_failure_does_not_change_existing_call_outcome_or_latch(self):
        original=os.open
        def unavailable(path,*args,**kwargs):
            if Path(path).name=='dws-call-audit.ndjson':raise OSError('private error')
            return original(path,*args,**kwargs)
        output=io.StringIO()
        with patch('dingtalk_bridge.dws_access.os.open',side_effect=unavailable),contextlib.redirect_stderr(output):
            with self.access.lease(operation='history') as lease:lease.complete()
        self.assertEqual(self.access.status(),{'state':'ready'})
        self.assertIn('dws_audit_write_failed',output.getvalue());self.assertNotIn('private error',output.getvalue())

    def test_unknown_operation_cannot_leak_text_and_known_failure_keeps_reason(self):
        with self.access.lease(operation='SECRET_ARG') as lease:
            lease.block('dws_timeout');lease.complete()
        rows=self.rows();self.assertEqual({x['operation'] for x in rows},{'other'})
        self.assertEqual(next(x for x in rows if x['event']=='suspended')['reason'],'dws_timeout')
        self.assertNotIn('SECRET_ARG',json.dumps(rows));self.assertEqual(self.access.status()['reason'],'dws_timeout')

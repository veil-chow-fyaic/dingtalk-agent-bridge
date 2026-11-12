"""Offline recovery checks: synthetic CLI only, pause stays closed throughout."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import check_dws_recovery_once as check
from dingtalk_bridge.dws_access import DWSAccess


class RecoveryOnceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'local').mkdir()
        self.binary=self.root/'synthetic-dws'
        self.config=self.root/'local/service-config.json'
        self.config.write_text(json.dumps({'profile':'synthetic-corp:synthetic-user','group':'synthetic-conversation','binary':self.binary.name}))
        self.access=DWSAccess(self.root)
        with self.access.lock():self.access.block('operator_suspended')
        self.before=self.access.block_path.read_bytes()

    def program(self,body):
        self.binary.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nwith Path("calls").open("a") as f:f.write("one\\n")\n'+body)
        self.binary.chmod(0o700)

    def test_prepare_has_zero_invocations_and_execution_requires_explicit_opt_in(self):
        self.program('raise SystemExit(77)')
        with patch.object(check.dws_access,'run_dws',side_effect=AssertionError('must not start')):
            plan=check.prepare(self.root,'prepared')
            self.assertEqual(plan['maxInvocations'],1)
            self.assertNotIn('synthetic-user',json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'Explicit permission'):check.execute(self.root,'prepared')
        self.assertFalse((self.root/'calls').exists());self.assertEqual(self.access.block_path.read_bytes(),self.before)
        self.assertEqual((check.directory(self.root,'prepared')/'plan.json').stat().st_mode & 0o777,0o600)

    def test_one_read_checks_target_and_repeat_never_calls_again(self):
        self.program('import json,sys\nPath("args.json").write_text(json.dumps(sys.argv[1:]))\nprint(\'{"result":{"conversationInfo":{"openConversationId":"synthetic-conversation"}}}\')')
        check.prepare(self.root,'once')
        result=check.execute(self.root,'once',allow_credential_read=True)
        self.assertEqual(result['state'],'readable');self.assertTrue(result['suspensionUnchanged'])
        for _ in range(3):self.assertTrue(check.execute(self.root,'once',allow_credential_read=True)['replayed'])
        self.assertEqual((self.root/'calls').read_text(),'one\n')
        self.assertEqual(json.loads((self.root/'args.json').read_text()),['chat','+conversation-info','--group','synthetic-conversation','--profile','synthetic-corp:synthetic-user','--format','json'])
        self.assertEqual(self.access.block_path.read_bytes(),self.before)

    def test_direct_arguments_and_failed_attempt_remain_consumed_after_code_change(self):
        route={'conversationType':'direct','peerOpenDingTalkId':'synthetic-peer','profile':'synthetic-corp:synthetic-user'}
        self.assertEqual(check.conversation_info_arguments(route), ['chat','+conversation-info','--open-dingtalk-id',
                         'synthetic-peer','--profile','synthetic-corp:synthetic-user','--format','json'])
        self.program('print(\'{"error":{"category":"validation","code":3,"reason":"unknown_flag"}}\');raise SystemExit(3)')
        check.prepare(self.root,'old-failure');result=check.execute(self.root,'old-failure',allow_credential_read=True)
        self.assertEqual(result['state'],'failed')
        receipt=check.directory(self.root,'old-failure')/'receipt.json';before=receipt.read_bytes()
        with patch.object(check,'current_plan',side_effect=AssertionError('must not revalidate a consumed call')):
            replay=check.execute(self.root,'old-failure',allow_credential_read=True)
        self.assertTrue(replay['replayed']);self.assertEqual(replay['state'],'failed')
        self.assertEqual(receipt.read_bytes(),before);self.assertEqual((self.root/'calls').read_text(),'one\n')

    def test_rejected_malformed_and_wrong_identity_are_not_healthy_or_retried(self):
        cases=[(51,{'error':{'message':'private-marker'}}),(0,'bad-json'),
               (0,{'result':{'conversationInfo':{'openConversationId':'wrong'}}}),
               (0,{'ok':False,'outcome':'done','data':{'result':{'conversationInfo':{'openConversationId':'synthetic-conversation'}}}})]
        for index,(code,data) in enumerate(cases):
            with self.subTest(index=index):
                output=json.dumps(data) if isinstance(data,dict) else data
                self.program('print('+repr(output)+')\nraise SystemExit('+str(code)+')')
                key='failed-'+str(index);check.prepare(self.root,key)
                result=check.execute(self.root,key,allow_credential_read=True)
                self.assertEqual(result['state'],'failed');self.assertNotIn('private-marker',json.dumps(result))
                self.assertTrue(check.execute(self.root,key,allow_credential_read=True)['replayed'])
        self.assertEqual((self.root/'calls').read_text(),'one\n'*len(cases))
        self.assertEqual(self.access.block_path.read_bytes(),self.before)

    def test_changed_plan_active_call_and_open_circuit_refuse_before_read(self):
        self.program('print("{}")');check.prepare(self.root,'bound')
        original=self.binary.read_bytes();self.binary.write_bytes(original+b'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'changed'):check.execute(self.root,'bound',allow_credential_read=True)
        self.binary.write_bytes(original)
        config=self.config.read_bytes();self.config.write_bytes(config+b'\n')
        with self.assertRaisesRegex(ValueError,'changed'):check.execute(self.root,'bound',allow_credential_read=True)
        self.config.write_bytes(config)
        with patch.dict(os.environ,{'DWS_DISABLE_KEYCHAIN':'1'}),self.assertRaisesRegex(ValueError,'File-key'):
            check.execute(self.root,'bound',allow_credential_read=True)
        with patch.dict(os.environ,{'DWS_CONFIG_DIR':'synthetic-other-dir'}),self.assertRaisesRegex(ValueError,'changed'):
            check.execute(self.root,'bound',allow_credential_read=True)
        original_digest=check.digest
        with patch.object(check,'digest',lambda path:'0'*64 if Path(path).name=='routing.py' else original_digest(path)),self.assertRaisesRegex(ValueError,'changed'):
            check.execute(self.root,'bound',allow_credential_read=True)
        self.access.resume()
        with self.assertRaisesRegex(ValueError,'must remain suspended'):check.execute(self.root,'bound',allow_credential_read=True)
        with self.access.lease() as lease:
            self.access.block('operator_suspended')
            with self.assertRaises(BlockingIOError):check.execute(self.root,'bound',allow_credential_read=True)
            lease.complete()
        self.assertFalse((self.root/'calls').exists())

    def test_timeout_is_consumed_once_and_children_do_not_survive(self):
        self.program('import os,time\nPath("pid").write_text(str(os.getpid()))\ntime.sleep(60)')
        check.prepare(self.root,'timed',timeout=2)
        result=check.execute(self.root,'timed',allow_credential_read=True)
        self.assertEqual(result['state'],'outcome_unknown');self.assertEqual(result['error'],'dws_timeout')
        self.assertTrue(check.execute(self.root,'timed',allow_credential_read=True)['replayed'])
        self.assertEqual((self.root/'calls').read_text(),'one\n')
        with self.assertRaises(ProcessLookupError):os.kill(int((self.root/'pid').read_text()),0)
        self.assertEqual(self.access.block_path.read_bytes(),self.before)

    def test_killed_checker_leaves_unknown_receipt_and_restart_cannot_probe_again(self):
        self.program('import os,time\nPath("pid").write_text(str(os.getpid()))\ntime.sleep(60)')
        check.prepare(self.root,'crashed')
        caller=subprocess.Popen([sys.executable,str(ROOT/'scripts/check_dws_recovery_once.py'),
            '--root',str(self.root),'--key','crashed','--execute','--allow-credential-read'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+8
            while not (self.root/'pid').exists() and time.monotonic()<deadline:time.sleep(.025)
            self.assertTrue((self.root/'pid').exists());caller.kill();caller.wait(timeout=5)
            pid=int((self.root/'pid').read_text());deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                result=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
                if not result.stdout.strip() or result.stdout.strip().startswith('Z'):break
                time.sleep(.025)
            else:self.fail('Owned synthetic CLI survived checker death')
            result=check.execute(self.root,'crashed',allow_credential_read=True)
            self.assertEqual(result['state'],'outcome_unknown');self.assertTrue(result['replayed'])
            self.assertEqual((self.root/'calls').read_text(),'one\n');self.assertEqual(self.access.block_path.read_bytes(),self.before)
        finally:
            if caller.poll() is None:caller.kill();caller.wait()


if __name__=='__main__':unittest.main()

"""Closed error telemetry with synthetic providers; no live credentials/network."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from dingtalk_bridge.core import DWS, DWSBusinessError, BridgeError
from dingtalk_bridge.dws_access import DWSAccess, DWSAccessSuspended, safe_dws_diagnostic
from dingtalk_bridge.official_proxy import execute

class DWSErrorDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.binary=self.root/'provider';self.access=DWSAccess(self.root)
        self.dws=DWS(self.root,{'binary':str(self.binary),'profile':'SECRET:PROFILE'})
    def tearDown(self):self.tmp.cleanup()
    def provider(self,data,code=0,raw=False):
        self.binary.write_text('#!'+sys.executable+'\nimport sys\nprint('+repr(data if raw else json.dumps(data))+
            ',file=sys.stderr if '+str(code)+' else sys.stdout)\nsys.exit('+str(code)+')\n')
        self.binary.chmod(0o700)
    def rows(self):return [json.loads(x) for x in (self.access.directory/'dws-call-audit.ndjson').read_text().splitlines()]
    def result(self):return [x['diagnostic'] for x in self.rows() if x['event']=='result'][-1]
    def error(self):return {'error':{'category':'api','reason':'request_timeout','code':4,
        'server_error_code':'SECRET-ID','message':'SECRET token=SECRET https://private.test',
        'origin':'mcp_gateway','stage':'request','execution_started':True,'retryable':True,
        'details':{'token':'SECRET'},'actions':['SECRET']}}

    def test_upstream_error_preserves_safe_structured_fields_without_retry_or_suspend(self):
        self.provider(self.error(),4)
        with self.assertRaises(DWSBusinessError) as caught:self.dws.call(['chat','+messages-send','--text','SECRET'])
        diag=self.result();self.assertEqual(caught.exception.diagnostic,diag)
        self.assertEqual(str(caught.exception),'request_timeout')
        self.assertEqual(diag['phase'],'response');self.assertEqual(diag['outcome'],'response_error')
        self.assertEqual(diag['exitCode'],4);self.assertGreater(diag['elapsedMs'],0)
        self.assertEqual(diag['reason'],'request_timeout');self.assertEqual(diag['category'],'api')
        self.assertTrue(diag['providerRetryable']);self.assertFalse(diag['automaticRetry'])
        self.assertTrue(diag['providerExecutionStarted']);self.assertEqual(diag['server_error_code'],'unclassified')
        self.assertNotIn('SECRET',json.dumps(self.rows()));self.assertNotIn('private.test',json.dumps(self.rows()))
        self.assertEqual(sum(x['event']=='invoking' for x in self.rows()),1)
        self.assertEqual(self.access.status(),{'state':'ready'})

    def test_credential_fault_is_latched_and_next_call_never_spawns(self):
        self.provider({'error':{'category':'internal','code':51,'message':
            'resolve access token: load access token: load from keychain: read DEK from macOS Keychain: SECRET'}},51)
        with self.assertRaisesRegex(DWSAccessSuspended,'credential_store_unavailable'):self.dws.call(['chat','+chat-messages'])
        self.assertEqual(self.result()['reason'],'credential_store_unavailable')
        with patch('dingtalk_bridge.core.run_dws') as spawn:
            with self.assertRaises(DWSAccessSuspended):self.dws.call(['chat','+chat-messages'])
            spawn.assert_not_called()
        self.assertNotIn('SECRET',json.dumps(self.rows()))

    def test_process_timeout_is_distinct_from_provider_timeout(self):
        with patch('dingtalk_bridge.core.run_dws',side_effect=DWSAccessSuspended('dws_timeout')):
            with self.assertRaises(DWSAccessSuspended):self.dws.call(['chat','+chat-messages'])
        self.assertEqual(self.result()['phase'],'process');self.assertIsNone(self.result()['exitCode'])
        self.assertEqual(self.result()['reason'],'dws_timeout');self.assertNotIn('category',self.result())
        self.assertEqual(self.access.status()['reason'],'dws_timeout')

    def test_invalid_json_and_nonobject_are_decode_errors(self):
        for body in ('SECRET not JSON','["SECRET"]'):
            self.provider(body,raw=True)
            with self.assertRaises(BridgeError):self.dws.call(['chat','+chat-messages'])
            self.assertEqual(self.result()['phase'],'decode');self.assertEqual(self.result()['reason'],'invalid_response')
        self.assertNotIn('SECRET',json.dumps(self.rows()));self.assertEqual(self.access.status(),{'state':'ready'})

    def test_inner_failure_and_top_failure_do_not_mask_each_other(self):
        cases=[{'outcome':'error','data':self.error()},
               {**self.error(),'outcome':'error','data':{'success':True}}]
        for case in cases:
            self.provider(case)
            with self.assertRaisesRegex(DWSBusinessError,'request_timeout'):self.dws.call(['chat','+chat-messages'])
        self.provider({'outcome':'ok','data':{'messages':[self.error()]}})
        self.assertIn('messages',self.dws.call(['chat','+chat-messages']))
        self.assertEqual(self.result()['outcome'],'response_ok')

    def test_office_preserves_raw_bytes_exit_and_error_diagnostic(self):
        envelope=self.error();self.provider(envelope,4)
        result=execute(self.root,self.binary,'synthetic:profile',['doc','list'])
        self.assertEqual(result.returncode,4);self.assertEqual(result.stdout,b'')
        self.assertEqual(json.loads(result.stderr),envelope)
        self.assertEqual(self.result()['reason'],'request_timeout');self.assertNotIn('SECRET',json.dumps(self.rows()))
        self.assertEqual({x['operation'] for x in self.rows()},{'office'})

    def test_spawn_failure_has_no_private_exception_text(self):
        with patch('dingtalk_bridge.core.run_dws',side_effect=OSError('SECRET')):
            with self.assertRaisesRegex(BridgeError,'dws_spawn_failed'):self.dws.call(['chat','+chat-messages'])
        self.assertEqual(self.result()['phase'],'spawn');self.assertEqual(self.result()['reason'],'spawn_failed')
        self.assertNotIn('SECRET',json.dumps(self.rows()))

    def test_unknown_codes_and_invalid_types_are_not_inferred_from_messages(self):
        for value in ('SECRET',['SECRET'],{'SECRET':'SECRET'},123456789):
            error={field:value for field in ('category','reason','server_error_code','origin','stage','code','retryable','execution_started')}
            diag=safe_dws_diagnostic({'error':error},7,.125)
            self.assertNotIn('SECRET',json.dumps(diag));self.assertNotIn('providerCode',diag)
            self.assertNotIn('providerRetryable',diag);self.assertNotIn('providerExecutionStarted',diag)
        self.assertNotIn('providerCode',safe_dws_diagnostic({'error':{'code':True}},0,0))

    def test_journal_failure_cannot_erase_successful_send_response(self):
        self.provider({'success':True,'sendReceipt':{'openTaskId':'SECRET'}})
        original=os.open
        def fail(path,*args,**kwargs):
            if Path(path).name=='dws-call-audit.ndjson':raise OSError('SECRET')
            return original(path,*args,**kwargs)
        out=io.StringIO()
        with patch('dingtalk_bridge.dws_access.os.open',side_effect=fail),contextlib.redirect_stderr(out):
            result=self.dws.call(['chat','+messages-send'])
        self.assertEqual(result['sendReceipt']['openTaskId'],'SECRET')
        self.assertEqual(self.access.status(),{'state':'ready'});self.assertNotIn('SECRET',out.getvalue())

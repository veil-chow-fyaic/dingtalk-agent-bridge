"""Local credential-store failures must be useful without exposing provider error text."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from urllib.request import Request, build_opener, ProxyHandler

from dingtalk_bridge.core import Bridge, BridgeError, DWS
from dingtalk_bridge.doctor import diagnose
from dingtalk_bridge.routing import Hub

ROOT = Path(__file__).resolve().parents[1]
ERROR = {'category': 'internal', 'code': 51, 'message':
    'resolve access token: load access token: load from keychain: read DEK from macOS Keychain: exit status 51; private-marker'}
CODE = 'credential_store_unavailable'


class CredentialHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);(self.root / 'local').mkdir()
        self.binary = self.root / 'dws'
        self.binary.write_text('#!' + sys.executable + '''
import json,sys
from pathlib import Path
a=sys.argv
with Path('calls').open('a') as f:f.write(json.dumps(a[1:])+'\\n')
group=a[a.index('--group')+1] if '--group' in a else 'a'
if '+conversation-info' in a:
 print(json.dumps({'result':{'conversationInfo':{'openConversationId':group}}}));raise SystemExit(0)
state=json.loads(Path(group+'.json').read_text());print(json.dumps(state['data']));raise SystemExit(state['exit'])
''')
        self.binary.chmod(0o700)
        self.routes = [dict(accountId='account', profile='synthetic-profile', conversationId=c,
            selfSenderId='self', conversationType='group', binary='dws', name='synthetic') for c in ('a', 'b')]
        self.config = {'routes': self.routes}
        (self.root / 'local/service-config.json').write_text(json.dumps(self.config))
        self.set_response('a', {'error': ERROR}, 51);self.healthy('b')

    def set_response(self, group, data, exit_code=0):
        destination = self.root / (group + '.json');temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps({'exit': exit_code, 'data': data}));temporary.replace(destination)

    def healthy(self, group):
        self.set_response(group, {'messages': [{'messageId': 'same-message', 'conversationId': group,
            'senderId': 'other', 'text': 'synthetic'}], 'complete': True})

    def test_exact_official_shape_gets_safe_typed_error(self):
        with self.assertRaises(BridgeError) as caught:DWS(self.root, self.routes[0]).call(['chat', '+chat-messages', '--group', 'a'])
        self.assertEqual(type(caught.exception).__name__, 'DWSCredentialStoreUnavailable')
        self.assertEqual(str(caught.exception), CODE)
        self.assertNotIn('private-marker', str(caught.exception))

    def test_exit51_or_keychain_word_alone_does_not_classify(self):
        errors = [dict(ERROR, message='unrelated failure'), dict(ERROR, code=50), dict(ERROR, code='51'),
            dict(ERROR, category='authorization'), {'reason': 'keychain_unavailable'}, None, [], 'private-marker']
        for error in errors:
            with self.subTest(error=error):
                self.set_response('a', {'error': error}, 51)
                with self.assertRaises(BridgeError) as caught:DWS(self.root, self.routes[0]).call(['chat', '+chat-messages', '--group', 'a'])
                self.assertNotEqual(type(caught.exception).__name__, 'DWSCredentialStoreUnavailable')

    def test_routes_remain_independent_and_recovery_clears_details_without_duplicates(self):
        hub = Hub(self.root, self.config);self.addCleanup(hub.close)
        hub.poll();rows = hub.health()['routes']
        self.assertEqual(rows[0]['poll_error_detail']['code'], CODE)
        self.assertIsNone(rows[0]['last_sync']);self.assertEqual(rows[0]['events'], 0)
        self.assertIsNone(rows[1]['poll_error_detail']);self.assertEqual(rows[1]['events'], 1)
        self.assertNotIn('private-marker', json.dumps(rows))
        rows[0]['poll_error_detail']['code']='caller-change'
        self.assertEqual(hub.health()['routes'][0]['poll_error_detail']['code'], CODE)
        self.set_response('a', {'error': {'message': 'other private-marker'}}, 51)
        hub.poll();self.assertIsNone(hub.health()['routes'][0]['poll_error_detail'])
        self.healthy('a');hub.poll();hub.poll()
        health = hub.health();self.assertFalse(health['poll_error'])
        self.assertTrue(all(r['poll_error_detail'] is None and r['events'] == 1 for r in health['routes']))
        self.assertNotIn('+messages-send', (self.root / 'calls').read_text())

    def test_doctor_reconstructs_only_allowlisted_diagnostic(self):
        token = self.root / 'local/runtime/http-token';token.parent.mkdir();token.write_text('synthetic-token');token.chmod(0o600)
        now = datetime.now(timezone.utc)
        rows = [dict(account_id='account', conversation_id=c, last_sync={'at': now.isoformat(), 'complete': True},
            poll_error='BridgeError', poll_error_detail={'code': CODE, 'message': 'private-marker', 'token': 'private-marker'}) for c in ('a', 'b')]
        report = diagnose(self.root, live=True, now=now, health_reader=lambda *_: {'routes': rows})
        errors = [c for c in report['checks'] if c['check'] == 'poll_error']
        self.assertFalse(report['ok']);self.assertTrue(all(c['detail']['code'] == CODE for c in errors))
        self.assertNotIn('private-marker', json.dumps(report))
        for row in rows:row['poll_error_detail'] = {'code': 'private-marker'}
        unknown = diagnose(self.root, live=True, now=now, health_reader=lambda *_: {'routes': rows})
        self.assertNotIn('private-marker', json.dumps(unknown))
        self.assertTrue(all('detail' not in c for c in unknown['checks'] if c['check'] == 'poll_error'))

    def test_send_failure_remains_unknown_and_same_key_never_resends(self):
        config = {**self.routes[0], 'group': 'a'}
        bridge = Bridge(self.root, config)
        try:
            failed = bridge.send('stable-key', text='synthetic task')
            self.assertEqual(failed['state'], 'outcome_unknown')
            self.assertNotIn('private-marker', json.dumps(failed))
            self.assertTrue(bridge.send('stable-key', text='synthetic task')['replayed'])
        finally:bridge.close()
        restarted = Bridge(self.root, config)
        try:
            self.assertEqual(restarted.delivery('stable-key')['state'], 'outcome_unknown')
            self.assertTrue(restarted.send('stable-key', text='synthetic task')['replayed'])
        finally:restarted.close()
        calls = [json.loads(line) for line in (self.root / 'calls').read_text().splitlines()]
        self.assertEqual(sum('+messages-send' in args for args in calls), 1)

    def test_real_http_scheduler_reports_and_clears_credential_failure(self):
        with socket.socket() as sock:sock.bind(('127.0.0.1', 0));port = sock.getsockname()[1]
        child = subprocess.Popen([sys.executable, '-m', 'dingtalk_bridge', '--port', str(port), '--poll-seconds', '5'],
            cwd=self.root, env={**os.environ, 'PYTHONPATH': str(ROOT)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        token = self.root / 'local/runtime/http-token'
        def health():
            request = Request(f'http://127.0.0.1:{port}/v1/health', headers={'Authorization': 'Bearer ' + token.read_text().strip()})
            with build_opener(ProxyHandler({})).open(request, timeout=3) as response:return json.load(response)
        def until(predicate):
            deadline = time.monotonic() + 9
            while time.monotonic() < deadline:
                self.assertIsNone(child.poll())
                if token.exists():
                    try:
                        result = health()
                        if predicate(result):return result
                    except OSError:pass
                time.sleep(.05)
            self.fail('Expected scheduler state did not appear')
        try:
            failed = until(lambda h: h['poll_error'] and h['routes'][1]['events'] == 1)
            self.assertEqual(failed['routes'][0]['poll_error_detail']['code'], CODE)
            self.assertNotIn('private-marker', json.dumps(failed))
            self.healthy('a')
            recovered = until(lambda h: not h['poll_error'] and h['routes'][0]['events'] == 1)
            self.assertTrue(all(r['poll_error_detail'] is None for r in recovered['routes']))
            self.assertNotIn('+messages-send', (self.root / 'calls').read_text())
        finally:
            child.send_signal(signal.SIGTERM)
            try:status = child.wait(timeout=8)
            except subprocess.TimeoutExpired:child.kill();child.wait();self.fail('Synthetic server did not stop')
        self.assertEqual(status, 0)


if __name__ == '__main__':unittest.main()

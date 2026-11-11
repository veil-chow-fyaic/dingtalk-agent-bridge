from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from dingtalk_bridge.doctor import diagnose, fetch_health
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge import cli


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'local/runtime').mkdir(parents=True)
        self.binary = self.root / 'dws'
        self.binary.write_text('not executed by doctor')
        self.binary.chmod(0o700)
        self.route = dict(accountId='private-account', profile='private-profile',
                          conversationId='private-conversation', selfSenderId='private-sender',
                          conversationType='group', binary='dws')
        self.config = {'routes': [self.route]}
        self.save()
        token = self.root / 'local/runtime/http-token'
        token.write_text('private-token')
        token.chmod(0o600)
        self.now = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)

    def save(self):
        (self.root / 'local/service-config.json').write_text(json.dumps(self.config))

    def health(self):
        return {'account_id': self.route['accountId'], 'conversation_id': self.route['conversationId'],
                'poll_error': None, 'last_sync': {'at': self.now.isoformat(), 'complete': True}}

    def report(self, **kwargs):
        return diagnose(self.root, now=self.now, **kwargs)

    def test_offline_never_calls_health_or_creates_state(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        reader = Mock(side_effect=AssertionError('offline network call'))
        report = self.report(health_reader=reader)
        self.assertTrue(report['ok'])
        reader.assert_not_called()
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertNotIn('private-', json.dumps(report))

    def test_missing_or_placeholder_config_fails_without_initialization(self):
        self.route['profile'] = '<choose profile>'
        self.save()
        self.assertFalse(self.report()['ok'])
        absent = self.root / 'missing'
        self.assertFalse(diagnose(absent)['ok'])
        self.assertFalse(absent.exists())
        (self.root / 'local/service-config.json').write_text('{}')
        self.assertFalse(self.report(live=True, health_reader=lambda *_: self.health())['ok'])

    def test_deadline_configuration_is_finite_positive_and_read_only(self):
        settings={'accountId':self.route['accountId'],'conversationId':self.route['conversationId'],
                  'allowedSenderIds':['private-allowed'],'runtime':{'kind':'kimi','binary':str(self.binary)}}
        path=self.root/'local/agent.json'
        values=[(float('nan'),False),(float('inf'),False),(float('-inf'),False),(0,False),(-1,False),
                (True,False),('90',False),(None,False),(10**1000,False),(.1,True),(90,True)]
        for index,(value,valid) in enumerate(values):
            with self.subTest(case=index):
                settings['runtime']['timeoutSeconds']=value;path.write_text(json.dumps(settings))
                before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
                with patch('subprocess.Popen',side_effect=AssertionError('doctor must not execute')):
                    report=self.report(agents=['local/agent.json'])
                self.assertEqual(report['ok'],valid)
                self.assertIn({'scope':'agent-1','check':'runtime_timeout_seconds','status':'ok' if valid else 'error'},report['checks'])
                self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
                self.assertNotIn('private-',json.dumps(report))

    def test_live_checks_exact_scope_freshness_completeness_and_errors(self):
        self.assertTrue(self.report(live=True, health_reader=lambda *_: self.health())['ok'])
        variants = []
        for field, value in [('conversation_id', 'wrong'), ('poll_error', 'secret-error')]:
            h = self.health(); h[field] = value; variants.append(h)
        for value in [{'at': '2026-11-11T11:58:00+00:00', 'complete': True},
                      {'at': self.now.isoformat(), 'complete': False}, {'at': 'invalid', 'complete': True}]:
            h = self.health(); h['last_sync'] = value; variants.append(h)
        variants.append({'routes': [self.health(), self.health()]})
        for health in variants:
            with self.subTest(health=health):
                report = self.report(live=True, health_reader=lambda *_: health)
                self.assertFalse(report['ok'])
                self.assertNotIn('secret-error', json.dumps(report))
                self.assertNotIn('private-', json.dumps(report))

    def test_scope_binding_mismatch_is_detected_without_repair(self):
        cfg, state = next(route_configs(self.config))
        folder = self.root / 'local/runtime/routes' / state
        folder.mkdir(parents=True)
        path = folder / 'bridge.sqlite3'
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript('CREATE TABLE meta(key TEXT,value TEXT); CREATE TABLE deliveries(state TEXT);')
            db.execute('INSERT INTO meta VALUES (?,?)', ('scope', json.dumps(['wrong-profile', cfg['group']])))
            db.execute('INSERT INTO deliveries VALUES ("upload_unknown")')
        before = path.read_bytes()
        connections = []
        connect = sqlite3.connect
        def tracked(*args, **kwargs):
            connection = connect(*args, **kwargs); connections.append(connection)
            return connection
        with patch('dingtalk_bridge.doctor.sqlite3.connect', side_effect=tracked):
            report = self.report()
        self.assertFalse(report['ok'])
        self.assertEqual(before, path.read_bytes())
        self.assertTrue(connections)
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
        self.assertTrue(any(c['check'] == 'unresolved_delivery' and c['detail']['count'] == 1 for c in report['checks']))

    def test_agent_allowlist_runtime_and_binding_are_independent_checks(self):
        settings = {'accountId': self.route['accountId'], 'conversationId': self.route['conversationId'],
                    'allowedSenderIds': ['private-allowed'], 'runtime': {'kind': 'kimi', 'binary': str(self.binary)}}
        path = self.root / 'local/agent.json'
        path.write_text(json.dumps(settings))
        self.assertTrue(self.report(agents=['local/agent.json'])['ok'])
        for mutation in [{'allowedSenderIds': []}, {'runtime': {'kind': 'kimi', 'binary': './dws'}},
                         {'bridgeConfig': 'another.json'}, {'conversationId': 'wrong'}]:
            with self.subTest(mutation=mutation):
                path.write_text(json.dumps({**settings, **mutation}))
                self.assertFalse(self.report(agents=['local/agent.json'])['ok'])
        path.write_text(json.dumps(settings))
        binding_scope = json.dumps([self.route['accountId'], self.route['profile'], self.route['conversationId'], 'group'])
        folder = self.root / 'local/agents' / hashlib.sha256(binding_scope.encode()).hexdigest()[:24]
        folder.mkdir(parents=True)
        with closing(sqlite3.connect(folder / 'tasks.sqlite3')) as db, db:
            db.executescript('CREATE TABLE meta(key TEXT,value TEXT); CREATE TABLE jobs(state TEXT);')
            db.execute('INSERT INTO meta VALUES ("binding",?)', (json.dumps([binding_scope, 'codex', str(self.binary)]),))
        self.assertFalse(self.report(agents=['local/agent.json'])['ok'])

    def test_build_digest_and_private_token_permissions(self):
        self.route['imageUploadBinary'] = 'dws'; self.save()
        (self.root / 'dws.build.json').write_text(json.dumps({'binarySha256': hashlib.sha256(self.binary.read_bytes()).hexdigest()}))
        self.assertTrue(self.report()['ok'])
        self.binary.write_text('changed executable')
        self.assertFalse(self.report()['ok'])
        self.route.pop('imageUploadBinary'); self.save()
        (self.root / 'local/runtime/http-token').chmod(0o644)
        self.assertFalse(self.report()['ok'])

    def test_authentication_failure_is_redacted(self):
        reader = Mock(side_effect=HTTPError('http://private-url', 401, 'private-secret', {}, None))
        report = self.report(live=True, health_reader=reader)
        self.assertFalse(report['ok'])
        self.assertNotIn('private-', json.dumps(report))
        self.assertTrue(any(c.get('detail') == 'authentication_rejected' for c in report['checks']))

    def test_loopback_health_does_not_forward_token_on_redirect(self):
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                paths.append(self.path)
                self.send_response(302)
                self.send_header('Location', '/unexpected')
                self.end_headers()
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with self.assertRaises(HTTPError) as caught:
                fetch_health(self.root, server.server_port)
            caught.exception.close()
        finally:
            server.shutdown(); server.server_close(); thread.join()
        self.assertEqual(paths, ['/v1/health'])

    def test_installed_cli_token_defaults_to_workspace_not_package(self):
        def token(path, *args, **kwargs):
            self.assertEqual(path, Path('local/runtime/http-token'))
            return 'synthetic-token'
        def response(request, **kwargs):
            self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-token')
            return io.StringIO('{"ok": true}')
        with patch.object(Path, 'read_text', autospec=True, side_effect=token), \
                patch.object(cli, 'urlopen', side_effect=response), \
                patch('sys.argv', ['dab', 'health']), patch('sys.stdout', new_callable=io.StringIO):
            cli.main()

    def test_cli_quote_preserves_route_reference_and_stdin_text(self):
        def response(request, **kwargs):
            self.assertEqual(json.loads(request.data), {'account_id': 'a', 'conversation_id': 'g',
                'idempotency_key': 'quote', 'reply_to': 'source', 'text': 'quoted\n中文'})
            self.assertTrue(request.full_url.endswith('/v1/send'))
            return io.StringIO('{"state":"confirmed"}')
        with patch.object(Path, 'read_text', return_value='synthetic-token'), \
                patch.object(cli, 'urlopen', side_effect=response), \
                patch('sys.argv', ['dab', '--account-id', 'a', '--conversation-id', 'g', 'send',
                                   '--key', 'quote', '--reply-to', 'source', '--text-stdin']), \
                patch('sys.stdin', io.StringIO('quoted\n中文')), patch('sys.stdout', new_callable=io.StringIO):
            cli.main()


if __name__ == '__main__':
    unittest.main()
from contextlib import closing

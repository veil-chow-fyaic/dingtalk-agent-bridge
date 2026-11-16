"""Incomplete history must not be reported as error-free; safe paging is progress."""
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
from urllib.request import Request, ProxyHandler, build_opener

from dingtalk_bridge.routing import Hub

ROOT = Path(__file__).resolve().parents[1]


class HistoryHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root / 'local').mkdir()
        binary = self.root / 'synthetic-dws'
        binary.write_text('#!' + sys.executable + '''
import json,sys
from pathlib import Path
a=sys.argv
with Path('calls').open('a') as out:out.write(json.dumps(a[1:])+'\\n')
group=a[a.index('--group')+1]
if '+conversation-info' in a:data={'result':{'conversationInfo':{'openConversationId':group}}}
elif '+chat-messages' in a:data=json.loads(Path(group+'.json').read_text())
else:raise SystemExit(92)
print(json.dumps(data))
''')
        binary.chmod(0o700)
        self.config = {'routes': [dict(accountId='synthetic', profile='synthetic-profile',
            conversationId=c, conversationType='group', selfSenderId='self', binary=binary.name,
            name='synthetic') for c in ('a', 'b')]}
        (self.root / 'local/service-config.json').write_text(json.dumps(self.config))
        self.response('a'); self.response('b')

    def response(self, route, **fields):
        data = {'messages': [{'messageId': 'm-'+route, 'conversationId': route,
                 'senderId': 'other', 'text': 'fixture'}], 'complete': True, 'hasMore': False}
        data.update(fields)
        path = self.root / (route + '.json'); temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data)); temp.replace(path)

    def snapshot(self, bridge):
        with bridge.lock:
            return dict(bridge.db.execute('SELECT key,value FROM meta'))

    def test_partial_failure_flags_remain_visible_after_reopen_and_clear_on_success(self):
        for fields in ({'partial': True}, {'failedCount': 1},
                       {'failures': [{'message': 'private-failure-marker'}]}):
            with self.subTest(fields=list(fields)):
                self.response('a', **fields)
                hub = Hub(self.root, self.config)
                try:
                    hub.poll(); health = hub.health()
                    self.assertTrue(health['poll_error'])
                    self.assertEqual(health['routes'][0]['poll_error'], 'HistoryIncomplete')
                    self.assertIsNone(health['routes'][1]['poll_error'])
                    self.assertNotIn('private-failure-marker', json.dumps(health))
                    before = self.snapshot(hub.select('synthetic', 'a'))
                    self.assertIn('history_window', before)
                finally: hub.close()
                hub = Hub(self.root, self.config)
                try:
                    # No poll after reopening: persistent incomplete sync cannot turn green.
                    self.assertTrue(hub.health()['poll_error'])
                    self.assertEqual(self.snapshot(hub.select('synthetic', 'a')), before)
                    self.response('a'); hub.poll(); health = hub.health()
                    self.assertFalse(health['poll_error'])
                    after = self.snapshot(hub.select('synthetic', 'a'))
                    self.assertEqual(after['watermark'], json.loads(before['history_window'])['end'])
                    self.assertNotIn('history_window', after)
                    self.assertEqual([r['events'] for r in health['routes']], [1, 1])
                finally: hub.close()

    def test_safe_limit_continuation_is_progress_even_with_no_new_messages(self):
        for reason in ('page_limit', 'result_limit'):
            with self.subTest(reason=reason):
                self.response('a', messages=[], complete=False, hasMore=True,
                              stopReason=reason, nextPageToken='synthetic-page-2')
                hub = Hub(self.root, self.config)
                try:
                    hub.poll(); health = hub.health(); row = health['routes'][0]
                    self.assertFalse(row['last_sync']['complete'])
                    self.assertTrue(row['last_sync']['continuing'])
                    self.assertFalse(health['poll_error'])
                    window = json.loads(self.snapshot(hub.select('synthetic', 'a'))['history_window'])
                    self.assertEqual(window['token'], 'synthetic-page-2')
                    self.response('a'); hub.poll()
                    self.assertFalse(hub.health()['poll_error'])
                    self.assertEqual(self.snapshot(hub.select('synthetic', 'a'))['watermark'], window['end'])
                finally: hub.close()

    def test_incomplete_without_safe_continuation_is_not_healthy(self):
        self.response('a', complete=False)
        hub = Hub(self.root, self.config)
        try:
            self.assertFalse(hub.health()['poll_error'])
            self.assertIsNone(hub.health()['routes'][0]['last_sync'])
            hub.poll(); row = hub.health()['routes'][0]
            self.assertEqual(row['poll_error'], 'HistoryIncomplete')
            self.assertFalse(row['last_sync']['continuing'])
            self.assertNotIn('watermark', self.snapshot(hub.select('synthetic', 'a')))
            self.assertEqual(row['events'], 1)
        finally: hub.close()

    def test_live_http_reports_background_and_explicit_sync_failures_without_resend(self):
        self.response('a', partial=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        env = {k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy')}
        env.update(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.Popen([sys.executable, '-m', 'dingtalk_bridge', '--port', str(port),
                                  '--poll-seconds', '3600'], cwd=self.root, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        opener = build_opener(ProxyHandler({}))
        def request(path, body=None):
            token = (self.root / 'local/runtime/http-token').read_text().strip()
            req = Request(f'http://127.0.0.1:{port}'+path,
                          headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'},
                          data=json.dumps(body).encode() if body is not None else None)
            with opener.open(req, timeout=3) as response: return json.load(response)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                self.assertIsNone(child.poll())
                try:
                    h = request('/v1/health')
                    if h['poll_scheduler']['last_completed_at'] is not None: break
                except OSError: pass
                time.sleep(.03)
            else: self.fail('Synthetic server did not finish its first poll')
            self.assertTrue(h['poll_error'])
            self.assertEqual(h['routes'][0]['poll_error'], 'HistoryIncomplete')
            self.response('a'); self.assertTrue(request('/v1/sync', {'account_id':'synthetic','conversation_id':'a'})['complete'])
            self.assertFalse(request('/v1/health')['poll_error'])
            for fields in ({'partial':True}, {'failedCount':1}, {'failures':[{'message':'private-failure-marker'}]}):
                self.response('a', **fields)
                self.assertFalse(request('/v1/sync', {'account_id':'synthetic','conversation_id':'a'})['complete'])
                h = request('/v1/health'); self.assertTrue(h['poll_error'])
                self.assertNotIn('private-failure-marker', json.dumps(h))
            self.response('a', complete=False, hasMore=True, stopReason='page_limit', nextPageToken='synthetic-next')
            self.assertFalse(request('/v1/sync', {'account_id':'synthetic','conversation_id':'a'})['complete'])
            self.assertFalse(request('/v1/health')['poll_error'])
            self.response('a'); self.assertTrue(request('/v1/sync', {'account_id':'synthetic','conversation_id':'a'})['complete'])
            h = request('/v1/health'); self.assertFalse(h['poll_error'])
            self.assertEqual([r['events'] for r in h['routes']], [1, 1])
            self.assertEqual(h['poll_scheduler']['cycles'], 1)
            calls = [json.loads(line) for line in (self.root / 'calls').read_text().splitlines()]
            self.assertTrue(all('+conversation-info' in a or '+chat-messages' in a for a in calls))
        finally:
            child.send_signal(signal.SIGTERM)
            try: code = child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(); self.fail('Synthetic service did not stop')
        self.assertEqual(code, 0)


if __name__ == '__main__': unittest.main()

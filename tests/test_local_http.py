"""Real loopback requests, synthetic tokens, no DWS, model or live bridge."""
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request

from dingtalk_bridge import cli, consume, agent_gateway, local_http


@contextmanager
def server(status=200, location=None):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({'authorization': self.headers.get('Authorization'),
                             'path': self.path, 'method': self.command})
            body = b'{"events":[],"next_cursor":0,"ok":true}'
            self.send_response(status)
            if location: self.send_header('Location', location)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        do_POST = do_GET
        def log_message(self, *args): pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try: yield f'http://127.0.0.1:{httpd.server_port}', requests
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=3)


class LocalHTTPTests(unittest.TestCase):
    def test_all_three_public_clients_connect_directly_with_hostile_proxy_environment(self):
        with tempfile.TemporaryDirectory() as directory, server() as (base, direct), server() as (proxy, diverted):
            root = Path(directory); (root/'local/runtime').mkdir(parents=True)
            (root/'local/runtime/http-token').write_text('synthetic-only')
            config = {'accountId':'test-account','profile':'test-profile','group':'test-chat',
                      'selfSenderId':'test-self','binary':'never-executed'}
            (root/'local/service-config.json').write_text(json.dumps(config))
            # Only replace the fixed endpoint with this test's owned random port.
            # The real shared opener, proxy environment and redirect machinery run.
            def request(url, *args, **kwargs):
                self.assertTrue(url.startswith('http://127.0.0.1:18768/'))
                return Request(url.replace('http://127.0.0.1:18768', base, 1), *args, **kwargs)
            env = {k:proxy for k in ('http_proxy','HTTP_PROXY','https_proxy','HTTPS_PROXY','all_proxy','ALL_PROXY')}
            env.update(no_proxy='',NO_PROXY='')
            before = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,env,clear=True):
                    with patch.object(cli,'Request',request), patch.object(sys,'argv',['dab','health']), redirect_stdout(io.StringIO()) as output:
                        cli.main()
                    self.assertTrue(json.loads(output.getvalue())['ok'])
                    with patch.object(consume,'Request',request), patch.object(sys,'argv',['dab-consume']), redirect_stdout(io.StringIO()) as output:
                        consume.main()
                    self.assertEqual(json.loads(output.getvalue())['fetched'],0)
                    gateway = agent_gateway.Gateway.__new__(agent_gateway.Gateway)
                    gateway.root=root; gateway.scope={'account_id':'test-account','conversation_id':'test-chat'}
                    with patch.object(agent_gateway,'Request',request): self.assertTrue(gateway.http('/v1/health')['ok'])
            finally: os.chdir(before)
            self.assertEqual(diverted,[])
            self.assertEqual(len(direct),3)
            self.assertTrue(all(r['authorization']=='Bearer synthetic-only' for r in direct))
            self.assertFalse((root/'local/runtime/bridge.sqlite3').exists())

    def test_redirects_never_forward_token_or_payload(self):
        with server() as (sink, leaked):
            for code in (301,302,303,307,308):
                for body in (None,b'{"text":"synthetic-only"}'):
                    with self.subTest(status=code,post=body is not None), server(code,sink+'/sink') as (origin, requests):
                        with self.assertRaises(HTTPError) as caught:
                            local_http.urlopen(Request(origin+'/v1/send',data=body,headers={'Authorization':'Bearer synthetic-only'}),timeout=2)
                        self.assertEqual(caught.exception.code,code); caught.exception.close()
                        self.assertEqual(len(requests),1)
            self.assertEqual(leaked,[])

    def test_external_ambiguous_and_credentialed_targets_rejected_before_opener(self):
        urls=['https://127.0.0.1:1234/a','http://example.invalid:1234/a','http://localhost:1234/a',
              'http://127.0.0.1/a','http://user:pass@127.0.0.1:1234/a','http://127.0.0.1:0/a',
              'http://127.0.0.1:65536/a','http://127.0.0.1:1234/a#fragment']
        with patch.object(local_http,'build_opener') as opener:
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError): local_http.urlopen(Request(url))
            with self.assertRaises(ValueError): local_http.urlopen('http://127.0.0.1:1234/a')
            opener.assert_not_called()

    def test_http_errors_remain_visible(self):
        with server(401) as (base, requests):
            with self.assertRaises(HTTPError) as caught: local_http.urlopen(Request(base+'/v1/health'),timeout=2)
            self.assertEqual(caught.exception.code,401); caught.exception.close()
            self.assertEqual(len(requests),1)


if __name__=='__main__': unittest.main()

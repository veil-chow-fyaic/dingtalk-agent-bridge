import argparse
import hmac
import json
import os
from pathlib import Path
import secrets
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from .core import BridgeError, ArtifactIntegrityError
from .routing import Hub
from .stream import StreamListener
from .provenance import startup_evidence


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description='Generic DWS IM bridge; runtime-neutral account/conversation routes')
    p.add_argument('--config', default='local/service-config.json')
    p.add_argument('--port', type=int, default=18768)
    p.add_argument('--poll-seconds', type=int, default=15)
    a = p.parse_args()
    if not 5 <= a.poll_seconds <= 3600:
        p.error('poll-seconds must be 5..3600')
    root = Path.cwd().resolve()
    config_path = root / a.config
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    hub = Hub(root, config)
    for bridge in hub.routes.values():bridge.validate_target()
    token_path = root / 'local/runtime/http-token'
    if not token_path.exists():
        token_path.write_text(secrets.token_urlsafe(32))
    token_path.chmod(0o600)
    token = token_path.read_text().strip()
    stop = threading.Event()
    wake = threading.Event()
    scheduler_lock=threading.Lock()
    scheduler={'cycles':0,'stream_hint_cycles':0,'timer_cycles':0,'last_trigger':None,
               'last_started_at':None,'last_completed_at':None}
    listeners={key:StreamListener(root,b.config,wake.set) for key,b in hub.routes.items()
               if b.config.get('receiveMode')=='stream_hint'}

    def poll():
        trigger='startup'
        while not stop.is_set():
            wake.clear()
            with scheduler_lock:
                scheduler['cycles']+=1
                if trigger in {'stream_hint','timer'}:scheduler[trigger+'_cycles']+=1
                scheduler.update(last_trigger=trigger,last_started_at=time.time())
            hub.poll(stop)
            with scheduler_lock:scheduler['last_completed_at']=time.time()
            wake.wait(a.poll_seconds)
            trigger='stream_hint' if wake.is_set() else 'timer'
            if trigger=='stream_hint':stop.wait(1)  # coalesce bursts; no unbounded event queue

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'

        def setup(self):
            super().setup()
            self.connection.settimeout(35)

        def log_message(self, *args):
            pass  # No message text, credentials or URLs in access logs.

        def respond(self, code, data):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def handle_request(self, write=False):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                return self.respond(401, {'error': 'unauthorized'})
            try:
                u = urlparse(self.path)
                data = {}
                if write:
                    n = int(self.headers.get('Content-Length', '0'))
                    if not 0 <= n <= 1024 * 1024:
                        return self.respond(413, {'error': 'payload_too_large'})
                    data = json.loads(self.rfile.read(n) or b'{}')
                    if not isinstance(data, dict):
                        raise ValueError('JSON object required')
                if not write and u.path == '/v1/health':
                    with scheduler_lock:polling=dict(scheduler)
                    return self.respond(200, {**hub.health(),'poll_scheduler':polling,'stream_listeners':[
                        {'account_id':k[0],'conversation_id':k[1],**s.status()} for k,s in listeners.items()]})
                if not write and u.path == '/v1/conversations':
                    return self.respond(200, {'conversations':hub.conversations()})
                q = parse_qs(u.query)
                if not write and u.path == '/v1/discovery':
                    return self.respond(200,hub.discover(q.get('account_id',[None])[0],
                        cursor=int(q.get('cursor',['0'])[0]),limit=int(q.get('limit',['50'])[0])))
                account = data.get('account_id') if write else q.get('account_id',[None])[0]
                conversation = data.get('conversation_id') if write else q.get('conversation_id',[None])[0]
                bridge = hub.select(account,conversation)
                if not write and u.path == '/v1/events':
                    q = parse_qs(u.query)
                    after = int(q.get('after', ['0'])[0])
                    events = bridge.events(after, int(q.get('limit', ['100'])[0]),float(q.get('wait_seconds',['0'])[0]))
                    return self.respond(200, {'account_id':bridge.config.get('accountId','default'),'conversation_id':bridge.config['group'],
                        'events': events, 'next_cursor': events[-1]['seq'] if events else after})
                if not write and u.path.startswith('/v1/deliveries/'):
                    value = bridge.delivery(unquote(u.path[len('/v1/deliveries/'):]))
                    return self.respond(200 if value else 404, value or {'error': 'not_found'})
                if write and u.path == '/v1/sync':
                    return self.respond(200, bridge.sync(deep=data.get('deep') is True))
                if write and u.path == '/v1/send':
                    value = bridge.send(data.get('idempotency_key'), data.get('text'), data.get('file'), data.get('image'),
                                        data.get('reply_to'), data.get('expected_sha256'), data.get('composition'))
                    return self.respond(200 if value['state'] == 'confirmed' else 202, value)
                if write and u.path == '/v1/reconcile':
                    return self.respond(200, bridge.reconcile(data['idempotency_key'], data.get('rejection_evidence')))
                if write and u.path == '/v1/attachments':
                    return self.respond(200, bridge.download(data['message_id'],repair=data.get('repair') is True))
                self.respond(404, {'error': 'not_found'})
            except ArtifactIntegrityError:
                self.respond(409, {'error': 'artifact_integrity_mismatch', 'delivery_attempted': False})
            except (ValueError, KeyError, TypeError) as e:
                self.respond(400, {'error': str(e)})
            except BridgeError as e:
                self.respond(502, {'error': str(e)})
            except Exception:
                self.respond(500, {'error': 'internal_error'})

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request(True)

    server = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    server.daemon_threads = False
    worker = threading.Thread(target=poll, daemon=True)
    worker.start()
    stream_workers=[threading.Thread(target=s.run,args=(stop,),daemon=True) for s in listeners.values()]
    for stream_worker in stream_workers:stream_worker.start()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(json.dumps({'listening': f'http://127.0.0.1:{a.port}', 'mode': 'experimental',
                      'token_file': str(token_path), 'auto_reply': False,
                      'startupEvidence': startup_evidence({config_path: config_bytes})}), flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        wake.set()
        for bridge in hub.routes.values():bridge.stop_waiters()
        server.server_close()
        worker.join()
        for stream_worker in stream_workers:stream_worker.join(timeout=35)
        hub.close()


if __name__ == '__main__':
    main()

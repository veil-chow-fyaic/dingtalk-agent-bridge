#!/usr/bin/env python3
"""Pinned official OpenClaw + synthetic provider: gateway SIGKILL, recovery, new.

Only newly owned gateway/CLI/tool processes are involved. No DWS, real provider,
credentials, production state or service control. All raw evidence stays local.
The test-only read/launch tripwire is not an OS sandbox.
"""
import argparse
from contextlib import chdir
import hashlib
import http.server
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.openclaw_runtime import expected_agents
from dingtalk_bridge.service_manager import process_identity
from review_openclaw_local_host import review_guard

ROUTE = {'profile': 'synthetic:person', 'accountId': 'synthetic-account',
         'group': 'synthetic-chat', 'selfSenderId': 'synthetic-self', 'binary': 'never-dws'}


def event(seq, task):
    raw = {'conversationId': ROUTE['group'], 'messageId': 'synthetic-' + str(seq),
           'senderId': 'synthetic-sender', 'createTime': '2026-11-15 12:00:00', 'text': '/agent ' + task}
    return {'seq': seq, 'message_id': raw['messageId'], 'conversation_id': raw['conversationId'],
            'from_self': False, 'source': 'dws_history', 'raw': raw}


class MemoryTransport:
    def __init__(self):
        self.events = [event(1, 'CRASH_GATEWAY_MARKER')]
        self.sends = {}

    def __call__(self, path, data=None):
        if path.startswith('/v1/events?'):
            cursor = int(parse_qs(urlparse(path).query)['after'][0])
            events = [e for e in self.events if e['seq'] > cursor]
            return {'events': events, 'next_cursor': events[-1]['seq'] if events else cursor}
        if path == '/v1/send':
            key = data['idempotency_key']
            if key in self.sends and self.sends[key] != data:
                raise AssertionError('Synthetic receipt key changed payload')
            self.sends[key] = data.copy()
            return {'state': 'confirmed', 'message_id': key}
        raise AssertionError('Unexpected transport operation')


def tree(root):
    rows = []
    for line in subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,comm='], text=True).splitlines():
        cols = line.strip().split(None, 3)
        if len(cols) == 4:
            rows.append({'pid': int(cols[0]), 'ppid': int(cols[1]), 'pgid': int(cols[2]), 'comm': cols[3]})
    owned = {root}
    for _ in range(16):
        owned.update(r['pid'] for r in rows if r['ppid'] in owned)
    return [r for r in rows if r['pid'] in owned]


def snapshot(path):
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        return {'meta': dict(db.execute('SELECT key,value FROM meta')),
                'jobs': [dict(r) for r in db.execute('SELECT * FROM jobs ORDER BY seq')],
                'outbox': [dict(r) for r in db.execute('SELECT * FROM outbox ORDER BY key')]}


def worker(folder):
    settings = json.loads((folder / 'settings.json').read_text())
    gateway = Gateway(folder, ROUTE, None, settings, MemoryTransport())
    try:
        gateway.intake()
        gateway.execute_one()
    finally:
        gateway.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--product-freeze', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
        return 0
    if not all((args.source_root, args.product_freeze, args.output_dir)):
        parser.error('source-root, product-freeze and output-dir are required')
    with chdir(args.source_root):
        source = Path.cwd()
    folder = args.output_dir.resolve()
    if not folder.is_relative_to(ROOT / 'local'):
        parser.error('Output must stay under local/')
    manifest = json.loads((ROOT / 'docs/references/openclaw-local-host-contract.json').read_text())
    extra = json.loads((ROOT / 'docs/references/openclaw-adapter-contract.json').read_text())
    product = json.loads(args.product_freeze.read_text())['codeSha256']
    code = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'dingtalk_bridge').glob('*.py')}
    if code != product or extra['commit'] != manifest['commit']:
        raise SystemExit('Frozen product/contract mismatch')
    for item in manifest['files'] + extra['files']:
        if hashlib.sha256((source / item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise SystemExit('Pinned upstream source changed')
    if json.loads((source / 'dist/build-info.json').read_text())['commit'] != manifest['commit']:
        raise SystemExit('Pinned build mismatch')
    node = shutil.which('node')
    if not node:
        raise SystemExit('Explicit local Node unavailable')
    folder.mkdir(parents=True, exist_ok=False)
    guard = (ROOT / 'fixtures/openclaw-credential-guard.mjs').read_text().replace(
        'const root=path.dirname(fileURLToPath(import.meta.url));',
        'const root=' + json.dumps(str(folder)) + ';\nconst source=' + json.dumps(str(source)) + ';')
    (folder / 'guard.mjs').write_text(guard)
    wrapper = folder / 'synthetic-only-openclaw'
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\n'
        + 'os.environ["NODE_OPTIONS"]=' + repr('--import ' + str(folder / 'guard.mjs')) + '\n'
        + 'os.environ["GIT_COMMIT"]=' + repr(manifest['commit']) + '\n'
        + 'os.execv(' + repr(node) + ',' + repr([node, str(source / 'openclaw.mjs')]) + '+sys.argv[1:])\n')
    wrapper.chmod(0o700)
    requests, checks, observations = [], {}, {}
    phase = 'crash'
    work = None

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            index = sum(x['phase'] == phase for x in requests)
            requests.append({'phase': phase, 'payload': payload})
            (folder / 'requests.json').write_text(json.dumps(requests, indent=2))
            delta, finish = {'role': 'assistant'}, 'stop'
            if phase == 'crash' and index == 0:
                code = "import pathlib,time,os,json; pathlib.Path('tool-start.json').write_text(json.dumps({'pid':os.getpid(),'at':time.time()})); time.sleep(10); pathlib.Path('late.txt').write_text('late')"
                command = shlex.quote(sys.executable) + ' -c ' + shlex.quote(code)
                delta['tool_calls'] = [{'index': 0, 'id': 'call_crash', 'type': 'function', 'function': {
                    'name': 'exec', 'arguments': json.dumps({'command': command, 'workdir': str(work),
                    'timeoutSeconds': 25, 'yieldMs': 10000, 'awaitResults': True})}}]
                finish = 'tool_calls'
            else:
                delta['content'] = json.dumps({'text': 'GATEWAY_FRESH_OK' if phase == 'fresh' else 'UNEXPECTED_CRASH_RESULT', 'files': []})
            chunk = {'id': 'fixture-' + phase, 'object': 'chat.completion.chunk', 'created': int(time.time()),
                'model': 'model', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            try:
                self.wfile.write(('data: ' + json.dumps(chunk) + '\n\ndata: [DONE]\n\n').encode())
            except BrokenPipeError:
                pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    config = {'agents': expected_agents('fixture/model'), 'plugins': {'enabled': False},
        'env': {'shellEnv': {'enabled': False}}, 'tools': {'allow': ['exec', 'process'], 'codeMode': False,
        'swarm': False, 'exec': {'host': 'gateway', 'security': 'full', 'ask': 'off'}, 'fs': {'workspaceOnly': True}},
        'models': {'mode': 'replace', 'providers': {'fixture': {'api': 'openai-completions',
        'apiKey': 'synthetic-unused', 'baseUrl': f'http://127.0.0.1:{server.server_port}/v1',
        'request': {'allowPrivateNetwork': True}, 'models': [{'id': 'model', 'name': 'Fixture',
        'reasoning': False, 'contextWindow': 32768, 'maxTokens': 512}]}}}}
    path = folder / 'host.json'
    path.write_text(json.dumps(config, indent=2))
    settings = {'allowedSenderIds': ['synthetic-sender'], 'runtime': {'kind': 'openclaw',
        'binary': str(wrapper), 'model': 'fixture/model', 'timeoutSeconds': 45,
        'openclaw': {'configPath': str(path), 'configSha256': hashlib.sha256(path.read_bytes()).hexdigest()}}}
    (folder / 'settings.json').write_text(json.dumps(settings))
    (folder / 'freeze.json').write_text(json.dumps({'codeSha256': code, 'upstreamCommit': manifest['commit'],
        'driverSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'python': sys.version.split()[0],
        'node': subprocess.check_output([node, '--version'], text=True).strip()}, indent=2))
    api = MemoryTransport()
    gateway = None
    owner = None
    try:
        gateway = Gateway(folder, ROUTE, None, settings, api)
        work, local = gateway.workspace(), gateway.local
        gateway.close()
        gateway = None
        with (folder / 'gateway.log').open('wb') as log:
            owner = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', str(folder)], stdout=log, stderr=log)
            deadline = time.monotonic() + 35
            while not (work / 'tool-start.json').exists():
                if owner.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('Tool readiness absent before owned gateway kill')
                time.sleep(.02)
            started = json.loads((work / 'tool-start.json').read_text())
            owned = tree(owner.pid)
            (folder / 'owned-tree.json').write_text(json.dumps(owned, indent=2))
            if started['pid'] not in {r['pid'] for r in owned}:
                raise RuntimeError('Tool is not in the newly owned gateway descendant tree')
            before = snapshot(local / 'tasks.sqlite3')
            (folder / 'before-kill.json').write_text(json.dumps(before, indent=2))
            checks['running_with_persisted_uuid_before_kill'] = (before['jobs'][0]['state'] == 'running'
                and len(before['meta']['session_id']) == 36 and 'session_contract' in before['meta'])
            owner.kill()
            observations['gatewayExitCode'] = owner.wait(timeout=5)
            checks['gateway_sigkill'] = observations['gatewayExitCode'] == -9
            deadline = time.monotonic() + 15
            remaining = lambda: [r['pid'] for r in owned if process_identity(r['pid'])]
            while remaining() and time.monotonic() < deadline:
                time.sleep(.05)
            observations['aliveAfterCleanup'] = remaining()
            checks['captured_owned_processes_gone'] = not observations['aliveAfterCleanup']
            while time.time() < started['at'] + 12:
                time.sleep(.1)
            observations['secondsAfterToolStart'] = time.time() - started['at']
            observations['ownedProcessCount'] = len(owned)
            checks['no_late_after_tool_deadline'] = not (work / 'late.txt').exists()
            stderr = (local / 'runs' / before['jobs'][0]['id'] / 'stderr.log').read_text()
            checks['pipe_eof_reached_native_interrupt'] = 'gateway_pipe_closed' in stderr and 'sent_and_exited' in stderr
            checks['crash_not_validated'] = not (local / 'runs' / before['jobs'][0]['id'] / 'validated-response.json').exists()
        request_count = len(requests)
        for i in range(2):
            gateway = Gateway(folder, ROUTE, None, settings, api)
            gateway.intake()
            checks['restart_' + str(i) + '_no_execution'] = not gateway.execute_one()
            gateway.flush()
            gateway.close()
            gateway = None
        recovered = snapshot(local / 'tasks.sqlite3')
        (folder / 'recovered.json').write_text(json.dumps(recovered, indent=2))
        checks['restart_no_provider_call'] = len(requests) == request_count
        checks['interrupted_not_completed_or_requeued'] = (recovered['jobs'][0]['state'] == 'interrupted'
            and recovered['jobs'][0]['error'] == 'process_restart' and recovered['jobs'][0]['result'] is None)
        checks['old_session_contract_binding_preserved'] = recovered['meta'] == before['meta']
        checks['only_original_ack_and_single_interrupt_notice'] = (len(api.sends) == 2 and
            set(api.sends) == {'agent-' + before['jobs'][0]['id'] + '-' + suffix for suffix in ('ack', 'interrupted')})
        gateway = Gateway(folder, ROUTE, None, settings, api)
        api.events.append(event(2, 'new'))
        gateway.intake()
        checks['native_new_executed'] = gateway.execute_one()
        new_meta = dict(gateway.db.execute('SELECT key,value FROM meta'))
        archive = json.loads(new_meta.get('session_history/0', '{}'))
        checks['native_new_archives_exact_old_contract'] = archive == {'sessionId': before['meta']['session_id'],
            'contract': json.loads(before['meta']['session_contract'])}
        checks['new_clears_session_and_preserves_binding'] = (new_meta['generation'] == '1' and
            new_meta['binding'] == before['meta']['binding'] and 'session_id' not in new_meta and 'session_contract' not in new_meta)
        phase = 'fresh'
        api.events.append(event(3, 'FRESH_GATEWAY_MARKER'))
        gateway.intake()
        checks['fresh_task_executed'] = gateway.execute_one()
        gateway.flush()
        fresh_meta = dict(gateway.db.execute('SELECT key,value FROM meta'))
        checks['fresh_uuid_and_generation'] = fresh_meta['session_id'] != before['meta']['session_id'] and gateway.workspace() != work
        fresh_job = dict(gateway.db.execute('SELECT * FROM jobs WHERE seq=3').fetchone())
        checks['fresh_completed_and_delivered'] = (fresh_job['state'] == 'completed' and
            any(x.get('text') == '[Agent] GATEWAY_FRESH_OK' for x in api.sends.values()))
        fresh_requests = [x for x in requests if x['phase'] == 'fresh']
        checks['fresh_provider_has_no_old_history'] = len(fresh_requests) == 1 and 'CRASH_GATEWAY_MARKER' not in json.dumps(fresh_requests)
        body = json.loads((local / 'runs' / fresh_job['id'] / 'events.jsonl').read_text())
        checks['official_workspace_matches_new_generation'] = body['meta']['systemPromptReport']['workspaceDir'] == str(gateway.workspace())
        checks['interrupted_job_unchanged_after_new'] = dict(gateway.db.execute('SELECT * FROM jobs WHERE seq=1').fetchone()) == recovered['jobs'][0]
        (folder / 'final-ledger.json').write_text(json.dumps(snapshot(local / 'tasks.sqlite3'), indent=2))
        (folder / 'synthetic-deliveries.json').write_text(json.dumps(api.sends, indent=2))
        checks['only_two_official_turns'] = len(requests) == 2
        checks['config_not_rewritten'] = hashlib.sha256(path.read_bytes()).hexdigest() == settings['runtime']['openclaw']['configSha256']
        checks['read_launch_boundaries'] = review_guard(folder, source)['ok']
        checks['product_unchanged'] = all(hashlib.sha256((ROOT / 'dingtalk_bridge' / n).read_bytes()).hexdigest() == v for n, v in code.items())
    except BaseException as exc:
        (folder / 'failure.json').write_text(json.dumps({'type': type(exc).__name__, 'message': str(exc)}, indent=2))
        raise
    finally:
        if gateway is not None:
            gateway.close()
        if owner is not None and owner.poll() is None:
            owner.kill()
            owner.wait(timeout=5)
        server.shutdown()
        server.server_close()
        report = {'ok': len(checks) == 25 and all(checks.values()) and not (folder / 'failure.json').exists(),
            'checks': checks, 'observations': observations, 'providerRequests': len(requests),
            'realProvider': False, 'realDws': False, 'deployed': False}
        (folder / 'result.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

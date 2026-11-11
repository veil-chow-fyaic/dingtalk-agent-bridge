"""Read-only, redacted configuration/state checks; optional loopback health GET.

Does not instantiate a Bridge/Gateway, run DWS/runtime, refresh credentials,
send probes, repair state, or start/stop processes.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .routing import route_configs


def read(path):
    return json.loads(path.read_text())


def executable(root, value, search_path=False):
    if not isinstance(value, str) or not value or '<' in value:
        return False
    path = Path(shutil.which(value) or root / value) if search_path and '/' not in value else root / value
    return path.is_file() and os.access(path, os.X_OK)


def meta_and_counts(path, table):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        return dict(db.execute('SELECT key,value FROM meta')), dict(
            db.execute('SELECT state,count(*) FROM ' + table + ' GROUP BY state'))


def fetch_health(root, port):
    token = (root / 'local/runtime/http-token').read_text().strip()
    if not token:
        raise ValueError('empty_token')
    request = Request(f'http://127.0.0.1:{port}/v1/health',
                      headers={'Authorization': 'Bearer ' + token})
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    # Never forward the local bearer token via an environment proxy/redirect.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=5) as response:
        return json.load(response)


def diagnose(root, config_path='local/service-config.json', agents=(), *, live=False,
             port=18768, max_age=90, health_reader=fetch_health, now=None):
    root = Path(root).resolve()
    checks = []

    def add(scope, check, status, detail=None):
        row = {'scope': scope, 'check': check, 'status': status}
        if detail is not None:
            row['detail'] = detail
        checks.append(row)

    def finish():
        return {'schemaVersion': 1, 'mode': 'live_read_only' if live else 'offline_read_only',
                'ok': not any(c['status'] == 'error' for c in checks),
                'warnings': sum(c['status'] == 'warning' for c in checks), 'checks': checks,
                'limitations': ['No message delivery or UI acceptance performed',
                                'No runtime request or credential renewal performed',
                                'Does not prove process code version or long-term reliability']}

    try:
        configs = list(route_configs(read(root / config_path)))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        add('transport', 'configuration', 'error', 'missing_or_invalid_config')
        return finish()
    add('transport', 'configuration', 'ok', {'routes': len(configs)})
    for index, (cfg, state) in enumerate(configs, 1):
        scope = f'route-{index}'
        fields = ('accountId', 'profile', 'group', 'selfSenderId')
        ready = all(isinstance(cfg.get(k), str) and cfg[k] and '<' not in cfg[k] for k in fields)
        add(scope, 'explicit_identity', 'ok' if ready else 'error')
        if not ready:
            continue
        add(scope, 'dws_executable', 'ok' if executable(root, cfg.get('binary')) else 'error')
        add(scope, 'receive_mode', 'ok' if cfg.get('receiveMode', 'history') in ('history', 'stream_hint') else 'error')
        image = cfg.get('imageUploadBinary')
        if image and isinstance(image, str):
            add(scope, 'image_upload_executable', 'ok' if executable(root, image) else 'error')
            binary = root / image
            try:
                build = read(Path(str(binary) + '.build.json'))
                matches = hashlib.sha256(binary.read_bytes()).hexdigest() == build['binarySha256']
                add(scope, 'image_upload_build_digest', 'ok' if matches else 'error')
            except (OSError, ValueError, KeyError, TypeError):
                add(scope, 'image_upload_build_digest', 'warning', 'no_verifiable_build_record')
        elif image:
            add(scope, 'image_upload_executable', 'error')
        else:
            add(scope, 'native_image_upload', 'warning', 'not_configured')
        directory = root / 'local/runtime'
        if state is not None:
            directory = directory / 'routes' / state
        db = directory / 'bridge.sqlite3'
        if not db.exists():
            add(scope, 'transport_ledger', 'warning', 'not_initialized')
        else:
            try:
                meta, counts = meta_and_counts(db, 'deliveries')
                add(scope, 'transport_binding', 'ok' if meta.get('scope') == json.dumps([cfg['profile'], cfg['group']]) else 'error')
                unknown = sum(counts.get(k, 0) for k in ('upload_unknown', 'outcome_unknown', 'uploading', 'executing'))
                add(scope, 'unresolved_delivery', 'warning' if unknown else 'ok', {'count': unknown})
                rejected, failed = counts.get('rejected', 0), counts.get('failed', 0)
                add(scope, 'terminal_delivery_failure', 'warning' if rejected + failed else 'ok',
                    {'rejected': rejected, 'failed': failed})
            except (sqlite3.Error, OSError, ValueError):
                add(scope, 'transport_ledger', 'error', 'unreadable_ledger')
    for index, path in enumerate(agents, 1):
        scope = f'agent-{index}'
        try:
            settings = read(root / path)
            selected = [c for c, _ in configs if c['accountId'] == settings['accountId'] and c['group'] == settings['conversationId']]
            same_config = (root / settings.get('bridgeConfig', 'local/service-config.json')).resolve() == (root / config_path).resolve()
            if len(selected) != 1 or not same_config:
                raise ValueError('wrong_route')
            cfg = selected[0]
            allowed = settings['allowedSenderIds']
            valid = isinstance(allowed, list) and bool(allowed) and all(isinstance(v, str) and v and '<' not in v for v in allowed)
            add(scope, 'explicit_allowlist', 'ok' if valid else 'error')
            runtime = settings['runtime']
            binary = runtime.get('binary')
            supported = runtime['kind'] in ('kimi', 'codex') and isinstance(binary, str)
            # Runtime cwd is its task workspace, so root-relative binaries do
            # not have the same meaning as DWS's root-relative binary path.
            supported = supported and (Path(binary).is_absolute() or '/' not in binary)
            add(scope, 'runtime_executable', 'ok' if supported and executable(root, binary, search_path=True) else 'error')
            add(scope, 'self_commands', 'warning' if settings.get('allowSelfCommands', False) else 'ok')
            binding_scope = json.dumps([cfg['accountId'], cfg['profile'], cfg['group'], cfg['conversationType']])
            key = hashlib.sha256(binding_scope.encode()).hexdigest()[:24]
            db = root / 'local/agents' / key / 'tasks.sqlite3'
            if db.exists():
                meta, counts = meta_and_counts(db, 'jobs')
                expected = json.dumps([binding_scope, runtime['kind'], runtime['binary']])
                add(scope, 'runtime_binding', 'ok' if meta.get('binding') == expected else 'error')
                attention = sum(counts.get(k, 0) for k in ('blocked', 'failed', 'interrupted'))
                add(scope, 'retained_task_failures', 'warning' if attention else 'ok', {'count': attention})
            else:
                add(scope, 'task_ledger', 'warning', 'not_initialized')
        except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error):
            add(scope, 'configuration_or_ledger', 'error', 'invalid_agent_binding_or_settings')
    token_path = root / 'local/runtime/http-token'
    if token_path.exists():
        private = token_path.stat().st_mode & 0o077 == 0
        add('transport', 'token_file_permissions', 'ok' if private else 'error')
    else:
        add('transport', 'token_file', 'error' if live else 'warning', 'not_initialized')
    if live:
        try:
            health = health_reader(root, port)
            actual = health.get('routes', [health])
            expected = {(c['accountId'], c['group']) for c, _ in configs}
            seen = {(r.get('account_id'), r.get('conversation_id')) for r in actual}
            add('transport', 'live_route_set', 'ok' if seen == expected and len(actual) == len(expected) else 'error')
            current = now or datetime.now(timezone.utc)
            for index, row in enumerate(actual, 1):
                sync = row.get('last_sync') or {}
                try:
                    age = (current - datetime.fromisoformat(sync['at'])).total_seconds()
                    fresh = -5 <= age <= max_age and sync.get('complete') is True
                except (ValueError, KeyError, TypeError):
                    fresh = False
                add(f'live-route-{index}', 'complete_recent_sync', 'ok' if fresh else 'error')
                add(f'live-route-{index}', 'poll_error', 'error' if row.get('poll_error') else 'ok')
        except HTTPError as exc:
            add('transport', 'loopback_health', 'error', 'authentication_rejected' if exc.code == 401 else 'http_failure')
            exc.close()
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            add('transport', 'loopback_health', 'error', 'unavailable_or_invalid_response')
    return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--config', default='local/service-config.json')
    parser.add_argument('--agent-config', action='append', default=[])
    parser.add_argument('--live', action='store_true', help='GET authenticated loopback health only')
    parser.add_argument('--port', type=int, default=18768)
    parser.add_argument('--max-sync-age', type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or args.max_sync_age <= 0:
        parser.error('port must be 1..65535; max-sync-age must be positive')
    report = diagnose(args.root, args.config, args.agent_config, live=args.live,
                      port=args.port, max_age=args.max_sync_age)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()

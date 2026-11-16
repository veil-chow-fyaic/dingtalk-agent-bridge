"""Explicit, workspace-local lifecycle management. No login or boot services."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from .doctor import diagnose, fetch_health
from .routing import route_configs
from .provenance import source_manifest, verify_startup


def process_identity(pid, observation=None):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
        raise ValueError('Invalid managed PID')
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'stat=', '-o', 'lstart=', '-o', 'command='],
                            capture_output=True, text=True, timeout=5)
    fields = result.stdout.strip().split(None, 1)
    identity = fields[1] if result.returncode == 0 and len(fields) == 2 and not fields[0].startswith('Z') else None
    if observation is not None:
        observation.update(at=time.time(), pid=pid, returncode=result.returncode,
                           stdout=result.stdout, stderr=result.stderr, identity=identity)
    return identity


class Manager:
    def __init__(self, root, config='local/service-config.json', agents=()):
        self.root = Path(root).resolve()
        self.config = (self.root / config).resolve()
        self.agents = [(self.root / a).resolve() for a in agents]
        self.folder = self.root / 'local/runtime'
        self.state_path = self.folder / 'managed-processes.json'
        self.children = {}
        self.observations = {}

    def read_state(self):
        if not self.state_path.exists():
            return {'schemaVersion': 1, 'root': str(self.root), 'components': []}
        state = json.loads(self.state_path.read_text())
        if state.get('schemaVersion') != 1 or state.get('root') != str(self.root) or not isinstance(state.get('components'), list):
            raise ValueError('Manager record does not belong to this workspace')
        names = set()
        for record in state['components']:
            name = record.get('name')
            expected = 'dingtalk_bridge' if name == 'transport' else 'dingtalk_bridge.agent_gateway'
            if (not isinstance(name, str) or name in names or
                    (name != 'transport' and not (name.startswith('agent-') and name[6:].isdigit())) or
                    record.get('module') != expected or not isinstance(record.get('config'), str) or
                    not isinstance(record.get('identity'), str) or
                    '-m ' + expected + ' --config ' + record['config'] not in record['identity']):
                raise ValueError('Invalid managed component identity record')
            names.add(name)
        return state

    def save(self, state):
        temporary = self.state_path.with_suffix('.tmp')
        with temporary.open('w') as output:
            os.chmod(temporary, 0o600)
            json.dump(state, output, ensure_ascii=False, indent=2)
            output.write('\n'); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, self.state_path)

    @contextmanager
    def locked(self):
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.folder / 'manager.lock').open('a') as lock:
            os.chmod(lock.name, 0o600)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise RuntimeError('Another manager operation is in progress') from None
            yield

    def journal(self, event, name):
        with (self.folder / 'manager-events.ndjson').open('a') as output:
            os.chmod(output.name, 0o600)
            output.write(json.dumps({'at': time.time(), 'event': event, 'component': name}) + '\n')
            output.flush(); os.fsync(output.fileno())

    def observe_identity(self, pid):
        observation = {}
        current = process_identity(pid, observation)
        self.observations[pid] = observation
        return current

    def ownership_error(self, record, phase, message):
        # Persist the observation that caused this decision, not a second ps
        # sample after the process may have disappeared. Private local only.
        try:
            self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = self.folder / 'manager-identity-errors.ndjson'
            with path.open('a') as output:
                os.chmod(path, 0o600)
                output.write(json.dumps({'at': time.time(), 'phase': phase,
                    'component': record['name'], 'pid': record['pid'],
                    'expected': record['identity'],
                    'observed': self.observations.get(record['pid'])}) + '\n')
                output.flush(); os.fsync(output.fileno())
        except OSError:
            pass  # A diagnostic write failure must not change the refusal.
        raise RuntimeError(message)

    def component_status(self, record):
        child = self.children.get(record['pid'])
        if child and child.poll() is not None:
            return 'stopped'
        # Only this invocation has the Popen handle proving child ownership.
        # macOS Python replaces its launcher executable during startup.
        if child and record.get('starting') is True:
            return 'running'
        current = self.observe_identity(record['pid'])
        if current is None:
            return 'stopped'
        return 'running' if current == record['identity'] else 'ownership_mismatch'

    def status(self):
        state = self.read_state()
        components = [{'component': r['name'], 'status': self.component_status(r), 'pid': r['pid']}
                      for r in state['components']]
        return {'managed': bool(components), 'all_running': bool(components) and all(
            c['status'] == 'running' for c in components), 'components': components,
            'scope': 'Process ownership/liveness only; use dab-doctor --live for transport health'}

    def specs(self):
        preflight = diagnose(self.root, str(self.config), [str(p) for p in self.agents])
        if not preflight['ok']:
            raise ValueError('Configuration preflight failed; run dab-doctor for details')
        if len(set(self.agents)) != len(self.agents):
            raise ValueError('Duplicate agent configuration')
        scopes = set()
        for path in self.agents:
            settings = json.loads(path.read_text())
            if (self.root / settings.get('bridgeConfig', 'local/service-config.json')).resolve() != self.config:
                raise ValueError('Every managed agent must use the selected bridge configuration')
            scope = (settings['accountId'], settings['conversationId'])
            if scope in scopes:
                raise ValueError('Multiple managed agents cannot own the same conversation')
            scopes.add(scope)
        return [{'name': 'transport', 'module': 'dingtalk_bridge', 'config': str(self.config),
                 'configSha256': hashlib.sha256(self.config.read_bytes()).hexdigest()}] + [
            {'name': 'agent-' + str(i), 'module': 'dingtalk_bridge.agent_gateway', 'config': str(p),
             'configSha256': hashlib.sha256(p.read_bytes()).hexdigest()} for i, p in enumerate(self.agents, 1)]

    def plan(self):
        return {'components': [s['name'] for s in self.specs()], 'port': 18768,
                'activated': False, 'createsBootService': False}

    def command(self, spec):
        return [sys.executable, '-m', spec['module'], '--config', spec['config']]

    def port_unused(self):
        try:
            with socket.create_connection(('127.0.0.1', 18768), timeout=.5):
                return False
        except OSError:
            return True

    def spawn(self, spec):
        package = self.root / 'dingtalk_bridge'
        if not package.is_dir(): package = Path(__file__).parent
        launch_sources = source_manifest(package)
        log_path = self.folder / ('managed-' + spec['name'] + '.log')
        offset = log_path.stat().st_size if log_path.exists() else 0
        with log_path.open('ab') as log:
            os.chmod(log_path, 0o600)
            child = subprocess.Popen(self.command(spec), cwd=self.root, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=log, start_new_session=True)
        self.children[child.pid] = child
        try:
            expected = '-m ' + spec['module'] + ' --config ' + spec['config']
            deadline = time.monotonic() + 5
            while True:
                identity = process_identity(child.pid)
                if child.poll() is not None:
                    raise RuntimeError('Component exited before it could be recorded; inspect private manager logs')
                if identity and expected in identity:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Child command did not become identifiable; inspect private manager logs')
                time.sleep(.02)
        except BaseException:
            if child.poll() is None: child.terminate()
            child.wait(timeout=5)
            raise
        return {**spec, 'pid': child.pid, 'identity': identity, 'log': str(log_path.relative_to(self.root)),
                'logOffset': offset, 'startedAt': time.time(), 'starting': True,
                'launchSourceSha256': launch_sources}

    def ready(self, record):
        if self.component_status(record) != 'running':
            return False
        with (self.root / record['log']).open('rb') as log:
            log.seek(record['logOffset'])
            messages = []
            for line in log.read(256 * 1024).decode(errors='replace').splitlines():
                try:
                    value = json.loads(line)
                    if isinstance(value, dict): messages.append(value)
                except ValueError:
                    continue
        startup = [m['startupEvidence'] for m in messages if 'startupEvidence' in m]
        if startup:
            if len(startup) != 1:
                raise RuntimeError('Ambiguous startup provenance')
            record['startupEvidence'] = startup[0]
            paths = [Path(record['config'])]
            if record['name'] != 'transport': paths.append(self.config)
            configs = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            package = self.root / 'dingtalk_bridge'
            if not package.is_dir(): package = Path(__file__).parent
            if not verify_startup(record, source_manifest(package), configs):
                raise RuntimeError('Service startup source/config changed or provenance mismatched')
        if record['name'] == 'transport':
            if not any(m.get('listening') == 'http://127.0.0.1:18768' for m in messages):
                return False
            try:
                health = fetch_health(self.root, 18768)
                actual = health.get('routes', [health])
                expected = {(c['accountId'], c['group']) for c, _ in route_configs(json.loads(self.config.read_text()))}
                return {(c.get('account_id'), c.get('conversation_id')) for c in actual} == expected and len(actual) == len(expected)
            except (OSError, ValueError):
                return False
        return any(m.get('gateway') == 'ready' for m in messages)

    def wait_ready(self, record, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.ready(record):
                return
            if self.component_status(record) != 'running':
                break
            time.sleep(.2)
        raise RuntimeError('Component startup did not become ready; inspect private manager logs')

    def exiting_after_signal(self, record):
        # macOS ps can lose argv while the same process is exiting (?Es).
        # This permits waiting only, never signalling or claiming it is gone.
        observation = self.observations.get(record['pid'], {})
        fields = observation.get('stdout', '').split(None, 6)
        expected = record['identity'].split(None, 5)
        return (observation.get('returncode') == 0 and observation.get('pid') == record['pid']
                and len(fields) == 7 and len(expected) == 6 and 'E' in fields[0][1:]
                and fields[1:6] == expected[:5])

    def stop_component(self, record, timeout):
        status = self.component_status(record)
        if status == 'ownership_mismatch':
            self.ownership_error(record, 'stop-precheck', 'PID ownership changed; refusing to signal it')
        if status == 'stopped':
            return
        # Compare again at signal time; never signal by name or process group.
        own_starting_child = self.children.get(record['pid']) if record.get('starting') is True else None
        if not own_starting_child:
            current = self.observe_identity(record['pid'])
            # The owned process may exit between the liveness and signal checks.
            # Absence needs no signal; a different live identity still fails closed.
            if current is None:
                return
            if current != record['identity']:
                self.ownership_error(record, 'stop-before-signal', 'PID ownership changed at shutdown')
        try:
            if own_starting_child:
                own_starting_child.terminate()
            else:
                os.kill(record['pid'], signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.component_status(record)
            if state == 'stopped':
                self.journal('stopped', record['name'])
                return
            if state == 'ownership_mismatch' and not self.exiting_after_signal(record):
                self.ownership_error(record, 'stop-after-signal', 'PID changed during shutdown; no further signal sent')
            time.sleep(.2)
        raise RuntimeError('Graceful shutdown still pending; no force kill performed')

    def start(self, timeout=45):
        desired = self.specs()  # Validation is read-only and precedes all writes.
        with self.locked():
            state = self.read_state()
            existing = {r['name']: r for r in state['components']}
            for r in state['components']:
                status = self.component_status(r)
                if status == 'ownership_mismatch':
                    self.ownership_error(r, 'start-precheck', 'PID ownership mismatch; existing records were not overwritten')
                if status == 'running' and not any(all(r[k] == s[k] for k in s) for s in desired):
                    raise RuntimeError('Active configuration changed; stop the managed processes first')
            created = []
            try:
                for spec in desired:
                    old = existing.get(spec['name'])
                    if old and self.component_status(old) == 'running':
                        self.wait_ready(old, timeout)
                        continue
                    if spec['name'] == 'transport' and not self.port_unused():
                        raise RuntimeError('Port 18768 is used by an unmanaged process; no takeover attempted')
                    record = self.spawn(spec)
                    created.append(record)
                    existing[spec['name']] = record
                    state['components'] = list(existing.values())
                    self.save(state)
                    self.journal('started', spec['name'])
                    self.wait_ready(record, timeout)
                    # A ready module has finished the launcher transition.
                    # Persist this identity before relinquishing the Popen handle.
                    identity = process_identity(record['pid'])
                    if not identity:
                        raise RuntimeError('Ready component exited before identity was committed')
                    record['identity'] = identity
                    record.pop('starting', None)
                    self.save(state)
                # Remove only dead entries from an earlier, explicitly stopped plan.
                state['components'] = [existing[s['name']] for s in desired]
                self.save(state)
            except BaseException:
                rollback_errors = []
                for record in reversed(created):
                    try:
                        self.stop_component(record, timeout)
                    except Exception:
                        rollback_errors.append(record['name'])
                self.save(state)
                if rollback_errors:
                    raise RuntimeError('Startup failed and shutdown is still pending; records retained for stop') from None
                raise
        return self.status()

    def stop(self, timeout=45):
        # An absent state must not create any directories or affect a listener.
        if not self.state_path.exists():
            return self.status()
        with self.locked():
            state = self.read_state()
            for r in state['components']:
                if self.component_status(r) == 'ownership_mismatch':
                    self.ownership_error(r, 'stop-all-precheck', 'PID ownership mismatch; no process was signalled')
            for record in reversed(state['components']):
                self.stop_component(record, timeout)
        return self.status()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--config', default='local/service-config.json')
    parser.add_argument('--agent-config', action='append', default=[])
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('action', choices=['plan', 'start', 'stop', 'status'])
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error('timeout must be 1..120 seconds per component')
    manager = Manager(args.root, args.config, args.agent_config)
    try:
        result = (getattr(manager, args.action)(args.timeout) if args.action in {'start', 'stop'}
                  else getattr(manager, args.action)())
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
    ok = not any(c.get('status') == 'ownership_mismatch' for c in result.get('components', []) if isinstance(c, dict))
    if args.action == 'start': ok = ok and result['all_running']
    print(json.dumps({'ok': ok, **result}, ensure_ascii=False))
    if not ok: raise SystemExit(1)


if __name__ == '__main__':
    main()

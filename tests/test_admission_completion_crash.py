"""Kill an owned synthetic worker at durable admission/completion boundaries.

No DWS or model process is started. SQLite COMMIT traces terminate the process
before the actual commit; a separate connection after death checks durability.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import dingtalk_bridge.agent_gateway as gateway_module
from test_agent_gateway import CFG, SETTINGS, FakeAPI, FakeRuntime, event


class DurableAPI(FakeAPI):
    def __init__(self, root, phase=None):
        super().__init__()
        self.root = root
        self.phase = phase
        self.events = [event(text='/agent synthetic crash boundary')]
        self.returned_events = 0

    def __call__(self, path, data=None):
        if path.startswith('/v1/events'):
            result = super().__call__(path, data)
            self.returned_events += len(result['events'])
            return result
        if path != '/v1/send':
            raise AssertionError(path)
        # Synthetic transport owns idempotency independently of the gateway.
        with sqlite3.connect(self.root / 'provider.sqlite3') as db:
            db.execute('CREATE TABLE IF NOT EXISTS accepted(key TEXT PRIMARY KEY, payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts(key TEXT, payload TEXT)')
            payload = json.dumps(data, sort_keys=True)
            prior = db.execute('SELECT payload FROM accepted WHERE key=?', (data['idempotency_key'],)).fetchone()
            if prior and prior[0] != payload:
                raise AssertionError('Same key changed payload')
            db.execute('INSERT INTO attempts VALUES (?,?)', (data['idempotency_key'], payload))
            db.execute('INSERT OR IGNORE INTO accepted VALUES (?,?)', (data['idempotency_key'], payload))
        if self.phase == 'provider_accepted' and data['idempotency_key'].endswith('-text-0'):
            die(self.root, self.phase)
        return {'state': 'confirmed', 'message_id': data['idempotency_key']}


class DurableRuntime(FakeRuntime):
    def __init__(self, root):
        super().__init__()
        self.root = root

    def run(self, *args):
        # An externally committed tool effect cannot be rolled back with tasks.
        with sqlite3.connect(self.root / 'tool.sqlite3') as db:
            db.execute('CREATE TABLE IF NOT EXISTS calls(n INTEGER)')
            db.execute('INSERT INTO calls VALUES (1)')
        return super().run(*args)


def die(root, phase):
    (root / 'checkpoint.json').write_text(json.dumps({'phase': phase}))
    os.kill(os.getpid(), signal.SIGKILL)


def worker(root, phase):
    api = DurableAPI(root, phase)
    gateway = gateway_module.Gateway(root, CFG, None, SETTINGS, api, DurableRuntime(root))
    if phase == 'inbox_before_commit':
        gateway.inbox.db.set_trace_callback(
            lambda sql: die(root, phase) if sql == 'COMMIT' else None)
    if phase in {'admission_before_commit', 'terminal_before_commit'}:
        def before_commit(sql):
            if sql != 'COMMIT':
                return
            target = 'queued' if phase == 'admission_before_commit' else 'completed'
            if gateway.db.execute('SELECT 1 FROM jobs WHERE state=?', (target,)).fetchone():
                die(root, phase)
        gateway.db.set_trace_callback(before_commit)
    gateway.intake()
    if not gateway.execute_one():
        raise AssertionError('No synthetic task')
    if phase == 'terminal_after_commit':
        die(root, phase)
    gateway.flush()
    raise AssertionError('Crash checkpoint was not reached')


class AdmissionCompletionCrashTests(unittest.TestCase):
    def check_boundary(self, phase):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # Pin the child import to the same source or installed package as parent.
            env = {**os.environ, 'PYTHONPATH': str(Path(gateway_module.__file__).resolve().parent.parent)}
            child = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', temp, phase],
                                   cwd=root, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(child.returncode, -signal.SIGKILL, child.stderr)
            self.assertEqual(json.loads((root / 'checkpoint.json').read_text()), {'phase': phase})
            task_db = next((root / 'local/agents').glob('*/tasks.sqlite3'))
            inbox_db = next((root / 'local/consumers').glob('*/inbox.sqlite3'))
            with sqlite3.connect(task_db) as db:
                jobs = db.execute('SELECT state,result FROM jobs').fetchall()
                outbox = db.execute('SELECT key,payload,state FROM outbox ORDER BY key').fetchall()
            with sqlite3.connect(inbox_db) as db:
                cursor = int(db.execute('SELECT value FROM meta WHERE key="cursor"').fetchone()[0])
                inbox_count = db.execute('SELECT count(*) FROM inbox').fetchone()[0]
            early = phase in {'inbox_before_commit', 'admission_before_commit'}
            self.assertEqual(cursor, int(phase != 'inbox_before_commit'))
            self.assertEqual(inbox_count, cursor)
            self.assertEqual(len(jobs), int(not early))
            self.assertEqual(len(outbox), 0 if early else 1 if phase == 'terminal_before_commit' else 3)
            if not early:
                self.assertEqual(jobs[0][0], 'running' if phase == 'terminal_before_commit' else 'completed')
                self.assertEqual(jobs[0][1] is None, phase == 'terminal_before_commit')
            if phase == 'provider_accepted':
                pending_text = [r for r in outbox if r[0].endswith('-text-0')]
                self.assertEqual(pending_text[0][2], 'pending')
            api = DurableAPI(root)
            runtime = DurableRuntime(root)
            gateway = gateway_module.Gateway(root, CFG, None, SETTINGS, api, runtime)
            try:
                gateway.intake()
                self.assertEqual(api.returned_events, int(phase == 'inbox_before_commit'))
                self.assertEqual(gateway.execute_one(), early)
                gateway.flush()
                self.assertEqual(runtime.calls, int(early))
                self.assertEqual(gateway.db.execute('SELECT state FROM jobs').fetchone()[0],
                                 'interrupted' if phase == 'terminal_before_commit' else 'completed')
                if phase == 'terminal_before_commit':
                    self.assertEqual(gateway.db.execute('SELECT result FROM jobs').fetchone()[0], None)
                    self.assertEqual(gateway.db.execute('SELECT count(*) FROM outbox WHERE key LIKE "%-text-%" OR key LIKE "%-file-%"').fetchone()[0], 0)
                else:
                    if not early:
                        self.assertEqual([(r[0], r[1]) for r in outbox],
                                         [tuple(r) for r in gateway.db.execute('SELECT key,payload FROM outbox ORDER BY key')])
                    result = json.loads(gateway.db.execute('SELECT result FROM jobs').fetchone()[0])
                    artifact = result['artifacts'][0]
                    self.assertEqual(hashlib.sha256((root / artifact['file']).read_bytes()).hexdigest(), artifact['sha256'])
                self.assertEqual({r[0] for r in gateway.db.execute('SELECT state FROM outbox')}, {'confirmed'})
                before = [tuple(r) for r in gateway.db.execute('SELECT * FROM outbox ORDER BY key')]
                gateway.close()
                gateway = gateway_module.Gateway(root, CFG, None, SETTINGS, api, runtime)
                gateway.intake()
                self.assertFalse(gateway.execute_one())
                gateway.flush()
                self.assertEqual(before, [tuple(r) for r in gateway.db.execute('SELECT * FROM outbox ORDER BY key')])
                with sqlite3.connect(root / 'tool.sqlite3') as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM calls').fetchone()[0], 1)
                with sqlite3.connect(root / 'provider.sqlite3') as db:
                    accepted = db.execute('SELECT count(*) FROM accepted').fetchone()[0]
                    attempts = db.execute('SELECT count(*) FROM attempts').fetchone()[0]
                    self.assertEqual(accepted, 2 if phase == 'terminal_before_commit' else 3)
                    self.assertEqual(attempts, accepted + int(phase == 'provider_accepted'))
                print('admission_completion_crash: ' + json.dumps({'phase': phase, 'childExit': child.returncode,
                    'durableCursorAtCrash': cursor, 'jobsAtCrash': len(jobs), 'outboxAtCrash': len(outbox),
                    'runtimeCallsAcrossCrash': 1, 'providerAcceptedKeys': accepted, 'providerAttempts': attempts,
                    'secondRestartUnchanged': True}))
            finally:
                gateway.close()

    def test_inbox_and_cursor_rollback_together_on_sigkill(self):
        self.check_boundary('inbox_before_commit')

    def test_admission_and_ack_rollback_recover_from_inbox_without_replay(self):
        self.check_boundary('admission_before_commit')

    def test_completed_tool_before_terminal_commit_is_interrupted_never_rerun(self):
        self.check_boundary('terminal_before_commit')

    def test_terminal_commit_recovers_delivery_without_rerunning_tool(self):
        self.check_boundary('terminal_after_commit')

    def test_provider_accept_before_receipt_commit_reuses_identical_key_and_payload(self):
        self.check_boundary('provider_accepted')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()

#!/usr/bin/env python3
"""Explicit offline runtime binding migration after a completed /agent new.

Only changes the task ledger binding and adds an audit row. Does not start/stop
services, change config, invoke a runtime/DWS, or replay messages. Plans/receipts
contain private routing data and must remain below local/.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from dingtalk_bridge.agent_runtime import LocalRuntime, runtime_binding
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.service_manager import Manager


def digest(value):
    return hashlib.sha256(value).hexdigest()


def ledger_view(db):
    return {table: [list(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
            for table in ('meta', 'jobs', 'outbox')}


def fingerprint(view):
    return digest(json.dumps(view, ensure_ascii=False, separators=(',', ':')).encode())


def validate_ledger(db, old_binding):
    meta = dict(db.execute('SELECT key,value FROM meta'))
    if meta.get('binding') != old_binding:
        raise ValueError('runtime_binding_mismatch')
    if 'session_id' in meta or 'session_contract' in meta:
        raise ValueError('explicit_new_required')
    last = db.execute('SELECT command,state FROM jobs ORDER BY seq DESC LIMIT 1').fetchone()
    if not last or tuple(last) not in (('new', 'completed'), ('新会话', 'completed')):
        raise ValueError('last_job_must_be_completed_new')
    generation = meta.get('generation', '')
    if not generation.isdigit() or int(generation) < 1:
        raise ValueError('new_generation_required')
    if db.execute('SELECT count(*) FROM jobs WHERE state IN ("running","queued","waiting_media")').fetchone()[0]:
        raise ValueError('unfinished_jobs')
    if db.execute('SELECT count(*) FROM outbox WHERE state NOT IN ("confirmed","failed","rejected")').fetchone()[0]:
        raise ValueError('unconfirmed_outbox')
    return generation


def target_paths(root, from_config, to_config):
    old = json.loads(from_config.read_text())
    new = json.loads(to_config.read_text())
    if {k:v for k,v in old.items() if k != 'runtime'} != {k:v for k,v in new.items() if k != 'runtime'}:
        raise ValueError('only_runtime_configuration_may_change')
    LocalRuntime(old['runtime'])  # Validates configuration; never spawns a process.
    LocalRuntime(new['runtime'])
    route_file = root / new.get('bridgeConfig', 'local/service-config.json')
    routes = [c for c,_ in route_configs(json.loads(route_file.read_text()))
              if (c['accountId'], c['group']) == (new['accountId'], new['conversationId'])]
    if len(routes) != 1:
        raise ValueError('route_not_unique')
    route = routes[0]
    scope = json.dumps([route['accountId'], route['profile'], route['group'], route['conversationType']])
    old_binding = runtime_binding(scope, old['runtime'])
    new_binding = runtime_binding(scope, new['runtime'])
    if old_binding == new_binding:
        raise ValueError('binding_unchanged')
    return (root / 'local/agents' / digest(scope.encode())[:24] / 'tasks.sqlite3',
            old_binding, new_binding, route_file)


def require_stopped(manager, config):
    config = Path(config).resolve()
    records = [r for r in manager.read_state()['components']
               if r.get('module') == 'dingtalk_bridge.agent_gateway' and Path(r['config']).resolve() == config]
    if len(records) != 1 or manager.component_status(records[0]) != 'stopped':
        raise ValueError('owned_target_gateway_must_be_stopped')


def create_plan(root, from_config, to_config):
    db_path, old_binding, new_binding, route_file = target_paths(root, from_config, to_config)
    with closing(sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        generation = validate_ledger(db, old_binding)
        view = ledger_view(db)
    return {'schemaVersion': 1, 'database': str(db_path), 'fromConfig': str(from_config),
            'toConfig': str(to_config), 'fromConfigSha256': digest(from_config.read_bytes()),
            'toConfigSha256': digest(to_config.read_bytes()), 'routeFile': str(route_file),
            'routeSha256': digest(route_file.read_bytes()), 'oldBinding': old_binding,
            'newBinding': new_binding, 'generation': generation, 'ledgerSha256': fingerprint(view)}


def apply_transaction(db, plan, now):
    """Caller holds manager lock and owns a stopped gateway; atomic SQLite update."""
    db.execute('BEGIN IMMEDIATE')
    try:
        generation = validate_ledger(db, plan['oldBinding'])
        if generation != plan['generation'] or fingerprint(ledger_view(db)) != plan['ledgerSha256']:
            raise ValueError('ledger_changed_since_plan')
        history_key = 'runtime_binding_history/' + generation
        audit = {'from': plan['oldBinding'], 'to': plan['newBinding'], 'at': now,
                 'planLedgerSha256': plan['ledgerSha256'], 'configSha256': plan['toConfigSha256']}
        db.execute('INSERT INTO meta(key,value) VALUES(?,?)', (history_key, json.dumps(audit)))
        db.execute('UPDATE meta SET value=? WHERE key="binding"', (plan['newBinding'],))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return history_key


def private_path(root, value):
    path = Path(value).resolve()
    if not path.is_relative_to(root / 'local'):
        raise ValueError('plan_and_receipt_must_stay_local')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--from-config', type=Path)
    parser.add_argument('--to-config', type=Path)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    path = private_path(root, args.plan)
    manager = Manager(root)
    with manager.locked():
        if not args.apply:
            if not args.from_config or not args.to_config:
                parser.error('preparation needs --from-config and --to-config')
            old, new = args.from_config.resolve(), args.to_config.resolve()
            require_stopped(manager, new)
            plan = create_plan(root, old, new)
            with path.open('x') as output:
                json.dump(plan, output, indent=2)
            print(json.dumps({'prepared': True, 'automaticStart': False, 'generation': plan['generation']}))
            return
        plan = json.loads(path.read_text())
        old, new = Path(plan['fromConfig']), Path(plan['toConfig'])
        require_stopped(manager, new)
        # Re-derive paths/scope from the actual configs; do not trust plan paths.
        if create_plan(root, old, new) != plan:
            raise ValueError('plan_inputs_changed')
        receipt = private_path(root, str(path) + '.receipt.json')
        with receipt.open('x') as output:
            json.dump({'attempted': True, 'at': time.time(), 'planSha256': digest(path.read_bytes()),
                       'state': 'started', 'automaticRetry': False}, output)
        # A crash or unknown receipt never permits automatic repetition. Inspect
        # the original binding/history under the same plan before recovery.
        with closing(sqlite3.connect(Path(plan['database']).as_uri() + '?mode=rw', uri=True)) as db:
            history = apply_transaction(db, plan, time.time())
        receipt.write_text(json.dumps({'attempted': True, 'state': 'completed', 'at': time.time(),
                                      'historyKey': history, 'automaticStart': False}) + '\n')
        print(json.dumps({'migrated': True, 'automaticStart': False, 'generation': plan['generation']}))


if __name__ == '__main__':
    main()

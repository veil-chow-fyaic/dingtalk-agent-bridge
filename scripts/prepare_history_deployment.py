#!/usr/bin/env python3
"""Create a PRIVATE, read-only deployment review. No apply/start/DWS/network path.

Requires existing owner locks and checkpointed SQLite files without sidecars.
Never checkpoint a database, instantiate a worker, copy credentials or replay work.
"""
import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge.routing import route_configs

TERMINAL = {'confirmed', 'failed', 'rejected'}
JOB_TERMINAL = {'completed', 'failed', 'blocked', 'interrupted', 'cancelled'}
SIDECARS = ('-wal', '-shm', '-journal')
SAFE_ERRORS = {'input_outside_workspace','symlink_input_refused','required_input_missing',
               'input_changed_during_read','snapshot_changed','owner_lock_unavailable','owner_lock_busy',
               'sqlite_sidecar_requires_separate_review','sqlite_integrity_failed','expected_ledger_table',
               'invalid_ledger_state','operator_suspension_required','agent_bridge_config_mismatch',
               'duplicate_agent_scope','agent_sender_allowlist_missing','agent_route_set_mismatch',
               'invalid_validation_record','invalid_recovery_receipt','bridge_scope_mismatch',
               'gateway_binding_mismatch','inbox_scope_mismatch','invalid_or_outdated_review','invalid_review_key'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Snapshot:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.inputs = {}

    def path(self, name):
        path = Path(name)
        if not path.is_absolute():path = self.root / path
        try:relative = path.relative_to(self.root)
        except ValueError:raise ValueError('input_outside_workspace') from None
        if '..' in relative.parts:raise ValueError('input_outside_workspace')
        cursor = self.root
        for part in relative.parts:
            cursor /= part
            if cursor.is_symlink():raise ValueError('symlink_input_refused')
        return path

    def read(self, name, optional=False):
        path = self.path(name);key = str(path.relative_to(self.root))
        try:
            with path.open('rb') as stream:
                before = os.fstat(stream.fileno());data = stream.read();after = os.fstat(stream.fileno())
        except FileNotFoundError:
            if not optional:raise ValueError('required_input_missing') from None
            self.inputs[key] = None
            return None
        identity = lambda s:(s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if identity(before) != identity(after) or identity(after) != identity(path.stat()):
            raise ValueError('input_changed_during_read')
        entry = {'sha256':digest(data), 'size':len(data), 'mtimeNs':after.st_mtime_ns,
                 'device':after.st_dev, 'inode':after.st_ino}
        if key in self.inputs and self.inputs[key] != entry:raise ValueError('snapshot_changed')
        self.inputs[key] = entry
        return data

    def json(self, name, optional=False):
        raw = self.read(name, optional)
        return json.loads(raw) if raw is not None else None

    def verify(self):
        expected = dict(self.inputs)
        for name in expected:self.read(name, optional=expected[name] is None)
        if self.inputs != expected:raise ValueError('snapshot_changed')

    @contextmanager
    def owner_lock(self, name):
        path = self.path(name)
        # Existing files only; read-only fd, no creation/chmod or PID signalling.
        try:fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:raise ValueError('owner_lock_unavailable') from None
        try:
            try:fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:raise ValueError('owner_lock_busy') from None
            yield
        finally:os.close(fd)

    @contextmanager
    def database(self, name):
        path = self.path(name)
        self.read(path)
        for suffix in SIDECARS:
            if self.read(str(path)+suffix, optional=True) is not None:
                raise ValueError('sqlite_sidecar_requires_separate_review')
        # immutable avoids creating/modifying shm; permitted only after rejecting
        # every sidecar and acquiring existing writer-owner locks. No WAL ignored.
        db = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':raise ValueError('sqlite_integrity_failed')
            yield db
        finally:db.close()


def inventory(db, table, identity, state=False, details=True):
    # All SQL identifiers are internal constants, never supplied by a message.
    if not re.fullmatch(r'[a-z_]+', table) or not re.fullmatch(r'[a-z_]+', identity):raise ValueError('invalid_table')
    schema = db.execute('SELECT type FROM sqlite_master WHERE name=?', (table,)).fetchone()
    if not schema or schema[0] != 'table':
        raise ValueError('expected_ledger_table')
    rows=[];states={};fingerprint=hashlib.sha256();count=0
    for row in db.execute(f'SELECT * FROM {table} ORDER BY {identity}'):
        raw=json.dumps(dict(row),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
        fingerprint.update(len(raw).to_bytes(8,'big'));fingerprint.update(raw);count+=1
        entry={identity:row[identity], 'rowSha256':digest(raw)}
        if state:
            if not isinstance(row['state'],str):raise ValueError('invalid_ledger_state')
            entry['state']=row['state'];states[row['state']]=states.get(row['state'],0)+1
        if details:rows.append(entry)
    return {'count':count,'sha256':fingerprint.hexdigest(),'states':states,'rows':rows}


def meta_value(db, key):
    row=db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
    return row[0] if row else None


def create_plan(root, config, agents, validation):
    snap=Snapshot(root);root=snap.root
    with ExitStack() as locks:
        for name in ('local/runtime/manager.lock','local/runtime/dws-access.lock'):
            locks.enter_context(snap.owner_lock(name))
        if snap.json('local/runtime/dws-suspended.json') != {'reason':'operator_suspended'}:
            raise ValueError('operator_suspension_required')
        settings=snap.json(config);routes=list(route_configs(settings))
        agent_by_scope={}
        for path in agents:
            value=snap.json(path)
            if snap.path(value.get('bridgeConfig','local/service-config.json')) != snap.path(config):
                raise ValueError('agent_bridge_config_mismatch')
            scope=(value['accountId'],value['conversationId'])
            if scope in agent_by_scope:raise ValueError('duplicate_agent_scope')
            if not value.get('allowedSenderIds'):raise ValueError('agent_sender_allowlist_missing')
            agent_by_scope[scope]=(path,value)
        if set(agent_by_scope)!={(r['accountId'],r['group']) for r,_ in routes}:
            raise ValueError('agent_route_set_mismatch')
        paths=[]
        for route,state in routes:
            scope=json.dumps([route['accountId'],route['profile'],route['group'],route.get('conversationType','group')])
            key=digest(scope.encode())[:24]
            base='local/runtime'+('/routes/'+state if state else '')
            inbox='local/consumers/agent-'+key
            for name in (base+'/process.lock',inbox+'/process.lock'):
                locks.enter_context(snap.owner_lock(name))
            paths.append((base+'/bridge.sqlite3','local/agents/'+key+'/tasks.sqlite3',inbox+'/inbox.sqlite3',scope))
        validated=snap.json(validation)
        if not validated.get('ok') or not isinstance(validated.get('codeSha256'),dict):raise ValueError('invalid_validation_record')
        code={p.name:digest(snap.read(p)) for p in sorted((root/'dingtalk_bridge').glob('*.py'))}
        versions={'validatedEvidence':validated.get('evidence'),'validatedWheelSha256':validated.get('wheelSha256'),
                  'currentProductSha256':code,'validatedProductSha256':validated['codeSha256'],
                  'matchesValidated':code==validated['codeSha256']}
        receipt=snap.json('local/recovery-checks/dab-auth-read-20261112/receipt.json',optional=True)
        auth_state=receipt.get('state') if isinstance(receipt,dict) else 'not_attempted'
        if auth_state not in {'not_attempted','failed','readable','outcome_unknown','checking'}:raise ValueError('invalid_recovery_receipt')
        items=[];unfinished=unconfirmed=historical=0
        for index,((route,_),(bridge_path,tasks_path,inbox_path,scope)) in enumerate(zip(routes,paths)):
            agent_path,agent=agent_by_scope[(route['accountId'],route['group'])]
            with snap.database(bridge_path) as db:
                if meta_value(db,'scope') != json.dumps([route['profile'],route['group']]):raise ValueError('bridge_scope_mismatch')
                bridge={name:inventory(db,name,ident,state=state,details=details) for name,ident,state,details in
                    [('meta','key',False,True),('events','seq',False,False),('deliveries','key',True,True),
                     ('image_uploads','key',True,True),('rejection_audit','key',False,True)]}
            with snap.database(tasks_path) as db:
                if meta_value(db,'binding') != json.dumps([scope,agent['runtime']['kind'],agent['runtime']['binary']]):
                    raise ValueError('gateway_binding_mismatch')
                tasks={name:inventory(db,name,ident,state=state) for name,ident,state in
                       [('meta','key',False),('jobs','id',True),('outbox','key',True)]}
            with snap.database(inbox_path) as db:
                expected=json.dumps([route['accountId'],route['profile'],route['group'],route.get('selfSenderId'),route.get('historyTimezone','Asia/Shanghai')])
                if meta_value(db,'scope') != expected:raise ValueError('inbox_scope_mismatch')
                inbox={'meta':inventory(db,'meta','key'), 'inbox':inventory(db,'inbox','seq',state=True,details=False)}
            nonterminal_jobs=[r['id'] for r in tasks['jobs']['rows'] if r['state'] not in JOB_TERMINAL]
            old_problems=[r['id'] for r in tasks['jobs']['rows'] if r['state'] in JOB_TERMINAL-{'completed'}]
            delivery_by_key={r['key']:r for r in bridge['deliveries']['rows']}
            uncertain=sorted({r['key'] for r in bridge['deliveries']['rows']+tasks['outbox']['rows'] if r['state'] not in TERMINAL})
            uncertain=sorted(set(uncertain)|{r['key'] for r in bridge['image_uploads']['rows'] if r['state']!='uploaded'})
            cross_layer=[{'key':r['key'],'outboxState':r['state'],'transportState':delivery_by_key.get(r['key'],{}).get('state','absent')}
                         for r in tasks['outbox']['rows'] if r['state'] not in TERMINAL]
            unfinished+=len(nonterminal_jobs);unconfirmed+=len(uncertain);historical+=len(old_problems)
            items.append({'routeIndex':index,'conversationType':route['conversationType'],'agentConfig':str(snap.path(agent_path).relative_to(root)),
                          'configurationChange':{'receiveMode':{'before':route.get('receiveMode','history'),'after':'history'},
                            'identityChange':False,'senderAllowlistChange':False,'runtimeChange':False},
                          'bridge':bridge,'tasks':tasks,'inbox':inbox,
                          'review':{'unfinishedJobIds':nonterminal_jobs,'historicalNonSuccessJobIds':old_problems,
                                    'unconfirmedOriginalKeys':uncertain,'outboxTransportComparison':cross_layer}})
        snap.verify()
        summary={'routeCount':len(items),'unfinishedJobs':unfinished,'unconfirmedOriginalKeys':unconfirmed,
                 'historicalNonSuccessJobs':historical,'currentMatchesValidated':versions['matchesValidated'],
                 'priorSingleReadState':auth_state,'newDwsCallsAllowed':False,'backgroundStartAllowed':False}
        return {'schemaVersion':1,'purpose':'private_review_only','executable':False,
                'plannerSha256':digest(Path(__file__).read_bytes()),
                'capturedAt':datetime.now(timezone.utc).isoformat(),'versions':versions,'routes':items,
                'proposedPollSeconds':15,'summary':summary,'inputSnapshot':snap.inputs,
                'requires':['New explicit authorization before any real DWS call or background start',
                            'Recheck this snapshot before deciding any action; stale plan is not approval',
                            'Review original uncertain keys without resend, re-key or replay',
                            'Review queued/running/waiting-media effects before any gateway start',
                            'Apply latest UI/group scope; route inventory does not authorize group tests',
                            'Preserve original observation, maintenance, failed and blocked history'],
                'notAssessed':['Live authentication, server delivery and UI','Unmanaged processes outside these owner locks']}


def check_snapshot(root,plan):
    if (plan.get('schemaVersion')!=1 or plan.get('executable') is not False or
            plan.get('plannerSha256')!=digest(Path(__file__).read_bytes()) or
            not isinstance(plan.get('inputSnapshot'),dict) or not plan['inputSnapshot']):
        raise ValueError('invalid_or_outdated_review')
    snap=Snapshot(root);snap.inputs=dict(plan['inputSnapshot']);snap.verify()


def publish(root,key,plan):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',key):raise ValueError('invalid_review_key')
    check_snapshot(root,plan)
    snap=Snapshot(root);parent=snap.path('local/deployment-reviews')
    parent.mkdir(mode=0o700,exist_ok=True)
    directory=snap.path('local/deployment-reviews/'+key);directory.mkdir(mode=0o700)
    path=directory/'plan.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(plan,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default='.')
    p.add_argument('--config',default='local/service-config.json')
    p.add_argument('--agent-config',action='append',default=[])
    p.add_argument('--validation',default='evidence/2026-11-12/history-continuation-applied-validation.json')
    p.add_argument('--key',required=True)
    p.add_argument('--check',action='store_true',help='Only check an existing review for changed inputs; never rewrite it')
    args=p.parse_args()
    try:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',args.key):raise ValueError('invalid_review_key')
        if args.check:
            plan=Snapshot(args.root).json('local/deployment-reviews/'+args.key+'/plan.json')
            check_snapshot(args.root,plan)
            print(json.dumps({'ok':True,'snapshotUnchanged':True,'reviewWritten':False,
                              'newDwsCallsAllowed':False,'backgroundStartAllowed':False}))
            return 0
        plan=create_plan(args.root,args.config,args.agent_config,args.validation)
        publish(args.root,args.key,plan)
    except (OSError,ValueError,KeyError,TypeError,IndexError,sqlite3.Error) as exc:
        # Never echo raw config, SQL, account values or absolute private paths.
        code=str(exc) if str(exc) in SAFE_ERRORS else ('review_already_exists' if isinstance(exc,FileExistsError) else 'input_validation_failed')
        print(json.dumps({'ok':False,'errorType':type(exc).__name__,'errorCode':code,'reviewWritten':False}))
        return 1
    print(json.dumps({'ok':True,'reviewWritten':True,**plan['summary']}))
    return 0


if __name__=='__main__':raise SystemExit(main())

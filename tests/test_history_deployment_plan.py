from contextlib import closing
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge.core import Bridge
from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.routing import route_configs

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('history_deployment',ROOT/'scripts/prepare_history_deployment.py')
planner=importlib.util.module_from_spec(spec);spec.loader.exec_module(planner)


class HistoryDeploymentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='deployment review 空格 ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'local/runtime').mkdir(parents=True)
        for name in ('manager.lock','dws-access.lock'):(self.root/'local/runtime'/name).touch()
        (self.root/'local/runtime/dws-suspended.json').write_text('{"reason":"operator_suspended"}')
        (self.root/'dingtalk_bridge').mkdir();(self.root/'dingtalk_bridge/core.py').write_text('# synthetic code only\n')
        self.config='local/service-config.json';self.validation='local/validated.json';self.agents=[];self.dbpaths=[]
        routes=[]
        for kind in ('group','direct'):
            routes.append({'accountId':'synthetic-account-secret','profile':'synthetic-corp:synthetic-user',
                           'conversationId':'synthetic-'+kind,'conversationType':kind,'peerOpenDingTalkId':'synthetic-peer',
                           'selfSenderId':'synthetic-self','receiveMode':'stream_hint','binary':'never-execute','name':'synthetic'})
        (self.root/self.config).write_text(json.dumps({'routes':routes}))
        for index,(route,state) in enumerate(route_configs({'routes':routes})):
            agent={'accountId':route['accountId'],'conversationId':route['group'],'bridgeConfig':self.config,
                   'allowedSenderIds':['synthetic-user'],'runtime':{'kind':'synthetic','binary':'never-execute','timeoutSeconds':30}}
            name=f'local/agent-{index}.json';(self.root/name).write_text(json.dumps(agent));self.agents.append(name)
            bridge=Bridge(self.root,route,dws=object(),state_name=state)
            gateway=Gateway(self.root,route,state,agent,api=object(),runtime=object())
            try:
                bridge.db.execute('INSERT INTO events(message_id,body) VALUES (?,?)',('synthetic-message','DO_NOT_PRINT_PRIVATE_BODY'))
                for status in ('confirmed','failed','rejected','submitted','executing','outcome_unknown','upload_unknown','uploading'):
                    bridge.db.execute('INSERT INTO deliveries(key,fingerprint,payload,state) VALUES (?,?,?,?)',
                                      ('delivery-'+status,'synthetic-fingerprint','DO_NOT_PRINT_PRIVATE_BODY',status))
                bridge.db.execute('INSERT INTO image_uploads(key,state) VALUES (?,?)',('image-only-unknown','outcome_unknown'))
                bridge.db.commit()
                for seq,status in enumerate(('completed','failed','blocked','interrupted','cancelled','queued','running','waiting_media'),1):
                    gateway.db.execute('INSERT INTO jobs(id,seq,command,model,state) VALUES (?,?,?,?,?)',
                                       ('job-'+status,seq,'DO_NOT_PRINT_PRIVATE_BODY','DO_NOT_PRINT_PRIVATE_BODY',status))
                for key,status in (('out-pending','pending'),('delivery-submitted','submitted'),('out-failed','failed'),('out-confirmed','confirmed')):
                    gateway.db.execute('INSERT INTO outbox(key,job_id,payload,state) VALUES (?,?,?,?)',
                                       (key,'job-completed','DO_NOT_PRINT_PRIVATE_BODY',status))
                gateway.db.commit()
                self.dbpaths.extend([bridge.local/'bridge.sqlite3',gateway.local/'tasks.sqlite3',self.root/'local/consumers'/('agent-'+gateway.key)/'inbox.sqlite3'])
            finally:gateway.close();bridge.close()
        code={'core.py':hashlib.sha256((self.root/'dingtalk_bridge/core.py').read_bytes()).hexdigest()}
        (self.root/self.validation).write_text(json.dumps({'ok':True,'evidence':'synthetic-validation','codeSha256':code,'wheelSha256':'synthetic-wheel'}))
        receipt=self.root/'local/recovery-checks/dab-auth-read-20261112';receipt.mkdir(parents=True)
        (receipt/'receipt.json').write_text('{"state":"failed","attempted":true,"automaticRetry":false}')

    def create(self):return planner.create_plan(self.root,self.config,self.agents,self.validation)

    def files(self):
        return {str(p.relative_to(self.root)):(p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}

    def test_two_routes_keep_all_states_and_original_keys_without_side_effects(self):
        before=self.files()
        with patch('subprocess.Popen',side_effect=AssertionError('no processes')),patch('socket.socket',side_effect=AssertionError('no network')),patch.object(Bridge,'__init__',side_effect=AssertionError('no worker')):
            result=self.create()
        self.assertEqual(before,self.files())
        self.assertEqual(result['summary']['routeCount'],2)
        self.assertEqual(result['summary']['unfinishedJobs'],6)
        self.assertEqual(result['summary']['unconfirmedOriginalKeys'],14)
        self.assertEqual(result['summary']['historicalNonSuccessJobs'],8)
        self.assertTrue(result['versions']['matchesValidated']);self.assertFalse(result['executable'])
        self.assertNotIn('DO_NOT_PRINT_PRIVATE_BODY',json.dumps(result))
        self.assertNotIn('synthetic-account-secret',json.dumps(result['summary']))
        for route in result['routes']:
            self.assertIn('delivery-outcome_unknown',route['review']['unconfirmedOriginalKeys'])
            self.assertIn('image-only-unknown',route['review']['unconfirmedOriginalKeys'])
            self.assertIn('job-interrupted',route['review']['historicalNonSuccessJobIds'])
            self.assertEqual(route['bridge']['deliveries']['states']['confirmed'],1)
            self.assertEqual(route['bridge']['deliveries']['states']['failed'],1)
            self.assertEqual(route['tasks']['outbox']['states']['failed'],1)
            self.assertEqual(route['configurationChange']['receiveMode'],{'before':'stream_hint','after':'history'})

    def test_owner_lock_and_sidecar_refuse_without_cleanup(self):
        lock=self.root/'local/runtime/manager.lock'
        with lock.open('rb') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'owner_lock_busy'):self.create()
        for suffix in planner.SIDECARS:
            side=Path(str(self.dbpaths[0])+suffix);side.write_bytes(b'synthetic pending state');before=self.files()
            with self.assertRaisesRegex(ValueError,'sidecar'):self.create()
            self.assertEqual(before,self.files());side.unlink()

    def test_binding_mismatch_and_missing_database_never_create_or_repair(self):
        dbpath=self.dbpaths[1]
        with closing(sqlite3.connect(dbpath)) as db, db:db.execute('UPDATE meta SET value=? WHERE key="binding"',('wrong',))
        before=self.files()
        with self.assertRaisesRegex(ValueError,'gateway_binding_mismatch'):self.create()
        self.assertEqual(before,self.files())
        dbpath.unlink();before=self.files()
        with self.assertRaisesRegex(ValueError,'required_input_missing'):self.create()
        self.assertEqual(before,self.files())

    def test_snapshot_changes_during_or_after_review_are_rejected(self):
        result=self.create();planner.check_snapshot(self.root,result)
        with closing(sqlite3.connect(self.dbpaths[0])) as db, db:db.execute('UPDATE deliveries SET state="confirmed" WHERE key="delivery-submitted"')
        with self.assertRaises(ValueError):planner.check_snapshot(self.root,result)
        with self.assertRaises(ValueError):planner.publish(self.root,'stale',result)
        self.assertFalse((self.root/'local/deployment-reviews/stale').exists())
        original=planner.inventory;changed=False
        def mutate(db,*args,**kwargs):
            nonlocal changed
            output=original(db,*args,**kwargs)
            if not changed:
                changed=True
                p=self.root/self.config;p.write_bytes(p.read_bytes()+b'\n')
            return output
        with patch.object(planner,'inventory',side_effect=mutate),self.assertRaisesRegex(ValueError,'snapshot_changed'):
            self.create()

    def test_publish_is_private_write_once_and_cannot_follow_symlinks(self):
        plan=self.create();before=self.files();target=planner.publish(self.root,'review',plan)
        self.assertEqual(target.stat().st_mode&0o777,0o600)
        self.assertEqual(target.parent.stat().st_mode&0o777,0o700)
        for name,data in before.items():self.assertEqual(data,self.files()[name])
        saved=target.read_bytes()
        with self.assertRaises(FileExistsError):planner.publish(self.root,'review',plan)
        self.assertEqual(target.read_bytes(),saved)
        victim=self.root/'untouched';victim.write_text('unchanged')
        (target.parent.parent/'link').symlink_to(victim)
        with self.assertRaisesRegex(ValueError,'symlink'):planner.publish(self.root,'link',plan)
        self.assertEqual(victim.read_text(),'unchanged')
        config=self.root/self.config;data=config.read_bytes();config.unlink();victim.write_bytes(data);config.symlink_to(victim)
        with self.assertRaisesRegex(ValueError,'symlink'):self.create()

    def test_version_mismatch_is_reported_without_permission_or_source_mutation(self):
        (self.root/'dingtalk_bridge/core.py').write_text('# different\n');before=self.files()
        plan=self.create();self.assertFalse(plan['versions']['matchesValidated'])
        self.assertFalse(plan['summary']['newDwsCallsAllowed']);self.assertFalse(plan['summary']['backgroundStartAllowed'])
        self.assertEqual(plan['summary']['priorSingleReadState'],'failed');self.assertEqual(before,self.files())

    def test_cli_prepare_check_and_stale_check_emit_only_safe_summary(self):
        command=[sys.executable,str(ROOT/'scripts/prepare_history_deployment.py'),'--root',str(self.root),'--key','cli',
                 '--validation',self.validation]
        for name in self.agents:command+=['--agent-config',name]
        p=subprocess.run(command,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr);value=json.loads(p.stdout)
        self.assertFalse(value['backgroundStartAllowed']);self.assertNotIn('synthetic-account-secret',p.stdout+p.stderr)
        self.assertNotIn('DO_NOT_PRINT_PRIVATE_BODY',p.stdout+p.stderr)
        p=subprocess.run(command+['--check'],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0);self.assertTrue(json.loads(p.stdout)['snapshotUnchanged'])
        saved=(self.root/'local/deployment-reviews/cli/plan.json').read_bytes()
        (self.root/self.config).write_text('changed-private-value')
        p=subprocess.run(command+['--check'],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,1);self.assertNotIn('changed-private-value',p.stdout+p.stderr)
        self.assertEqual((self.root/'local/deployment-reviews/cli/plan.json').read_bytes(),saved)


if __name__=='__main__':unittest.main()

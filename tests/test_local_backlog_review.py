from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_history_deployment_plan as fixtures
from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.consumer import Inbox
from dingtalk_bridge.core import Bridge
from dingtalk_bridge.message_model import normalize
from dingtalk_bridge.routing import route_configs

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('backlog_review',ROOT/'scripts/review_local_backlog.py')
reviewer=importlib.util.module_from_spec(spec);spec.loader.exec_module(reviewer)


class LocalBacklogReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.HistoryDeploymentPlanTests('runTest')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root.resolve()
        self.routes=list(route_configs(json.loads((self.root/self.fixture.config).read_text())))
        self.events=[]
        for index,(route,_) in enumerate(self.routes):
            messages=[]
            texts=['ordinary DO_NOT_EXPORT_BODY','/agent work DO_NOT_EXPORT_BODY','/agent status',
                   '/agent cancel','/agent new','[Agent] /agent echo','/agent stranger',
                   '/agent unknown','[文件] input.txt fileId: synthetic-file',
                   '/agent --files ["input.txt"] synthetic task','malformed','/agent old failed task']
            for seq,text in enumerate(texts,1):
                sender='stranger' if seq==7 else None if seq==8 else 'synthetic-user'
                raw={'conversationId':route['group'],'messageId':'synthetic-message-'+str(seq),
                     'senderId':sender,'createTime':'2026-11-12 13:00:00','text':text}
                if seq==9:raw['resourceRefs']=[{'type':'fileId','resourceId':'synthetic-file'}]
                messages.append({'seq':seq,'message_id':raw['messageId'],'account_id':route['accountId'],
                    'conversation_id':route['group'],'from_self':False if sender else None,'raw':raw})
            self.events.append(messages)
            bridge,tasks,inbox=self.fixture.dbpaths[index*3:index*3+3]
            with closing(sqlite3.connect(bridge)) as db,db:
                db.execute('DELETE FROM events')
                for e in messages:db.execute('INSERT INTO events(seq,message_id,body) VALUES(?,?,?)',
                    (e['seq'],e['message_id'],json.dumps(e) if e['seq']!=11 else 'PRIVATE_BROKEN_JSON'))
            scope=json.dumps([route['accountId'],route['profile'],route['group'],route['conversationType']])
            key=hashlib.sha256(scope.encode()).hexdigest()[:24]
            job_id=hashlib.sha256((key+'\0'+messages[-1]['message_id']).encode()).hexdigest()[:24]
            with closing(sqlite3.connect(tasks)) as db,db:
                db.execute('DELETE FROM jobs')
                db.execute('INSERT INTO jobs(id,seq,command,model,state,error) VALUES(?,?,?,?,?,?)',
                    (job_id,12,'DO_NOT_EXPORT_OLD_COMMAND','DO_NOT_EXPORT_OLD_MODEL','failed','original failure'))
            with closing(sqlite3.connect(inbox)) as db,db:
                db.execute('DELETE FROM inbox')
                db.execute('INSERT OR REPLACE INTO meta VALUES("cursor","5")')
                for e in messages[:5]:db.execute('INSERT INTO inbox(seq,message_id,raw,model,state) VALUES(?,?,?,?,?)',
                    (e['seq'],e['message_id'],json.dumps(e),json.dumps(normalize(e,route)),'normalized'))

    def plan(self):
        value=self.fixture.create()
        folder=self.root/'local/review';folder.mkdir(exist_ok=True)
        path=folder/'deployment.json';path.write_text(json.dumps(value))
        return path

    def test_both_routes_preview_existing_and_unconsumed_events_without_execution(self):
        plan=self.plan();before=self.fixture.files()
        with patch('subprocess.Popen',side_effect=AssertionError('no process')), \
             patch('socket.socket',side_effect=AssertionError('no network')), \
             patch.object(Bridge,'__init__',side_effect=AssertionError('no bridge')), \
             patch.object(Gateway,'__init__',side_effect=AssertionError('no gateway')), \
             patch.object(Inbox,'__init__',side_effect=AssertionError('no inbox')):
            value=reviewer.preview(self.root,plan)
        self.assertEqual(before,self.fixture.files())
        self.assertEqual(value['summary']['unconsumedLocalEvents'],14)
        self.assertEqual(value['summary']['remoteUnsyncedMessages'],'unknown')
        self.assertFalse(value['summary']['executionAllowed'])
        self.assertNotIn('DO_NOT_EXPORT',json.dumps(value));self.assertNotIn('PRIVATE_BROKEN_JSON',json.dumps(value))
        group,direct=value['routes']
        g={e['seq']:e for e in group['entries']};d={e['seq']:e for e in direct['entries']}
        self.assertEqual(g[1]['classification'],'ignored_by_task_policy')
        self.assertEqual(d[1]['classification'],'text_task_review')
        for records in (g,d):
            for seq in (3,4,5):self.assertEqual(records[seq]['classification'],'control_review')
            for seq in (7,8):self.assertEqual(records[seq]['classification'],'ignored_by_task_policy')
            self.assertEqual(records[11]['classification'],'quarantined')
            self.assertEqual(records[12]['classification'],'existing_job')
            self.assertEqual(records[12]['priorJobState'],'failed')
            self.assertEqual(records[2]['origin'],'stored_inbox')
            self.assertEqual(records[9]['origin'],'unconsumed_transport')
        self.assertEqual(g[6]['classification'],'ignored_by_task_policy')
        self.assertEqual(d[6]['classification'],'text_task_review')
        self.assertEqual(g[9]['classification'],'ignored_by_task_policy')
        self.assertEqual(g[10]['classification'],'file_selection_review')
        self.assertEqual(d[9]['classification'],'media_task_review')
        self.assertEqual(group['candidateTasksOrNotices'],5)
        self.assertEqual(direct['candidateTasksOrNotices'],8)

    def test_stale_review_and_sidecars_refuse_without_mutation(self):
        plan=self.plan()
        side=Path(str(self.fixture.dbpaths[0])+'-wal');side.write_bytes(b'preserve synthetic journal')
        before=self.fixture.files()
        with self.assertRaises(ValueError):reviewer.preview(self.root,plan)
        self.assertEqual(before,self.fixture.files());side.unlink()
        (self.root/self.fixture.agents[0]).write_text('{"changed":"PRIVATE"}')
        with self.assertRaises(ValueError):reviewer.preview(self.root,plan)

    def test_cursor_ahead_of_local_events_is_explicit_not_corrected(self):
        with closing(sqlite3.connect(self.fixture.dbpaths[2])) as db,db:
            db.execute('UPDATE meta SET value="99" WHERE key="cursor"')
        plan=self.plan();before=self.fixture.files();value=reviewer.preview(self.root,plan)
        self.assertTrue(value['routes'][0]['cursorExceedsLocalMax'])
        self.assertEqual(value['routes'][0]['unconsumedLocalEvents'],0)
        self.assertEqual(value['routes'][0]['consumerCursor'],99)
        self.assertEqual(before,self.fixture.files())
        self.assertEqual(value['summary']['remoteUnsyncedMessages'],'unknown')

    def test_inconsistent_inbox_cursor_and_message_identity_fail_closed(self):
        inbox=self.fixture.dbpaths[2]
        for mutation,reason in (('UPDATE meta SET value="4" WHERE key="cursor"','inbox_ahead_of_cursor'),
                         ('UPDATE inbox SET message_id="mismatched" WHERE seq=1','saved_model_identity_mismatch')):
            with closing(sqlite3.connect(inbox)) as db,db:
                db.execute('UPDATE meta SET value="5" WHERE key="cursor"');db.execute(mutation)
            plan=self.plan();before=self.fixture.files()
            with self.assertRaisesRegex(ValueError,reason):reviewer.preview(self.root,plan)
            self.assertEqual(before,self.fixture.files())

    def test_private_write_once_cli_outputs_counts_not_raw_text(self):
        plan=self.plan();before=self.fixture.files()
        command=[sys.executable,str(ROOT/'scripts/review_local_backlog.py'),'--root',str(self.root),
                 '--deployment-review',str(plan),'--key','synthetic']
        result=subprocess.run(command,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        safe=json.loads(result.stdout)
        self.assertEqual(safe['unconsumedLocalEvents'],14);self.assertEqual(safe['candidateTasksOrNotices'],13)
        for private in ('synthetic-user','synthetic-message','DO_NOT_EXPORT','PRIVATE'):
            self.assertNotIn(private,result.stdout+result.stderr)
        path=self.root/'local/backlog-reviews/synthetic/preview.json';saved=path.read_bytes()
        self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(path.parent.stat().st_mode&0o777,0o700)
        for name,data in before.items():self.assertEqual(data,self.fixture.files()[name])
        result=subprocess.run(command,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2);self.assertEqual(path.read_bytes(),saved)

    def test_saved_model_cross_scope_is_not_classified_under_another_route(self):
        inbox=self.fixture.dbpaths[2]
        with closing(sqlite3.connect(inbox)) as db,db:
            model=json.loads(db.execute('SELECT model FROM inbox WHERE seq=1').fetchone()[0])
            model['conversationId']='foreign-conversation'
            db.execute('UPDATE inbox SET model=? WHERE seq=1',(json.dumps(model),))
        plan=self.plan();before=self.fixture.files()
        with self.assertRaisesRegex(ValueError,'saved_model_scope_mismatch'):
            reviewer.preview(self.root,plan)
        self.assertEqual(before,self.fixture.files())


if __name__=='__main__':unittest.main()

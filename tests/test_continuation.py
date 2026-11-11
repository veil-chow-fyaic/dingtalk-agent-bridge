import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from dingtalk_bridge.configure import migrate,select,write_config
from dingtalk_bridge.core import Bridge,BridgeError
from dingtalk_bridge.discovery import discover
from dingtalk_bridge.routing import Hub,route_configs
from dingtalk_bridge.consumer import Inbox
from test_core import CFG,Fake
from test_routing_consumer import event,ref


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def test_migration_keeps_media_fingerprint_cursor_and_unknown_send(self):
        fake=Fake();b=Bridge(self.root,CFG,fake)
        self.root.joinpath('fixtures').mkdir();self.root.joinpath('fixtures/a.txt').write_text('bytes')
        b.sync();b.send('file-key',file='fixtures/a.txt');fake.fail=True;b.send('unknown',text='unknown')
        before=[tuple(r) for r in b.db.execute('SELECT * FROM deliveries ORDER BY key')];events=b.events();b.close()
        migrated=migrate(CFG);self.assertEqual(migrate(migrated),migrated)
        h=Hub(self.root,migrated,lambda root,c,state_name:Bridge(root,c,fake,state_name))
        try:
            b=h.select();self.assertEqual(b.events(),events)
            self.assertEqual([tuple(r) for r in b.db.execute('SELECT * FROM deliveries ORDER BY key')],before)
            self.assertTrue(b.send('file-key',file='fixtures/a.txt')['replayed'])
            self.assertEqual(b.send('unknown',text='unknown')['state'],'outcome_unknown')
            self.assertEqual(fake.sent,2)
            self.assertFalse(self.root.joinpath('local/runtime/routes').exists())
        finally:h.close()

    def test_config_output_exclusive_and_private(self):
        p=self.root/'config.json';write_config(p,migrate(CFG))
        before=p.read_bytes()
        with self.assertRaises(FileExistsError):write_config(p,{})
        self.assertEqual(p.read_bytes(),before);self.assertEqual(p.stat().st_mode&0o777,0o600)

    def test_routes_distinguish_alias_from_auth_identity(self):
        # An alias equal to another profile is legal, provided neither actual identity is duplicated.
        routes=[{'accountId':a,'profile':p,'conversationId':'g','conversationType':'group','binary':'dws'}
                for a,p in [('a','b'),('b','c')]]
        self.assertEqual(len(list(route_configs({'routes':routes}))),2)
        routes[1]['profile']='b'
        with self.assertRaises(ValueError):list(route_configs({'routes':routes}))
        legacy=migrate(CFG);second=copy.deepcopy(legacy['routes'][0]);second['conversationId']='other'
        with self.assertRaises(ValueError):list(route_configs({'routes':legacy['routes']+[second]}))

    def test_discovery_pagination_and_no_unverified_peer_inference(self):
        calls=[]
        response={'chats':[{'openConversationId':'dm','conversationType':'direct','name':'same','ownerOpenDingtalkId':'not-a-peer'},
                           {'openConversationId':'g','conversationType':'group','name':'same'}],
                  'complete':True,'paginationKnown':False,'hasMore':True,'nextCursor':12}
        class D:
            def call(self,args):calls.append(args);return response
        d=D();result=discover(d,'a',cursor=4,limit=2,configured={'g'})
        self.assertFalse(result['complete']);self.assertFalse(result['routes_changed'])
        self.assertTrue(result['conversations'][0]['requires_peer_id'])
        self.assertNotIn('ownerOpenDingtalkId',json.dumps(result))
        self.assertEqual(result['next_cursor'],12);self.assertEqual(calls[0][-4:],['--page-token','4','--page-size','2'])
        response['paginationKnown']=True;response['complete']=False
        self.assertFalse(discover(d,'a')['complete'])

    def test_select_verifies_exact_id_before_preparing_config(self):
        calls=[]
        class D:
            def __init__(self,*args):pass
            def call(self,args):calls.append(args);return {'result':{'conversationInfo':{'openConversationId':'new','name':'test'}}}
        with self.assertRaises(ValueError):select(CFG,'default','new','direct',dws_factory=D)
        self.assertEqual(calls,[])
        with self.assertRaises(BridgeError):select(CFG,'default','wrong','group',dws_factory=D)
        c=select(CFG,'default','new','direct','peer',dws_factory=D)
        self.assertEqual(c['routes'][1]['peerOpenDingTalkId'],'peer')
        self.assertNotIn('stateStorage',c['routes'][1]);self.assertEqual(calls[-1][-2:],['--open-dingtalk-id','peer'])
        self.assertNotIn('routes',CFG)

    def test_self_media_never_starves_other_sender(self):
        i=Inbox(self.root,CFG)
        try:
            events=[event(n,text='[文件] x fileId: f',sender='self',refs=[ref('fileId','f')]) for n in range(1,26)]
            events.append(event(26,text='[文件] x fileId: f',sender='other',refs=[ref('fileId','f')]))
            i.ingest({'events':events,'next_cursor':26});calls=[]
            def download(mid):calls.append(mid);raise OSError('simulate pending resource')
            self.assertEqual(i.hydrate(download,limit=1)['failed'],1)
            self.assertEqual(calls,['m26']);self.assertEqual(i.cursor,26)
        finally:i.close()

    def test_wait_wakes_only_after_commit_and_cursor_resumes(self):
        fake=Fake();b=Bridge(self.root,CFG,fake);results=[]
        try:
            t=threading.Thread(target=lambda:results.append(b.events(wait_seconds=2)))
            t.start();time.sleep(.03);b.sync();t.join(1)
            self.assertFalse(t.is_alive());self.assertEqual(len(results[0]),2)
            cursor=results[0][-1]['seq'];self.assertEqual(b.events(cursor,wait_seconds=.01),[])
            fake.messages.append({'messageId':'new','conversationId':'g','text':'new','senderId':'other'})
            b.sync();self.assertEqual([e['message_id'] for e in b.events(cursor)],['new'])
            with self.assertRaises(ValueError):b.events(wait_seconds=float('nan'))
        finally:b.stop_waiters();b.close()

    def test_missing_history_does_not_mark_scan_complete(self):
        class D:
            def call(self,args):return {'complete':True}
        b=Bridge(self.root,CFG,D())
        try:
            with self.assertRaises(BridgeError):b.sync()
            self.assertIsNone(b.health()['last_sync'])
        finally:b.close()

    def test_direct_route_consumer_model_remains_direct(self):
        config={**CFG,'accountId':'a','conversationType':'direct','peerOpenDingTalkId':'peer'}
        i=Inbox(self.root,config)
        try:
            i.ingest({'events':[event()],'next_cursor':1})
            self.assertEqual(i.ready()[0]['message']['conversationType'],'direct')
        finally:i.close()

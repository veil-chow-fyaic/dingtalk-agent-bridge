import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from dingtalk_bridge.core import Bridge
from dingtalk_bridge.routing import Hub
from dingtalk_bridge.consumer import Inbox
from dingtalk_bridge.message_model import normalize,materialize,media_parts

CFG={'profile':'org:person','accountId':'a','group':'g','name':'test','selfSenderId':'self','binary':'dws'}
def ref(kind,rid):return {'type':kind,'resourceId':rid}
def event(seq=1,text='hello',sender='other',refs=None,quote=None):
    raw={'conversationId':'g','messageId':'m'+str(seq),'senderId':sender,'createTime':'2026-11-11 12:00:00','text':text}
    if refs:raw['resourceRefs']=refs
    if quote:raw['quotedMessage']=quote
    return {'seq':seq,'message_id':raw['messageId'],'conversation_id':'g','from_self':sender=='self' if sender else None,'source':'dws_history','raw':raw}
class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_inline_order_and_quoted_resource_not_duplicated(self):
        e=event(text='before[图片消息](mediaId=imgA)middle[图片消息](mediaId=imgB)after',refs=[ref('mediaId','imgA'),ref('mediaId','imgB')])
        m=normalize(e,CFG)
        self.assertEqual([p['type'] for p in m['parts']],['text','image','text','image','text'])
        self.assertEqual(m['issues'],[])
        q={'conversationId':'g','messageId':'q','text':'[文件] x.xlsx fileId: f','resourceRefs':[ref('fileId','f')]}
        m=normalize(event(text='reply',refs=[ref('fileId','f')],quote=q),CFG)
        self.assertEqual(m['parts'],[{'type':'text','text':'reply'}]);self.assertEqual(len(list(media_parts(m))),1)
        self.assertEqual(m['quote']['parts'][0]['name'],'x.xlsx');self.assertEqual(m['issues'],[])
    def test_unknown_media_and_cross_scope_quote_fail_closed(self):
        m=normalize(event(refs=[ref('fileId','f')]),CFG)
        self.assertIn('unpositioned_resources',m['issues'])
        with self.assertRaises(ValueError):normalize(event(quote={'conversationId':'other','text':'secret'}),CFG)
    def test_native_image_alias_requires_identical_downloaded_bytes(self):
        refs=[ref('mediaId','positioned'),{**ref('mediaId','native'),'contentType':'image'}]
        original=normalize(event(text='[图片消息](mediaId=positioned)',refs=refs),CFG)
        self.assertEqual(original['issues'],[])
        self.assertEqual(len(list(media_parts(original))),1)
        folder=self.root/'local/runtime/downloads/alias';folder.mkdir(parents=True)
        records=[]
        for rid in ('positioned','native'):
            p=folder/(rid+'.png');p.write_bytes(b'identical')
            records.append({'resourceType':'mediaId','resourceId':rid,'localPath':str(p.relative_to(self.root)),
                            'sizeBytes':9,'sha256':hashlib.sha256(b'identical').hexdigest()})
        ledger={'ok':True,'downloads':records}
        ready=materialize(copy.deepcopy(original),ledger,self.root)
        self.assertTrue(ready['imageAliasCandidates'][0]['verified'])
        self.assertEqual(ready['imageAliasCandidates'][0]['aliasOf'],ref('mediaId','positioned'))
        with self.assertRaisesRegex(ValueError,'missing_downloaded_resource'):
            materialize(copy.deepcopy(original),{'ok':True,'downloads':records[:1]},self.root)
        (folder/'native.png').write_bytes(b'different')
        records[1]['sha256']=hashlib.sha256(b'different').hexdigest()
        rejected=copy.deepcopy(original)
        with self.assertRaisesRegex(ValueError,'unpositioned_image_not_alias'):
            materialize(rejected,ledger,self.root)
        self.assertNotIn('path',rejected['parts'][0])
    def test_inbox_transaction_rollback_and_restart(self):
        i=Inbox(self.root,CFG)
        with self.assertRaises(ValueError):i.ingest({'events':[event()], 'next_cursor':99})
        self.assertEqual(i.cursor,0);self.assertEqual(i.summary()['messages'],0)
        i.ingest({'events':[event(2),event(4,sender='self'),event(7,sender=None)],'next_cursor':7})
        i.close();i=Inbox(self.root,CFG)
        try:
            self.assertEqual(i.cursor,7);self.assertEqual(len(i.ready()),1)
            self.assertEqual(i.summary()['selfFiltered'],1);self.assertEqual(i.summary()['unknownSender'],1)
            i.ingest({'events':[],'next_cursor':7});self.assertEqual(i.summary()['messages'],3)
        finally:i.close()
    def test_invalid_batch_never_advances(self):
        i=Inbox(self.root,CFG);wrong=event(2);wrong['conversation_id']='other'
        try:
            with self.assertRaises(ValueError):i.ingest({'events':[event(),wrong],'next_cursor':2})
            self.assertEqual(i.cursor,0);self.assertEqual(i.summary()['messages'],0)
        finally:i.close()
    def test_media_failure_recovery_does_not_lose_cursor(self):
        i=Inbox(self.root,CFG);i.ingest({'events':[event(text='[图片消息](mediaId=i)',refs=[ref('mediaId','i')])],'next_cursor':1})
        path=self.root/'local/runtime/downloads/test/image.png';path.parent.mkdir(parents=True);path.write_bytes(b'original')
        ledger={'ok':True,'downloads':[{'resourceType':'mediaId','resourceId':'i','localPath':str(path.relative_to(self.root)),'sizeBytes':8,'sha256':hashlib.sha256(b'original').hexdigest()}]}
        try:
            self.assertEqual(i.hydrate(lambda _: {'ok':True,'downloads':[]})['failed'],1)
            self.assertEqual(i.cursor,1);self.assertEqual(i.ready(),[])
            self.assertEqual(i.hydrate(lambda _:ledger)['completed'],1)
            self.assertEqual(len(i.ready()),1)
            m=normalize(event(text='[图片消息](mediaId=i)',refs=[ref('mediaId','i')]),CFG)
            path.write_bytes(b'changed')
            self.assertEqual(i.ready(),[])
            with self.assertRaises(ValueError):materialize(m,ledger,self.root)
        finally:i.close()
    def test_consumer_scope_and_owner(self):
        i=Inbox(self.root,CFG)
        with self.assertRaises(ValueError):Inbox(self.root,CFG)
        i.close()
        with self.assertRaises(ValueError):Inbox(self.root,{**CFG,'profile':'different'})
    def test_multiroute_identity_and_idempotency_isolation(self):
        routes=[{'accountId':a,'profile':a+':user','conversationId':g,'conversationType':t,'name':'same name','peerOpenDingTalkId':'peer','binary':'dws'} for a,g,t in [('one','g','group'),('two','g','group'),('one','dm','direct')]]
        calls=[]
        class DWS:
            def __init__(self,c):self.c=c
            def call(self,args):
                calls.append((self.c['accountId'],args))
                if '+messages-send' in args:return {'sendReceipt':{'openTaskId':'task'}}
                return {'result':{'sendStatus':'SUCCESS'},'messageRef':{'openConversationId':self.c['group'],'openMessageId':'m'}}
        h=Hub(self.root,{'routes':routes},factory=lambda root,c,state_name:Bridge(root,c,DWS(c),state_name))
        try:
            with self.assertRaises(ValueError):h.select()
            with self.assertRaises(ValueError):h.select('missing','g')
            for a,g in [('one','g'),('two','g'),('one','dm')]:
                self.assertEqual(h.select(a,g).send('same-key',text='same')['state'],'confirmed')
                self.assertTrue(h.select(a,g).send('same-key',text='same')['replayed'])
            sent=[args for _,args in calls if '+messages-send' in args]
            self.assertEqual(len(sent),3);self.assertIn('--open-dingtalk-id',sent[-1]);self.assertNotIn('--group',sent[-1])
            self.assertEqual(h.select('one','g').events(),[])
        finally:h.close()
    def test_late_index_recovered_by_deep_scan(self):
        calls=[];late=False
        def call(args):
            calls.append(args);start=datetime.fromisoformat(args[args.index('--start')+1])
            found=late and start<datetime.now(timezone.utc)-timedelta(hours=2)
            return {'messages':[{'messageId':'late','conversationId':'g','senderId':'self','text':'late'}] if found else [],'complete':True}
        d=type('DWS',(),{})();d.call=call;b=Bridge(self.root,CFG,d)
        try:
            self.assertTrue(b.sync()['deep']);late=True
            self.assertEqual(b.sync()['inserted'],0)
            self.assertEqual(b.sync(deep=True)['inserted'],1)
            self.assertEqual(b.sync(deep=True)['inserted'],0)
        finally:b.close()

class DownloadRecoveryTests(unittest.TestCase):
    def test_partial_download_retry_uses_new_directory_and_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);calls=[]
            class DWS:
                def call(self,args):
                    if '+chat-messages' in args:return {'complete':True,'messages':[event(text='[文件] x.txt fileId: f',refs=[ref('fileId','f')])['raw']]}
                    folder=args[args.index('--output-dir')+1];calls.append(folder)
                    p=root/folder/'x.txt';p.parent.mkdir(parents=True);p.write_bytes(b'bytes')
                    return {'messages':[{'messageId':'m1','conversationId':'g'}],
                        'resourceDownloads':{'ok':len(calls)>1,'partial':len(calls)==1,'failedCount':1 if len(calls)==1 else 0,
                        'downloads':[{'resourceType':'fileId','resourceId':'f','messageId':'m1','localPath':str(p.relative_to(root)),'sizeBytes':5}]}}
            b=Bridge(root,CFG,DWS())
            try:
                b.sync();self.assertFalse(b.download('m1')['ok'])
                self.assertTrue(b.download('m1')['ok']);self.assertNotEqual(calls[0],calls[1])
                cached=b.download('m1');self.assertEqual(len(calls),2)
                (root/cached['downloads'][0]['localPath']).write_bytes(b'corrupt')
                from dingtalk_bridge.core import BridgeError
                with self.assertRaises(BridgeError):b.download('m1')
                self.assertTrue(b.download('m1',repair=True)['ok']);self.assertEqual(len(calls),3)
            finally:b.close()

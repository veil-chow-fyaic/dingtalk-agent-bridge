import hashlib
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from dingtalk_bridge.core import Bridge, BridgeError
from dingtalk_bridge.host_channel import ChannelError, HostChannel
from test_core import Fake
from test_routing_consumer import CFG, event, ref


class FilesDWS(Fake):
    def __init__(self, root):
        super().__init__()
        self.messages = []
        self.root = root
        self.downloaded = []

    def call(self, args):
        if '+messages-mget' not in args:
            return super().call(args)
        mid = args[args.index('--msg-ids') + 1]
        raw = next(record for record in self.messages if record['messageId'] == mid)
        self.downloaded.append(mid)
        content = ('原件:' + mid).encode()
        downloads = []
        for index, resource in enumerate(raw['resourceRefs']):
            path = Path(args[args.index('--output-dir') + 1]) / f'original-{index}'
            (self.root / path).parent.mkdir(parents=True,exist_ok=True)
            blob = content if len(raw['resourceRefs']) == 1 else content + bytes([index])
            (self.root / path).write_bytes(blob)
            downloads.append({'resourceType':resource['type'],'resourceId':resource['resourceId'],
                              'localPath':str(path),'sizeBytes':len(blob)})
        ledger = {'ok': True, 'downloads': downloads}
        return {'messages': [raw], 'resourceDownloads': ledger}


def file(seq, name='source.txt', sender='other', at=None):
    rid = 'resource-' + str(seq)
    raw = event(seq, f'[文件] {name} fileId: {rid}', sender=sender, refs=[ref('fileId',rid)])['raw']
    if at:
        raw['createTime'] = at
    return raw


def command(seq, names='["source.txt"]', task='inspect'):
    return event(seq, f'/agent --files {names} {task}')['raw']


class GroupFileSelectionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.route = {**CFG, 'executionOwner':'openclaw'}
        self.dws = FilesDWS(self.root)
        self.state = 'a' * 64
        self.transport = Bridge(self.root, self.route, self.dws, self.state)
        self.addCleanup(self.transport.close)

    def api(self, path, data=None):
        if path == '/v1/attachments':
            return self.transport.download(data['message_id'])
        query = parse_qs(urlsplit(path).query)
        after = int(query['after'][0])
        items = self.transport.events(after, int(query['limit'][0]))
        return {'events': items, 'account_id': self.route['accountId'], 'conversation_id': self.route['group'],
                'next_cursor': items[-1]['seq'] if items else after}

    def admit(self, prior, request, following=()):
        self.dws.messages = list(prior)
        self.transport.sync()
        cursor = self.transport.events(limit=200)[-1]['seq'] if prior else 0
        self.channel = HostChannel(self.root, self.route, self.state, cursor, self.api)
        self.addCleanup(self.channel.close)
        self.dws.messages.extend([request, *following])
        self.transport.sync()
        self.assertEqual(self.channel.poll()['message']['id'], request['messageId'])
        return {'messageId':request['messageId']}

    def test_source_predates_initial_cursor_and_only_selected_originals_are_read_in_request_order(self):
        files = [file(1), file(2,'图 表.csv'), file(3,sender='stranger'), file(4,sender='self')]
        msg = self.admit(files, command(5,'["图 表.csv", "source.txt"]'))
        self.assertEqual(self.channel.handle({'op':'selectFiles', **msg}), {'count':2, 'task':'inspect'})
        for index, expected in enumerate(('m2','m1')):
            part = self.channel.handle({'op':'selectedFile', **msg, 'index':index})['part']
            content = ('原件:' + expected).encode()
            self.assertEqual(part['sha256'], hashlib.sha256(content).hexdigest())
            self.assertEqual(Path(part['path']).read_bytes(), content)
        self.assertEqual(self.dws.downloaded, ['m2','m1'])
        self.assertEqual(self.channel.db.execute('SELECT count(*) FROM inbox').fetchone()[0], 1)
        self.channel.ack(msg['messageId'], 'done')
        with self.assertRaisesRegex(ChannelError, 'requires_claim'):
            self.channel.handle({'op':'selectedFile', **msg, 'index':0})
        self.assertIsNone(self.channel.poll()['message'])

    def test_changed_cache_is_rejected_without_refetch_or_partial_output(self):
        msg = self.admit([file(1)], command(2))
        self.channel.handle({'op':'selectFiles', **msg})
        op = {'op':'selectedFile', **msg, 'index':0}
        part = self.channel.handle(op)['part']
        Path(part['path']).write_bytes(b'changed')
        with self.assertRaises(BridgeError):
            self.channel.handle(op)
        self.assertEqual(self.dws.downloaded, ['m1'])

    def test_expired_future_other_senders_and_later_file_do_not_match(self):
        msg = self.admit([file(1,at='2026-11-11 11:29:59'), file(2,sender='stranger'),
                          file(3,at='2026-11-11 12:00:01')], command(4), [file(5)])
        result = self.channel.handle({'op':'selectFiles', **msg})
        self.assertEqual(result, {'error':'file_selection_missing_or_ambiguous'})

    def test_ambiguous_names_are_refused_without_guessing(self):
        msg = self.admit([file(1),file(2)],command(3))
        self.assertEqual(self.channel.handle({'op':'selectFiles', **msg})['error'],
                         'file_selection_missing_or_ambiguous')
        self.assertEqual(self.dws.downloaded, [])

    def test_window_counts_all_actual_events(self):
        messages = [file(1)] + [event(seq)['raw'] for seq in range(2, 52)]
        msg = self.admit(messages, command(52))
        self.assertEqual(self.channel.handle({'op':'selectFiles', **msg})['error'],
                         'file_selection_missing_or_ambiguous')
        self.assertEqual(self.dws.downloaded, [])

    def test_conversation_anchor_and_scope_are_checked(self):
        msg = self.admit([file(1)], command(2))
        with self.transport.db:
            self.transport.db.execute("UPDATE events SET body=json_set(body,'$.raw.text','changed') WHERE message_id='m2'")
        with self.assertRaisesRegex(ChannelError, 'anchor_mismatch'):
            self.channel.handle({'op':'selectFiles', **msg})
        with self.transport.db:
            self.transport.db.execute("UPDATE meta SET value='[\"another-profile\",\"g\"]' WHERE key='scope'")
        with self.assertRaisesRegex(ChannelError, 'scope_mismatch'):
            self.channel.handle({'op':'selectFiles', **msg})
        self.assertEqual(self.dws.downloaded, [])

    def test_explicit_mixed_sources_follow_request_order_and_freeze_at_command(self):
        def photos(seq, sender, ids):
            return event(seq,' '.join('[图片消息](mediaId='+rid+')' for rid in ids),sender=sender,
                         refs=[ref('mediaId',rid) for rid in ids])['raw']
        prior = [photos(1,'other',['old']), file(2,'交接单.txt'),photos(3,'other',['left','right']),
                 photos(4,'stranger',['foreign'])]
        request = event(5,'/agent --attachments [{"image":2},"交接单.txt",{"image":1}] 核对')['raw']
        msg = self.admit(prior, request, [photos(6,'other',['late'])])
        self.assertEqual(self.channel.handle({'op':'selectFiles',**msg}),{'count':3,'task':'核对'})
        parts = [self.channel.handle({'op':'selectedFile',**msg,'index':n})['part'] for n in range(3)]
        self.assertEqual([p['resource']['resourceId'] for p in parts],['left','resource-2','right'])
        self.assertEqual([p['type'] for p in parts],['image','file','image'])
        self.assertNotEqual(parts[0]['sha256'],parts[2]['sha256'])
        for p in parts:self.assertEqual(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),p['sha256'])

    def test_missing_malformed_or_unpositioned_image_does_not_substitute_an_older_one(self):
        prior=[event(1,'[图片消息](mediaId=before)',refs=[ref('mediaId','before')])['raw'],
               event(2,'[图片消息]',refs=[ref('mediaId','bad')])['raw']]
        msg=self.admit(prior,event(3,'/agent --attachments [{"image":1}] 核对')['raw'])
        self.assertEqual(self.channel.handle({'op':'selectFiles',**msg}),{'error':'file_selection_missing_or_ambiguous'})
        self.assertFalse(self.dws.downloaded)

    def test_invalid_or_duplicate_positions_and_quoted_only_sources_are_rejected(self):
        from dingtalk_bridge.message_model import normalize,select_file_sources
        origin=normalize(event(1,'引用',quote=event(11,'[图片消息](mediaId=only-quote)',
                                                     refs=[ref('mediaId','only-quote')])['raw']),CFG)
        request=normalize(event(2,'请处理'),CFG)
        for argument in ('[{"image":0}]','[{"image":true}]','[{"image":2,"file":"x"}]',
                         '[{"image":1},{"image":1}]','["same.txt","same.txt"]'):
            with self.subTest(argument=argument),self.assertRaisesRegex(ValueError,'file_selection_invalid'):
                select_file_sources(request,'--attachments '+argument+' 核对',[origin],allow_images=True)
        with self.assertRaisesRegex(ValueError,'file_selection_missing_or_ambiguous'):
            select_file_sources(request,'--attachments [{"image":1}] 核对',[origin],allow_images=True)


    def test_natural_followup_uses_original_observed_by_this_consumer(self):
        image = event(1, '[图片消息](mediaId=photo)', refs=[ref('mediaId','photo')])['raw']
        self.channel = HostChannel(self.root, self.route, self.state, 0, self.api)
        self.addCleanup(self.channel.close)
        question = '读刚才那张图上的订单号'
        self.dws.messages = [image, event(2,question)['raw']]
        self.transport.sync()
        # A participation decision can leave a silent upload in the durable inbox.
        first = self.channel.handle({'op':'poll','ordered':True})['message']
        self.assertEqual(first['id'],'m1')
        self.channel.ack('m1','ignored')
        self.assertEqual(self.channel.poll()['message']['id'],'m2')
        selection = self.channel.handle({'op':'selectFiles','messageId':'m2','recentKind':'image'})
        self.assertEqual(selection,{'count':1,'task':question})
        part = self.channel.handle({'op':'selectedFile','messageId':'m2','index':0})['part']
        self.assertEqual(part['type'],'image')
        blob = '原件:m1'.encode()
        self.assertEqual(Path(part['path']).read_bytes(),blob)
        self.assertEqual(part['sha256'],hashlib.sha256(blob).hexdigest())
        self.assertEqual(self.dws.downloaded,['m1'])

    def test_natural_followup_does_not_reach_pre_admission_history(self):
        msg = self.admit([file(1)], event(2,'读刚才那份文件')['raw'])
        self.assertEqual(self.channel.handle({'op':'selectFiles', **msg, 'recentKind':'file'}),
                         {'error':'recent_original_ambiguous'})
        self.assertFalse(self.dws.downloaded)

    def test_natural_followup_refuses_competing_originals_and_uncertain_history(self):
        from dingtalk_bridge.message_model import normalize, recent_original
        question = normalize(event(10,'读刚才那张图'), CFG)
        image = normalize(event(1,'[图片消息](mediaId=img)',refs=[ref('mediaId','img')]), CFG)
        multi = normalize(event(2,'[图片消息](mediaId=a)[图片消息](mediaId=b)',
                                refs=[ref('mediaId','a'),ref('mediaId','b')]), CFG)
        quoted = normalize(event(3,'引用',quote=event(1,'[图片消息](mediaId=img)',refs=[ref('mediaId','img')])['raw']), CFG)
        text = normalize(event(4,'讨论'), CFG)
        stranger = {**image,'senderId':'another-sender'}
        with self.subTest('unique'):
            self.assertEqual(recent_original(question,[text,image],'image')[1]['imagePartIndex'],0)
        for history in ([multi], [stranger,image], [stranger], [{**image,'fromSelf':True}],
                        [None,image], [quoted,image], [text]*8+[image],
                        [{**image,'conversationId':'other'}], [{**image,'accountId':'wrong'}],
                        [{**image,'issues':['unpositioned_resources']}],
                        [{**image,'receivedAt':'2026-11-11T11:57:59+08:00'}],
                        [{**image,'receivedAt':'2026-11-11T12:00:01+08:00'}]):
            with self.subTest(history=history), self.assertRaisesRegex(ValueError,'recent_original_ambiguous'):
                recent_original(question,history,'image')

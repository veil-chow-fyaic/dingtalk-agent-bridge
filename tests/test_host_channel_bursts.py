"""Mixed native-channel input: order, availability, bounded failures and stop/restart."""
from contextlib import closing
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import time
import unittest

from dingtalk_bridge.host_channel import HostChannel
from test_host_channel import Transport
from test_routing_consumer import CFG, event, ref


class BurstTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.route = {**CFG, 'executionOwner': 'openclaw'}
        self.api = Transport(self.root, self.route)

    def open(self):
        return closing(HostChannel(self.root, self.route, None, 0, self.api))

    def file(self, seq, kind):
        key = str(seq)
        if kind == 'image':
            return event(seq, text='检验[图片消息](mediaId=' + key + ')', refs=[ref('mediaId',key)])
        return event(seq, text='[文件] 箱单.csv fileId: ' + key, refs=[ref('fileId',key)])

    def record(self, seq, kind):
        p = self.root / 'local/runtime/downloads' / str(seq)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = f'item,{seq}'.encode()
        p.write_bytes(data)
        return {'ok': True, 'downloads': [{'type':'mediaId' if kind=='image' else 'fileId',
            'resourceId':str(seq),'localPath':str(p.relative_to(self.root)), 'sizeBytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest()}]}

    @staticmethod
    def poll(channel):
        return channel.handle({'op':'poll','orderedMedia':True})['message']

    def hydrated(self, channel, mid):
        end = time.monotonic() + 4
        while time.monotonic() < end:
            res = channel.handle({'op':'prepareMedia','messageId':mid})
            if res['state'] not in ('waiting','retrying'):
                return res
            time.sleep(.002)
        self.fail('media preparation timed out')

    def test_mixed_burst_exceeds_old_window_in_both_chat_types(self):
        for chat_type in ('direct','group'):
            with self.subTest(chat_type=chat_type):
                self.route['conversationType'] = chat_type
                self.api.events = [self.file(i, 'file' if i%2 else 'image') for i in range(1,24)]
                self.api.events.append(event(24, text='刚才发的附件收全了吗'))
                received=[]
                with self.open() as channel:
                    for seq in range(1,24):
                        model = self.poll(channel)
                        self.assertTrue(model['mediaPreparing'])
                        self.assertEqual(model['id'], 'm'+str(seq))
                        self.api.download = self.record(seq,'file' if seq%2 else 'image')
                        prepared = self.hydrated(channel,model['id'])
                        self.assertEqual(prepared['state'],'ready')
                        part = next(p for p in prepared['message']['parts'] if p['type']!='text')
                        self.assertEqual(Path(part['path']).read_bytes(),f'item,{seq}'.encode())
                        received.append(model['id'])
                        channel.ack(model['id'],'done')
                    msg = self.poll(channel)
                    self.assertEqual(msg['id'],'m24')
                    channel.ack(msg['id'],'done')
                    self.assertEqual(len(set(received)),23)
                    self.assertIsNone(self.poll(channel))
                with self.open() as restarted:
                    self.assertIsNone(self.poll(restarted))
                    self.assertEqual(restarted.handle({'op':'summary'})['dispatch'],{'done':24})
                # The inbox scope includes the route and its dedicated consumer.
                # Use a fresh synthetic root for the second independently configured chat.
                if chat_type == 'direct':
                    self.root = self.root / 'second'
                    self.api = Transport(self.root,self.route)

    def test_unavailable_original_has_receipt_and_later_text_proceeds(self):
        self.api.events = [self.file(1,'file'),event(2,text='继续')]
        self.api.download = {'ok':False}
        with self.open() as channel:
            self.assertEqual(self.poll(channel)['id'],'m1')
            self.assertEqual(self.hydrated(channel,'m1'),{'state':'unavailable'})
            row=channel.db.execute('SELECT state,attempts FROM inbox WHERE message_id="m1"').fetchone()
            self.assertEqual(tuple(row),('media_failed',3))
            channel.ack('m1','done')  # e.g. confirmed user notice
            self.assertEqual(self.poll(channel)['id'],'m2')
            channel.ack('m2','done')
        with self.open() as restarted:
            self.assertIsNone(self.poll(restarted))
            summary = restarted.handle({'op':'summary','includeInbox':True})
            self.assertEqual(summary['mediaFailures'],{'original_unavailable':1})

    def test_slow_download_can_be_cancelled_without_dispatch_or_blocking_followup(self):
        self.api.events = [self.file(1,'image'),event(2,text='继续'),event(3,text='/agent cancel')]
        started, release = Event(), Event()
        api = self.api
        def slow(path,payload=None):
            if path == '/v1/attachments':
                started.set()
                release.wait(5)
                return {'ok':False}
            return api(path,payload)
        self.api = slow
        with self.open() as channel:
            try:
                self.assertEqual(self.poll(channel)['id'],'m1')
                self.assertEqual(channel.prepare_media('m1')['state'],'waiting')
                self.assertTrue(started.wait(2))
                control=channel.poll_cancel('m1')['message']
                self.assertEqual(control['id'],'m3')
                self.assertEqual(channel.prepare_media('m1')['state'],'waiting')
                channel.ack('m3','done')
                channel.ack('m1','canceled','m3')
                self.assertEqual(self.poll(channel)['id'],'m2')
                channel.ack('m2','done')
                self.assertEqual(channel.handle({'op':'summary'})['dispatch'],{'done':2,'canceled':1})
                self.assertEqual(api.sends,[])
            finally:
                release.set()

    def test_only_pre_dispatch_media_recovered_after_restart(self):
        self.api.events = [self.file(1,'file'), self.file(2,'image'),event(3,text='下一条')]
        with self.open() as channel:
            self.assertEqual(self.poll(channel)['id'],'m1')
            self.assertIsNone(self.poll(channel))
            self.assertEqual(channel.handle({'op':'summary'})['dispatch'],{'preparing':1})
        with self.open() as restarted:
            self.assertEqual(self.poll(restarted)['id'],'m1')
            self.api.download=self.record(1,'file')
            self.assertEqual(self.hydrated(restarted,'m1')['state'],'ready')
        with self.open() as interrupted:
            self.assertEqual(self.poll(interrupted)['id'],'m2')
            interrupted.ack('m2','ignored')
            self.assertEqual(self.poll(interrupted)['id'],'m3')
            interrupted.ack('m3','done')
            self.assertEqual(interrupted.handle({'op':'summary'})['dispatch'],{'unknown':1,'ignored':1,'done':1})

    def test_stop_crossing_restart_fences_unstarted_original(self):
        self.api.events = [self.file(1,'image'),event(2,text='/agent cancel'),event(3,text='下一条')]
        with self.open() as channel:
            self.poll(channel)
            self.assertEqual(channel.poll_cancel('m1')['message']['id'],'m2')
        with self.open() as restarted:
            self.assertEqual(self.poll(restarted)['id'],'m3')
            self.assertEqual(restarted.handle({'op':'summary'})['dispatch'],{'unknown':2,'claimed':1})

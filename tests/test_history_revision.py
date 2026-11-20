"""Complete a provider-truncated projection without changing its original sequence or replaying a task."""
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.consumer import Inbox
from dingtalk_bridge.core import Bridge
from dingtalk_bridge.host_channel import HostChannel
from test_agent_gateway import FakeRuntime, SETTINGS
from test_routing_consumer import CFG


def message(mid, text, **changes):
    return {'messageId': mid, 'conversationId': 'g', 'senderId':'other', 'text':text,
            'createTime':'2026-11-19T10:00:00+00:00', **changes}


class Provider:
    def __init__(self, root):
        self.root = root
        self.messages = []
        self.file_data = {}
        self.downloads = 0

    def call(self, args):
        if args[1] == '+messages-mget':
            self.downloads += 1
            folder = Path(args[args.index('--output-dir')+1])
            (self.root/folder).mkdir(parents=True)
            entries = []
            for rid, data in self.file_data.items():
                path = folder/rid
                (self.root/path).write_bytes(data)
                entries.append({'resourceType':'fileId','resourceId':rid,'localPath':str(path),'sizeBytes':len(data)})
            return {'messages':self.messages, 'resourceDownloads':{'ok':True, 'downloads':entries}}
        assert args[1] == '+chat-messages'
        return {'messages':self.messages,'complete':True,'hasMore':False}


class HistoryRevisionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.provider = Provider(self.root)
        self.bridge = Bridge(self.root, CFG, self.provider)
        self.addCleanup(lambda: self.bridge.close())

    def sync(self, *messages):
        self.provider.messages = list(messages)
        return self.bridge.sync()

    def api(self, path, data=None):
        self.assertTrue(path.startswith('/v1/events?'))
        q = parse_qs(urlsplit(path).query)
        self.assertIn('after_revision', q)
        return {'account_id':'a','conversation_id':'g',
                **self.bridge.event_batch(after=int(q['after'][0]), limit=int(q['limit'][0]),
                                          after_revision=int(q['after_revision'][0]))}

    def test_prior_projection_is_published_once_in_original_order_and_initial_floor_is_respected(self):
        old = message('old','first fragment',truncated=True)
        normal = message('normal','later ordinary message')
        self.sync(old,normal)
        legacy = self.bridge.event_batch()
        self.assertNotIn('revisions', legacy)
        with closing(Inbox(self.root,CFG,'existing')) as inbox:
            inbox.ingest(legacy)
            self.assertEqual([r['message']['id'] for r in inbox.ready()], ['normal'])
        # A legacy installation has durable event/inbox rows but no revision table.
        with self.bridge.db:
            self.bridge.db.execute('DROP TABLE history_revisions')
        self.bridge.close()
        self.bridge = Bridge(self.root, CFG, self.provider)
        good = message('old','fully available')
        self.assertEqual(self.sync(good)['revised'], 1)
        self.assertEqual(self.sync({**good,'text':'unrelated edit'})['revised'], 0)
        page = self.bridge.event_batch(2,200,after_revision=0)
        self.assertEqual(page['events'], [])
        self.assertEqual([(r['revision'],r['event']['seq']) for r in page['revisions']], [(1,1)])
        with closing(Inbox(self.root,CFG,'existing')) as inbox:
            inbox.ingest(page)
            self.assertEqual(inbox.read_cursors(), {'after':2,'after_revision':1})
            self.assertEqual([(r['seq'],r['message']['parts'][0]['text']) for r in inbox.ready()],
                             [(1,'fully available'), (2,'later ordinary message')])
        with closing(Inbox(self.root,CFG,'floor')) as inbox:
            with inbox.db:
                inbox.db.execute('INSERT INTO meta VALUES ("cursor","2")')
            inbox.ingest(page)
            self.assertEqual(inbox.ready(), [])
            self.assertEqual(inbox.revision_cursor, 1)
        with closing(Inbox(self.root,CFG,'new')) as inbox:
            inbox.ingest(self.bridge.event_batch(after_revision=0))
            self.assertEqual([r['seq'] for r in inbox.ready()], [1,2])

    def test_revision_page_cannot_skip_unseen_originals_or_change_a_known_sender(self):
        self.sync(message('a','old-a',partial=True), message('b','old-b',truncated=True))
        self.assertEqual(self.sync(message('b','wrong sender',senderId='different'))['revised'],0)
        self.assertEqual(self.sync(message('b','still truncated',partial=True))['revised'],0)
        self.assertEqual(self.sync(message('b','new-b'),message('a','new-a'))['revised'],2)
        with closing(Inbox(self.root,CFG)) as inbox:
            first = self.bridge.event_batch(0,1,after_revision=0)
            self.assertEqual(first['revisions'], [])
            inbox.ingest(first)
            second = self.bridge.event_batch(1,1,after_revision=0)
            self.assertEqual(second['revisions'][0]['event']['message_id'], 'b')
            inbox.ingest(second)
            inbox.ingest(self.bridge.event_batch(2,1,after_revision=inbox.revision_cursor))
            self.assertEqual([r['message']['id'] for r in inbox.ready()], ['a','b'])
            self.assertEqual(inbox.revision_cursor, 2)

    def test_host_dispatches_repaired_input_once_and_never_replays_a_done_task(self):
        self.sync(message('a','/agent pending',truncated=True),message('b','/agent already done'))
        route = {**CFG,'conversationType':'group','executionOwner':'openclaw'}
        with closing(HostChannel(self.root, route, None, 0, self.api)) as host:
            self.assertEqual(host.poll_ordered()['message']['id'], 'b')
            host.ack('b','done')
        self.sync(message('a','/agent completed projection'),message('c','/agent next task'))
        with closing(HostChannel(self.root, route, None, 0, self.api)) as host:
            first = host.poll_ordered()['message']
            self.assertEqual((first['id'],first['parts'][0]['text']), ('a','/agent completed projection'))
            host.ack('a','done')
            self.assertEqual(host.poll_ordered()['message']['id'], 'c')
            host.ack('c','done')
            self.assertIsNone(host.poll_ordered()['message'])
            self.assertEqual(host.handle({'op':'summary'})['dispatch'], {'done':3})

    def test_gateway_recovers_its_never_executed_block_after_restart(self):
        runtime = FakeRuntime()
        self.sync(message('partial-job','/agent incomplete',truncated=True),
                  message('finished-job','/agent regular'))
        with closing(Gateway(self.root, CFG, None, SETTINGS, self.api, runtime)) as gateway:
            gateway.intake()
            self.assertEqual(gateway.summary()['jobs'], {'blocked':1,'queued':1})
            self.assertTrue(gateway.execute_one())
        self.sync(message('partial-job','/agent corrected request'),message('another','/agent final'))
        with closing(Gateway(self.root, CFG, None, SETTINGS, self.api, runtime)) as gateway:
            gateway.intake()
            jobs = gateway.db.execute('SELECT command,state FROM jobs ORDER BY seq').fetchall()
            self.assertEqual([tuple(row) for row in jobs], [('corrected request','queued'),
                             ('regular','completed'),('final','queued')])
            self.assertTrue(gateway.execute_one())
            self.assertTrue(gateway.execute_one())
            gateway.intake()
            self.assertFalse(gateway.execute_one())
            self.assertEqual(runtime.calls, 3)

    def test_native_control_scanner_finds_corrected_later_stop(self):
        self.sync(message('running','/agent long'), message('stop','/agent can',truncated=True))
        route = {**CFG,'conversationType':'group','executionOwner':'openclaw'}
        with closing(HostChannel(self.root, route, None, 0, self.api)) as host:
            self.assertEqual(host.poll_ordered()['message']['id'], 'running')
            self.assertIsNone(host.poll_cancel('running')['message'])
            self.sync(message('stop','/agent cancel'))
            self.assertEqual(host.poll_cancel('running')['message']['id'], 'stop')

    def test_cached_partial_resource_set_is_refetched_after_a_verified_correction(self):
        ref = {'type':'fileId','resourceId':'pdf'}
        old = message('f','incomplete',partial=True)
        self.sync(old)
        empty = self.bridge.download('f')
        self.assertEqual(empty['downloads'], [])
        self.provider.file_data = {'pdf':b'sample'}
        self.sync(message('f','[文件] file.pdf fileId: pdf',resourceRefs=[ref]))
        self.assertEqual(self.bridge.download('f')['downloads'][0]['resourceId'],'pdf')
        self.assertEqual(self.bridge.download('f')['downloads'][0]['sizeBytes'],6)
        self.assertEqual(self.provider.downloads, 2)

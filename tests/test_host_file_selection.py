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
        path = Path(args[args.index('--output-dir') + 1]) / 'original'
        (self.root / path).parent.mkdir(parents=True)
        (self.root / path).write_bytes(content)
        ledger = {'ok': True, 'downloads': [{'resourceType':'fileId', 'resourceId':raw['resourceRefs'][0]['resourceId'],
                                              'localPath': str(path),
                                              'sizeBytes': len(content)}]}
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

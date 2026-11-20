"""A late history correction must not redirect an older stop onto a new turn."""
import unittest
from contextlib import closing
from dingtalk_bridge.host_channel import HostChannel
import test_history_revision as fixtures
from test_history_revision import message
from test_routing_consumer import CFG


class HostStopChronologyTests(unittest.TestCase):
    setUp = fixtures.HistoryRevisionTests.setUp
    api = fixtures.HistoryRevisionTests.api
    sync = fixtures.HistoryRevisionTests.sync

    def test_backfilled_stop_created_before_active_turn_cannot_cancel_it(self):
        route = {**CFG, 'conversationType':'group','executionOwner':'openclaw'}
        active = message('new','/agent process the new order', createTime='2026-11-19T10:03:53+00:00')
        fragment = message('old-stop','/agent can',truncated=True,createTime='2026-11-19T18:02:17+08:00')
        self.sync(active)
        with closing(HostChannel(self.root, route, None, 0, self.api)) as channel:
            self.assertEqual(channel.poll_ordered()['message']['id'],'new')
            self.sync(fragment)
            self.assertIsNone(channel.poll_cancel('new')['message'])
            full = {k:v for k,v in fragment.items() if k!='truncated'}
            self.sync({**full,'text':'/agent cancel'})
            self.assertIsNone(channel.poll_cancel('new')['message'])
            self.assertEqual(channel.cancel_matches,{})
            self.assertEqual(channel.handle({'op':'summary'})['dispatch'],{'claimed':1,'ignored':1})
            self.assertEqual(channel.ack('new','done'),{'status':'done'})

    def test_larger_revision_cursor_cannot_override_original_seq_in_direct_chat(self):
        route = {**CFG, 'conversationType':'direct','executionOwner':'openclaw'}
        self.bridge.config = {**self.bridge.config,'conversationType':'direct','peerOpenDingTalkId':'test-peer'}
        old = message('stop','/st',truncated=True)
        self.sync(old,message('running','work on the current order'))
        with closing(HostChannel(self.root, route, None, 0, self.api)) as channel:
            self.assertEqual(channel.poll_ordered()['message']['id'],'running')
            self.sync(message('stop','/stop'))
            self.assertIsNone(channel.poll_cancel('running')['message'])
            # A fresh stop from the same sender with the same timestamp is ordered
            # by its original seq. Its higher correction cursor has no authority.
            self.sync(message('fresh-stop','/stop'))
            self.assertEqual(channel.poll_cancel('running')['message']['id'],'fresh-stop')
            self.assertEqual(channel.cancel_matches,{'fresh-stop':'running'})

    def test_ambiguous_unzoned_dst_times_cannot_prove_order(self):
        route = {**CFG, 'conversationType':'group','executionOwner':'openclaw',
                 'historyTimezone':'America/New_York'}
        active = message('active','/agent long',createTime='2026-11-01 01:15:00')
        ambiguous = message('ambiguous','/agent cancel',createTime='2026-11-01 01:30:00')
        certain = message('certain','/agent cancel',createTime='2026-11-01 02:10:00')
        self.sync(active)
        with closing(HostChannel(self.root, route, None, 0, self.api)) as channel:
            self.assertEqual(channel.poll_ordered()['message']['id'],'active')
            self.sync(ambiguous,certain)
            self.assertEqual(channel.poll_cancel('active')['message']['id'],'certain')
            self.assertEqual(channel.cancel_matches,{'certain':'active'})

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from dingtalk_bridge.core import BridgeError
from dingtalk_bridge.group_participation import mention_message_ids
from dingtalk_bridge.host_channel import ChannelError, HostChannel
from test_host_channel import Transport
from test_routing_consumer import CFG, event, ref


def mentions(ids=(), *, more=False, group='g'):
    return {'result': {'hasMore': more, 'conversationMessagesList': [
        {'openConversationId': group, 'messages': [{'messageId': i, 'conversationId': group} for i in ids]},
    ]}}


class GroupParticipationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.route = {**CFG, 'binary': 'fixture', 'executionOwner': 'openclaw', 'conversationType': 'group'}
        self.api = Transport(self.root, self.route)
        self.channel = None

    def open(self, verify_mentions=False):
        if self.channel:
            self.channel.close()
        self.channel = HostChannel(self.root, self.route, None, 0, self.api,
                                   mention_senders=['other'] if verify_mentions else [])
        self.addCleanup(self.channel.close)
        return self.channel

    def smart(self, channel):
        return channel.handle({'op':'poll','orderedMedia':True,'deferGroupExecution':True})['message']

    def test_mentions_match_only_exact_id_from_same_account_and_group(self):
        h = self.open(True)
        self.api.events = [event(1, text='@assistant not a real mention'), event(2, text='native metadata')]
        h.mention_index.dws.call = Mock(return_value=mentions(['m2']))
        first = h.poll()['message']
        self.assertFalse(first['mentionedSelf'])
        self.assertTrue(h.poll()['message']['mentionedSelf'])
        h.mention_index.dws.call.assert_called_once()
        args, = h.mention_index.dws.call.call_args.args
        self.assertEqual(args[:5], ['chat','message','list-mentions','--conversation-id','g'])
        self.assertIn('--start', args)
        self.assertIn('--end', args)
        self.api.events.append(event(3, text='newer event'))
        h.poll()
        self.assertEqual(h.mention_index.dws.call.call_count, 2)

    def test_pending_mention_is_durable_and_not_a_silent_answer_or_claim(self):
        h = self.open(True)
        self.api.events = [event(1)]
        h.mention_index.dws.call = Mock(return_value=mentions([], more=True))
        self.assertIsNone(h.poll()['message'])
        self.assertIsNone(h.poll()['message'])
        h.mention_index.dws.call.assert_called_once()
        h = self.open(True)
        h.mention_index.dws.call = Mock(side_effect=BridgeError('unavailable'))
        self.assertIsNone(h.poll()['message'])
        h.mention_index.dws.call.assert_not_called()
        h.db.execute('UPDATE host_participation_wait SET retry_at=0')
        self.assertIsNone(h.poll()['message'])
        self.assertEqual(h.db.execute('SELECT reason FROM host_participation_wait').fetchone()[0],
                         'mention_lookup_unavailable')
        self.assertEqual(h.db.execute('SELECT count(*) FROM host_dispatch').fetchone()[0], 0)
        h.mention_index.dws.call = Mock(return_value=mentions(['m1']))
        h.db.execute('UPDATE host_participation_wait SET retry_at=0')
        self.assertTrue(h.poll()['message']['mentionedSelf'])
        h.ack('m1','done')
        self.assertEqual(h.db.execute('SELECT count(*) FROM host_participation_wait').fetchone()[0], 0)

    def test_foreign_ids_invalid_results_and_partial_pages(self):
        with self.assertRaisesRegex(ValueError, 'scope'):
            mention_message_ids(mentions(['m1'], group='other'), 'g')
        self.assertEqual(mention_message_ids(mentions(['m1'], more=True),'g'), ({'m1'}, False))
        self.assertFalse(mention_message_ids({**mentions(), 'paging':{'partial':True}},'g')[1])
        with self.assertRaises(ValueError):
            mention_message_ids({}, 'g')

    def test_official_mention_pagination_ids_and_per_message_conversation(self):
        page = mentions()
        group = page['result']['conversationMessagesList'][0]
        group['messages'] = [{'id':'m1'}, {'openMsgId':'m2','id':'different-internal-id'},
                             {'msg_id':3,'openConversationId':'g'}]
        self.assertEqual(mention_message_ids(page,'g'), ({'m1','m2','3'},True))
        self.assertFalse(mention_message_ids({**page,'paging':{'sourceExhausted':False}},'g')[1])
        group['messages'].append({'openMessageId':'m4','openConversationId':'another'})
        with self.assertRaisesRegex(ValueError,'scope'):
            mention_message_ids(page,'g')

    def test_context_does_not_expose_other_senders_or_paths(self):
        h = self.open()
        self.api.events = [event(1, sender='outsider', text='private'), event(2, sender='self', text='reply'),
                           event(3, text='follow up'), event(4, text='new')]
        h.receive()
        for _ in range(2):
            h.ack(h.poll()['message']['id'],'ignored')
        self.assertEqual(h.poll()['message']['id'],'m4')
        ctx = h.handle({'op':'groupContext','messageId':'m4','allowSenders':['other']})
        self.assertEqual([v['text'] for v in ctx['recent']], ['reply','follow up'])
        self.assertEqual([v['speaker'] for v in ctx['recent']], ['assistant','current_sender'])

    def test_tool_free_silence_is_bound_to_its_original_despite_an_independent_send(self):
        h = self.open()
        self.api.events = [event(1), event(2)]
        self.smart(h)
        h.ack('m1','done',silent_reason='agent_decision')
        h = self.open()
        self.assertEqual(h.db.execute('SELECT reason FROM host_silent_replies WHERE message_id="m1"').fetchone()[0],
                         'agent_decision')
        h.ack('m1','done',silent_reason='agent_decision')
        with self.assertRaisesRegex(ChannelError, 'conflict'):
            h.ack('m1','done')
        self.assertEqual(self.smart(h)['id'],'m2')
        h.send('independent', {'text':'scheduled reminder'})
        h.ack('m2','done',silent_reason='agent_decision')
        self.assertEqual(h.db.execute('SELECT COUNT(*) FROM host_silent_replies').fetchone()[0], 2)

    def test_decision_error_retries_only_the_pre_run_classifier(self):
        h = self.open()
        self.api.events = [event(1),event(2, sender='independent')]
        self.smart(h)
        h.handle({'op':'deferParticipation','messageId':'m1','reason':'classifier_unavailable'})
        self.assertEqual(h.poll()['message']['id'],'m2')
        h.ack('m2','done')
        h = self.open()
        self.assertIsNone(h.poll()['message'])
        self.assertFalse(h.db.execute('SELECT count(*) FROM host_silent_replies').fetchone()[0])
        h.db.execute('UPDATE host_participation_wait SET retry_at=0')
        self.assertEqual(self.smart(h)['id'],'m1')
        h.send('independent', {'text':'scheduled reminder'})
        h.defer_participation('m1','classifier_unavailable')
        self.assertEqual(h.db.execute('SELECT attempts FROM host_participation_wait').fetchone()[0],2)

    def test_pending_picture_blocks_its_sender_followup_across_restart(self):
        h = self.open()
        self.api.events = [event(1, text='[图片消息](mediaId=im)', refs=[ref('mediaId','im')]),
                           event(2, text='What does the picture say?'),
                           event(3, text='/agent other work', sender='second')]
        poll = lambda channel: channel.handle({'op':'poll','orderedMedia':True})['message']
        first = poll(h)
        self.assertEqual((first['id'],first['mediaPreparing']),('m1',True))
        h.defer_participation('m1','classifier_unavailable')
        self.assertEqual(poll(h)['id'],'m3')
        self.api.events.append(event(4, sender='second', text='/agent cancel'))
        self.assertEqual(h.poll_cancel('m3')['message']['id'],'m4')
        h.ack('m4','done')
        h.ack('m3','canceled',cancel_id='m4')
        h = self.open()
        self.assertIsNone(poll(h))
        self.assertEqual(h.db.execute('SELECT count(*) FROM host_dispatch WHERE message_id="m2"').fetchone()[0],0)
        h.db.execute('UPDATE host_participation_wait SET retry_at=0')
        self.assertEqual(poll(h)['id'],'m1')
        h.ack('m1','done',silent_reason='agent_decision')
        self.assertEqual(poll(h)['id'],'m2')
        self.assertEqual(h.handle({'op':'summary','includeInbox':True})['silentReplies'], {'agent_decision':1})

    def test_stop_during_mention_lookup_drains_lease_without_claiming(self):
        h = self.open(True)
        self.api.events = [event(1)]
        completed = []
        def finish_read(_):
            h.mention_index.stop_when_drained(None,None)
            completed.append(True)
            return mentions(['m1'])
        h.mention_index.dws.call = finish_read
        with self.assertRaises(SystemExit):
            h.poll()
        self.assertEqual(completed,[True])
        self.assertFalse(h.db.execute('SELECT count(*) FROM host_dispatch').fetchone()[0])

    def test_tool_free_decision_restarts_until_business_execution_is_committed(self):
        h = self.open()
        self.api.events = [event(1,text='please help'),event(2,text='/agent run')]
        self.assertTrue(self.smart(h)['participationPreparing'])
        h = self.open()  # terminated while the small decision model was still running
        self.assertEqual(self.smart(h)['id'],'m1')
        self.assertEqual(h.handle({'op':'beginGroupDispatch','messageId':'m1'}),{'state':'claimed'})
        with self.assertRaisesRegex(ChannelError, 'conflict'):
            h.defer_participation('m1','classifier_unavailable')
        with self.assertRaisesRegex(ChannelError, 'conflict'):
            h.ack('m1','done',silent_reason='agent_decision')
        h = self.open()  # terminated after handing the real organization task to its agent
        self.assertEqual(self.smart(h)['id'],'m2')
        self.assertEqual(h.db.execute('SELECT status FROM host_dispatch WHERE message_id="m1"').fetchone()[0],'unknown')
        h.begin_group_dispatch('m2')
        h = self.open()
        self.assertIsNone(self.smart(h))
        self.assertEqual(h.db.execute('SELECT status FROM host_dispatch WHERE message_id="m2"').fetchone()[0],'unknown')

    def test_stop_during_decision_fences_promotion_and_prevents_replay(self):
        h = self.open()
        self.api.events = [event(1,text='work'), event(2,text='/agent cancel')]
        self.smart(h)
        self.assertEqual(h.poll_cancel('m1')['message']['id'],'m2')
        self.assertEqual(h.begin_group_dispatch('m1'),{'state':'stopping'})
        h.ack('m2','done')
        h.ack('m1','canceled',cancel_id='m2')
        h = self.open()
        self.assertIsNone(self.smart(h))
        self.assertEqual(h.db.execute('SELECT cancel_message_id FROM host_cancellations').fetchone()[0],'m2')

    def test_business_no_reply_and_unattributed_send_quarantine_one_turn_only(self):
        h = self.open()
        self.api.events = [event(1),event(2)]
        self.smart(h)
        h.begin_group_dispatch('m1')
        h.send('independent', {'text':'scheduled reminder or host tool'})
        receipt = h.ack('m1','done',silent_reason='host_policy')
        self.assertEqual(receipt, {'status':'unknown'})
        self.assertEqual(h.db.execute('SELECT COUNT(*) FROM host_silent_replies').fetchone()[0], 0)
        self.assertEqual(self.smart(h)['id'],'m2')
        self.assertEqual(h.status('independent',reconcile=True)['state'],'confirmed')

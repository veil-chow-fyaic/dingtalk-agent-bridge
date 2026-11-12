"""Provider evidence must belong to this send; never trust quoted IDs or prose."""
import copy
from pathlib import Path
import tempfile
import unittest

from dingtalk_bridge.core import Bridge, BridgeError
from test_core import CFG, Fake


def accepted():
    return {'sendReceipt': {'contractVersion': 'im.message-send-receipt.v1', 'openTaskId': 'task'},
            'result': {'success': True, 'result': {'openTaskId': 'task'}}}


def status():
    return {'contractVersion': 'im.message-send-status.v1', 'openTaskId': 'task',
            'result': {'sendStatus': 'SUCCESS', 'openMessageId': 'sent', 'openConversationId': 'g'},
            'messageRef': {'openMessageId': 'sent', 'openConversationId': 'g'}}


class EvidenceProvider(Fake):
    def __init__(self, send=None, query=None):
        super().__init__()
        self.send = accepted() if send is None else send
        self.query = status() if query is None else query
        self.queried_tasks = []

    def call(self, args):
        if '+messages-send' in args or '+messages-reply' in args:
            self.sent += 1
            return copy.deepcopy(self.send)
        if '+messages-query-send-status' in args:
            self.queried_tasks.append(args[args.index('--open-task-id') + 1])
            return copy.deepcopy(self.query)
        return super().call(args)


class DeliveryEvidenceContractTests(unittest.TestCase):
    def check_uncertain(self, provider, *, quote=False, queries=0):
        with tempfile.TemporaryDirectory() as temp:
            bridge = Bridge(Path(temp), CFG, provider)
            try:
                if quote:
                    bridge.sync()
                args = {'text': 'synthetic'}
                if quote:
                    args['reply_to'] = 'm2'
                result = bridge.send('one-key', **args)
                self.assertEqual(result['state'], 'outcome_unknown')
                self.assertIsNone(result['message_id'])
                self.assertEqual(len(provider.queried_tasks), queries)
                bridge.close()
                bridge = Bridge(Path(temp), CFG, provider)
                # Calling send again with the original key reads the ledger only.
                self.assertTrue(bridge.send('one-key', **args)['replayed'])
                self.assertEqual(provider.sent, 1)
                self.assertEqual(len(provider.queried_tasks), queries)
            finally:
                bridge.close()

    def test_projected_and_raw_task_conflicts_never_query_or_confirm(self):
        for quote in (False, True):
            for value in ('other-task', ['task'], True):
                receipt = accepted()
                receipt['result']['result']['openTaskId'] = value
                with self.subTest(quote=quote, value=value):
                    self.check_uncertain(EvidenceProvider(send=receipt), quote=quote)

    def test_wrong_or_malformed_status_task_cannot_confirm_or_fail_this_send(self):
        for terminal in ('SUCCESS', 'FAILED'):
            for value in ('other-task', ['task'], True):
                query = status()
                query['openTaskId'] = value
                query['result']['sendStatus'] = terminal
                with self.subTest(terminal=terminal, value=value):
                    self.check_uncertain(EvidenceProvider(query=query), queries=1)

    def test_conflicting_or_invalid_outgoing_identity_is_not_confirmation(self):
        cases = []
        for value in ('other-message', 7, True, '   '):
            query = status()
            query['messageRef']['openMessageId'] = value
            cases.append(query)
        query = status()
        query['result']['openConversationId'] = 'other-conversation'
        cases.append(query)
        for query in cases:
            with self.subTest(query=query):
                self.check_uncertain(EvidenceProvider(query=query), queries=1)

    def test_quote_source_and_nonprovider_success_noise_never_prove_send(self):
        for noise in ({'referencedMessage': {'openTaskId': 'source-task', 'openMessageId': 'm2'}},
                      {'nextActions': [{'arguments': {'openTaskId': 'source-task'}}]},
                      {'result': {'text': 'SUCCESS 200 sent', 'processQueryKey': 'recall-key'}},
                      {'success': True, 'idempotency': {'state': 'duplicate_confirmed'}}):
            with self.subTest(noise=noise):
                self.check_uncertain(EvidenceProvider(send=noise), quote=True)

    def test_explicit_nested_failure_and_wrong_contract_are_not_acceptance(self):
        cases = []
        receipt = accepted()
        receipt['result']['success'] = False
        cases.append(receipt)
        receipt = accepted()
        receipt['sendReceipt']['contractVersion'] = 'unrelated-receipt.v1'
        cases.append(receipt)
        for receipt in cases:
            with self.subTest(receipt=receipt):
                self.check_uncertain(EvidenceProvider(send=receipt))
        query = status()
        query['contractVersion'] = 'unrelated-status.v1'
        self.check_uncertain(EvidenceProvider(query=query), queries=1)

    def test_projected_source_message_is_not_new_quote_delivery(self):
        query = status()
        query['result']['openMessageId'] = 'm2'
        query['messageRef']['openMessageId'] = 'm2'
        self.check_uncertain(EvidenceProvider(query=query), quote=True, queries=1)

    def test_pending_ignores_metadata_success_and_matching_reply_can_confirm(self):
        query = status()
        query['result']['sendStatus'] = 'PENDING'
        query['result']['metadata'] = {'sendStatus': 'SUCCESS', 'openTaskId': 'not-provider-evidence'}
        provider = EvidenceProvider(query=query)
        with tempfile.TemporaryDirectory() as temp:
            bridge = Bridge(Path(temp), CFG, provider)
            try:
                self.assertEqual(bridge.send('one-key', text='synthetic')['state'], 'submitted')
                provider.query = status()
                confirmed = bridge.reconcile('one-key')
                self.assertEqual(confirmed['state'], 'confirmed')
                self.assertEqual(confirmed['message_id'], 'sent')
                self.assertEqual(provider.queried_tasks, ['task', 'task'])
                self.assertEqual(provider.sent, 1)
            finally:
                bridge.close()

    def test_nested_status_task_conflict_leaves_existing_pending_record_unchanged(self):
        provider = EvidenceProvider()
        provider.query['result']['sendStatus'] = 'PENDING'
        with tempfile.TemporaryDirectory() as temp:
            bridge = Bridge(Path(temp), CFG, provider)
            try:
                before = bridge.send('one-key', text='synthetic')
                provider.query = status()
                provider.query['result']['openTaskId'] = 'other-task'
                with self.assertRaises(BridgeError):
                    bridge.reconcile('one-key')
                self.assertEqual(bridge.delivery('one-key'), before)
                self.assertEqual(provider.sent, 1)
            finally:
                bridge.close()


if __name__ == '__main__':
    unittest.main()

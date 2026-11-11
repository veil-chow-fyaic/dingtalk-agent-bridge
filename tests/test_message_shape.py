"""A malformed payload must not prevent later valid events from reaching intake."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.consumer import Inbox
from test_agent_gateway import SETTINGS, FakeAPI, FakeRuntime
from test_routing_consumer import CFG, event


def malformed_events():
    events = []
    for raw in (None, [], 'invalid', 7):
        item = event(len(events) + 1)
        item['raw'] = raw
        events.append(item)
    for refs in ([None], ['invalid'], [7], {}, {'fileId': 'invalid'}, None, 'invalid'):
        for quoted in (False, True):
            item = event(len(events) + 1, text='/agent must not execute')
            source = item['raw']
            if quoted:
                source['quotedMessage'] = {'conversationId': 'g', 'text': 'quoted data'}
                source = source['quotedMessage']
            source['resourceRefs'] = copy.deepcopy(refs)
            events.append(item)
    return events


class MessageShapeTests(unittest.TestCase):
    def test_malformed_raw_and_quote_refs_are_quarantined_without_losing_later_message(self):
        for malformed in malformed_events():
            with self.subTest(raw=malformed['raw']), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                bad = copy.deepcopy(malformed)
                bad['seq'] = 2
                bad['message_id'] = 'm2'
                if isinstance(bad['raw'], dict):
                    bad['raw']['messageId'] = 'm2'
                events = [event(1), bad, event(3)]
                inbox = Inbox(root, CFG)
                try:
                    self.assertEqual(inbox.ingest({'events': events, 'next_cursor': 3}), 3)
                    self.assertEqual(inbox.cursor, 3)
                    row = inbox.db.execute('SELECT * FROM inbox WHERE seq=2').fetchone()
                    self.assertEqual(row['state'], 'quarantined')
                    self.assertIsNone(json.loads(row['model']))
                    self.assertEqual(json.loads(row['raw']), bad)
                    self.assertEqual([r['seq'] for r in inbox.ready()], [1, 3])
                    inbox.close()
                    inbox = Inbox(root, CFG)
                    self.assertEqual(inbox.cursor, 3)
                    self.assertEqual(inbox.ingest({'events': [], 'next_cursor': 3}), 0)
                    self.assertEqual(inbox.summary()['states'], {'normalized': 2, 'quarantined': 1})
                finally:
                    inbox.close()

    def test_gateway_skips_malformed_batch_members_and_executes_only_valid_authorized_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            api, runtime = FakeAPI(), FakeRuntime()
            api.events = malformed_events()
            api.events.append(event(len(api.events) + 1, text='/agent valid task'))
            gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
            try:
                gateway.intake()
                self.assertEqual(gateway.inbox.cursor, len(api.events))
                self.assertEqual(gateway.summary()['jobs'], {'queued': 1})
                self.assertEqual(gateway.inbox.summary()['states'], {'quarantined': 18, 'normalized': 1})
                self.assertTrue(gateway.execute_one())
                gateway.flush()
                self.assertEqual(runtime.calls, 1)
                self.assertEqual(len(api.sends), 3)
                gateway.close()
                gateway = Gateway(root, CFG, None, SETTINGS, api, runtime)
                gateway.intake()
                self.assertFalse(gateway.execute_one())
                gateway.flush()
                self.assertEqual(runtime.calls, 1)
                self.assertEqual(len(api.sends), 3)
            finally:
                gateway.close()


if __name__ == '__main__':
    unittest.main()

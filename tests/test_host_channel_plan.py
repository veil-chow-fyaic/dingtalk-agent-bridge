"""Durable host queue plans bind ordered physical messages to exact content before send."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from dingtalk_bridge.host_channel import ChannelError, HostChannel
from test_host_channel import Transport
from test_routing_consumer import CFG


def entry(key, kind, fields):
    compact = json.dumps(fields, ensure_ascii=False, separators=(',', ':'))
    return {'key': key, 'kind': kind, 'fingerprint': hashlib.sha256(compact.encode()).hexdigest()}


class DeliveryPlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.route = {**CFG, 'executionOwner': 'openclaw'}
        self.api = Transport(self.root, self.route)
        self.open()
        self.text = '  原样\n[Agent]\t🙂 '
        self.first = entry('chunk', 'text', ['text', self.text])
        self.second = entry('chunk-2', 'text', ['text', self.text])
        self.body = b'original'
        self.media = entry('original-file', 'media', [
            'file', '输出.txt', hashlib.sha256(self.body).hexdigest()])

    def open(self):
        self.channel = HostChannel(self.root, self.route, None, 0, self.api)
        self.addCleanup(self.channel.close)

    def plan(self, index, keys, count=2, intent='queue'):
        return self.channel.handle({'op': 'plan', 'intent': intent, 'partIndex': index,
                                    'partCount': count, 'keys': keys})

    def lookup(self, intent='queue'):
        return self.channel.handle({'op': 'lookupPlan', 'intent': intent})

    def test_incomplete_lookup_never_attempts_delivery_and_survives_restart(self):
        self.assertEqual(self.lookup(), {'partCount': None, 'parts': []})
        self.plan(1, [self.media])
        partial = {'partCount': 2, 'parts': [{'partIndex': 1, 'keys': [self.media]}]}
        self.assertEqual(self.lookup(), partial)
        self.channel.close()
        self.open()
        self.assertEqual(self.lookup(), partial)
        self.assertEqual(self.channel.handle({'op': 'reconcile', 'key': self.media['key']})['state'],
                         'outcome_unknown')
        self.assertEqual(self.api.sends, [])
        self.plan(0, [self.first, self.second])
        stable = {'partCount': 2, 'parts': [
            {'partIndex': 0, 'keys': [self.first, self.second]}, {'partIndex': 1, 'keys': [self.media]}]}
        self.assertEqual(self.lookup(), stable)
        self.plan(1, [self.media])
        self.plan(0, [self.first, self.second])
        self.assertEqual(self.lookup(), stable)

    def test_collision_rollback_and_invalid_plans(self):
        self.plan(0, [self.first, self.second])
        baseline = self.lookup()
        changed = entry('chunk', 'text', ['text', 'changed'])
        for index, keys, count in [(0, [self.first, self.second], 3), (0, [changed, self.second], 2),
                                   (0, [self.second, self.first], 2), (1, [self.media, self.first], 2)]:
            with self.subTest(index=index, keys=keys, count=count), self.assertRaisesRegex(
                    ChannelError, 'delivery_plan_conflict'):
                self.plan(index, keys, count=count)
            self.assertEqual(self.lookup(), baseline)
        for invalid in [[], [self.first, self.first], [{**self.media, 'kind': 'bad'}],
                        [{**self.media, 'fingerprint': 'short'}], ['key']]:
            with self.subTest(invalid=invalid), self.assertRaises(ChannelError):
                self.plan(0, invalid, intent='invalid')
            self.assertEqual(self.lookup('invalid'), {'partCount': None, 'parts': []})
        with self.assertRaisesRegex(ChannelError, 'delivery_plan_conflict'):
            self.plan(0, [self.first], intent='another-queue')
        self.assertEqual(self.lookup('another-queue'), {'partCount': None, 'parts': []})
        self.plan(1, [self.media])

    def test_plan_fingerprint_binds_very_first_send_and_reconciliation_is_read_only(self):
        self.plan(0, [self.first], count=1)
        self.channel.close()
        self.open()
        for change in [{'text': self.text.rstrip()}, {'text': self.text, 'replyTo': 'different-target'}]:
            with self.assertRaisesRegex(ChannelError, 'delivery_plan_conflict'):
                self.channel.handle({'op': 'send', 'key': self.first['key'], **change})
        self.assertEqual(self.api.sends, [])
        submitted = self.channel.handle({'op': 'send', 'key': self.first['key'], 'text': self.text})
        self.assertEqual(submitted['state'], 'submitted')
        self.channel.close()
        self.open()
        for _ in range(2):
            self.assertEqual(self.channel.handle({'op':'reconcile','key':'chunk'})['state'], 'confirmed')
        self.assertEqual(len(self.api.sends), 1)
        # Two intentionally identical messages in distinct intents keep distinct IDs.
        independent = entry('independent', 'text', ['text', self.text])
        self.plan(0, [independent], count=1, intent='next')
        self.channel.handle({'op': 'send', 'key': 'independent', 'text': self.text})
        self.assertEqual(len(self.api.sends), 2)

    def test_media_bytes_name_and_kind_are_frozen_before_first_send(self):
        self.plan(0, [self.media], count=1)
        media = {'kind':'file','filename':'输出.txt','base64': base64.b64encode(self.body).decode()}
        for override in [{'filename':'other.txt'}, {'kind':'image'}, {'base64':'b3RoZXI='}]:
            with self.assertRaisesRegex(ChannelError, 'delivery_plan_conflict'):
                self.channel.handle({'op':'send','key':'original-file','media':{**media, **override}})
        self.assertEqual(self.api.sends, [])
        self.channel.handle({'op':'send','key':'original-file','media':media})
        self.assertEqual(len(self.api.sends), 1)
        self.assertEqual((self.root / self.api.sends[0]['file']).read_bytes(), self.body)

    def test_prior_unplanned_send_cannot_be_attached_to_different_queue(self):
        self.channel.handle({'op': 'send', 'key': 'chunk', 'text': self.text})
        with self.assertRaisesRegex(ChannelError, 'delivery_plan_conflict'):
            self.plan(0, [self.first], count=1)
        self.assertEqual(self.lookup(), {'partCount':None, 'parts':[]})
        self.assertEqual(len(self.api.sends), 1)

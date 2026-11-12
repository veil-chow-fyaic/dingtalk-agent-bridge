import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dingtalk_bridge.core import Bridge, BridgeError, DWS, DWSRequestRejected
from test_core import Fake, CFG


class RejectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = {**CFG, 'conversationType': 'direct', 'peerOpenDingTalkId': 'peer'}
        self.fake = Fake()
        self.bridge = Bridge(self.root, self.cfg, self.fake)
        self.text = '🙂' * 3110
        payload = json.dumps({'kind': 'text', 'text': self.text}, sort_keys=True, ensure_ascii=False)
        self.bridge.db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?,?,?)',
            ('old-key', hashlib.sha256(payload.encode()).hexdigest(), payload, 'outcome_unknown', None, None, 'PARAM_ERROR'))
        self.bridge.db.commit()
        self.original = dict(self.bridge.db.execute('SELECT * FROM deliveries').fetchone())
        base = {'product': 'chat', 'tool': 'send_personal_message'}
        self.records = [
            {**base, 'msg': 'command_start', 'execution_id': 'execution-1', 'time': '2026-11-11T22:46:25+08:00'},
            {'msg': 'jsonrpc_request_body', 'execution_id': 'execution-1', 'time': '2026-11-11T22:46:25.1+08:00',
             'tool_name': 'send_personal_message', 'arguments_summary': json.dumps(
                 {'uuid': 'old-key', 'receiverOpenDingTalkId': 'peer', 'msgType': 'text', 'content': '***'})},
            {**base, 'msg': 'business_error', 'time': '2026-11-11T22:46:25.2+08:00',
             'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR',
             'errorMsg': "sendPersonalMessageByServerPush error: Length of filed: 'textContent.text' cannot greater than 5120 but actual is 6220."},
            {**base, 'msg': 'command_end', 'execution_id': 'execution-1', 'time': '2026-11-11T22:46:25.3+08:00',
             'success': False, 'error_reason': 'invalid_request'},
        ]
        self.path = self.root / 'local/evidence.json'
        self.save(self.records)

    def tearDown(self):
        self.bridge.close()
        self.tmp.cleanup()

    def save(self, records):
        self.path.write_text(json.dumps(records))

    def test_bound_reconciliation_preserves_original_and_never_resends(self):
        result = self.bridge.reconcile('old-key', 'local/evidence.json')
        self.assertEqual(result['state'], 'rejected')
        self.assertEqual(result['rejection']['source'], 'official_cli_log')
        audit = self.bridge.db.execute('SELECT * FROM rejection_audit').fetchone()
        self.assertEqual(json.loads(audit['before_json']), self.original)
        self.assertEqual(audit['evidence_json'].encode(), self.path.read_bytes())
        self.assertEqual(audit['evidence_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(self.bridge.reconcile('old-key', 'local/evidence.json'), result)
        self.assertEqual(self.bridge.reconcile('old-key'), result)
        self.assertEqual(self.bridge.send('old-key', text=self.text)['state'], 'rejected')
        self.assertEqual(self.fake.sent, 0)
        self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM rejection_audit').fetchone()[0], 1)

    def test_wrong_key_target_length_and_unproven_errors_leave_unknown(self):
        variants = []
        for field, value in [('uuid', 'another-key'), ('receiverOpenDingTalkId', 'someone-else'), ('msgType', 'image')]:
            records = copy.deepcopy(self.records)
            args = json.loads(records[1]['arguments_summary']); args[field] = value
            records[1]['arguments_summary'] = json.dumps(args); variants.append(records)
        for field, value in [('reason', 'timeout'), ('server_error_code', 'INTERNAL_ERROR'),
                             ('errorMsg', self.records[2]['errorMsg'].replace('6220', '6008'))]:
            records = copy.deepcopy(self.records); records[2][field] = value; variants.append(records)
        records = copy.deepcopy(self.records); records[-1]['success'] = True; variants.append(records)
        variants.append(self.records[:-1])
        for records in variants:
            with self.subTest(records=variants.index(records)):
                self.save(records)
                with self.assertRaises(ValueError): self.bridge.reconcile('old-key', 'local/evidence.json')
                self.assertEqual(self.bridge.delivery('old-key')['state'], 'outcome_unknown')
                self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM rejection_audit').fetchone()[0], 0)
        self.assertEqual(self.fake.sent, 0)

    def test_interleaved_or_missing_execution_identity_is_rejected(self):
        records = copy.deepcopy(self.records)
        records.insert(2, {**records[0], 'time': '2026-11-11T22:46:25.15+08:00', 'execution_id': 'other'})
        self.save(records)
        with self.assertRaisesRegex(ValueError, 'Interleaved'): self.bridge.reconcile('old-key', 'local/evidence.json')
        records = copy.deepcopy(self.records); records[1].pop('execution_id'); self.save(records)
        with self.assertRaisesRegex(ValueError, 'execution'): self.bridge.reconcile('old-key', 'local/evidence.json')

    def test_task_id_or_matching_history_prevents_rejection_reconciliation(self):
        with self.bridge.db: self.bridge.db.execute('UPDATE deliveries SET task_id="known-task"')
        with self.assertRaises(ValueError): self.bridge.reconcile('old-key', 'local/evidence.json')
        with self.bridge.db:
            self.bridge.db.execute('UPDATE deliveries SET task_id=NULL')
            self.bridge.db.execute('INSERT INTO events(message_id,body) VALUES (?,?)', ('m', json.dumps({'content': self.text})))
        with self.assertRaisesRegex(ValueError, 'history'): self.bridge.reconcile('old-key', 'local/evidence.json')
        self.assertEqual(self.bridge.delivery('old-key')['state'], 'outcome_unknown')

    def test_evidence_must_stay_private_and_previous_audit_cannot_be_replaced(self):
        outside = self.root / 'outside.json'; outside.write_bytes(self.path.read_bytes())
        with self.assertRaises(ValueError): self.bridge.reconcile('old-key', 'outside.json')
        self.bridge.reconcile('old-key', 'local/evidence.json')
        self.path.write_text(self.path.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'different'): self.bridge.reconcile('old-key', 'local/evidence.json')

    def test_explicit_send_rejection_is_terminal_and_audited(self):
        original = self.fake.call
        def call(args):
            if '+messages-send' in args:
                self.fake.sent += 1
                raise DWSRequestRejected({'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR'})
            return original(args)
        self.fake.call = call
        receipt = self.bridge.send('new', text='synthetic')
        self.assertEqual(receipt['state'], 'rejected')
        self.assertEqual(receipt['rejection']['source'], 'official_error_response')
        self.assertEqual(self.bridge.send('new', text='synthetic')['state'], 'rejected')
        self.assertEqual(self.fake.sent, 1)

    def test_rejected_status_query_does_not_reclassify_accepted_send(self):
        original = self.fake.call
        def call(args):
            if '+messages-query-send-status' in args:
                raise DWSRequestRejected({'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR'})
            return original(args)
        self.fake.call = call
        receipt = self.bridge.send('new', text='synthetic')
        self.assertEqual(receipt['state'], 'outcome_unknown')
        self.assertEqual(receipt['task_id'], 'task')
        self.assertNotIn('rejection', receipt)

    def test_dws_classifies_only_explicit_server_invalid_parameter(self):
        for error, rejected in [({'reason': 'invalid_request', 'server_error_code': 'PARAM_ERROR'}, True),
                                ({'reason': 'timeout', 'server_error_code': 'PARAM_ERROR'}, False),
                                ({'reason': 'invalid_request', 'server_error_code': 'UNKNOWN'}, False)]:
            response = SimpleNamespace(returncode=1, stdout=json.dumps({'ok': False, 'error': error}), stderr='')
            with patch('dingtalk_bridge.core.run_dws', return_value=response):
                with self.assertRaises(BridgeError) as raised: DWS(self.root, self.cfg).call(['chat', '+messages-send'])
                self.assertEqual(isinstance(raised.exception, DWSRequestRejected), rejected)


if __name__ == '__main__':
    unittest.main()

import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('observation_snapshot',Path(__file__).resolve().parents[1]/'scripts/reconcile_observation_snapshot.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ObservationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.baseline={'routes':[{'accountId':'a','profile':'u:c','conversationId':'g'}],'cursors':[10]}
        self.event={'seq':15,'account_id':'a','conversation_id':'g','message_id':'m','content':'synthetic'}
        self.samples=[{'events':[{'route':0,'event':self.event}]}]
        self.ledgers=[{'routeIndex':0,'scope':['u:c','g'],'events':[copy.deepcopy(self.event)],
                       'deliveries':{'confirmed':3,'outcome_unknown':1,'failed':2}}]

    def test_exact_capture_keeps_failures_and_does_not_prove_window_cutoff(self):
        result=module.reconcile(self.baseline,self.samples,self.ledgers)
        self.assertTrue(result['capturedRangeReconciled']);self.assertFalse(result['historicalWindowCutoffProven'])
        self.assertEqual(result['routes'][0]['currentDeliveryStates'],{'confirmed':3,'outcome_unknown':1,'failed':2})
        self.assertEqual(result['routes'][0]['exactlyRetained'],1)

    def test_missing_mutated_wrong_scope_and_duplicate_rows_fail(self):
        for case in ('missing','mutated','wrong_scope','duplicate'):
            ledgers=copy.deepcopy(self.ledgers)
            if case=='missing':ledgers[0]['events']=[]
            if case=='mutated':ledgers[0]['events'][0]['content']='different'
            if case=='wrong_scope':ledgers[0]['scope']=['other:c','g']
            if case=='duplicate':ledgers[0]['events']*=2
            with self.subTest(case=case):self.assertFalse(module.reconcile(self.baseline,self.samples,ledgers)['capturedRangeReconciled'])

    def test_unobserved_row_inside_captured_sequence_range_is_detected(self):
        self.ledgers[0]['events'].append({**self.event,'seq':12,'message_id':'missing-from-observation'})
        result=module.reconcile(self.baseline,self.samples,self.ledgers)
        self.assertFalse(result['capturedRangeReconciled']);self.assertFalse(result['routes'][0]['sampledRangeExact'])

    def test_later_rows_are_separate_even_if_they_have_an_old_message_timestamp(self):
        self.ledgers[0]['events'].append({**self.event,'seq':99,'message_id':'late-ingestion','timestamp':1})
        result=module.reconcile(self.baseline,self.samples,self.ledgers)
        self.assertTrue(result['capturedRangeReconciled']);self.assertFalse(result['historicalWindowCutoffProven'])
        self.assertEqual(result['routes'][0]['persistedBeyondLastCapture'],1)

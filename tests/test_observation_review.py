import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('observation_review', Path(__file__).resolve().parents[1] / 'scripts/review_service_observations.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ObservationReviewTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {'at': 9, 'routes': [{'accountId': 'synthetic', 'conversationId': 'test-chat'}], 'cursors': [4]}
        self.samples = [{'observedAt': 10 + n * 30, 'events': [], 'health': {'poll_error': False, 'routes': [{'poll_error': None}]}} for n in range(2880)]
        self.status = {'startedAt': 10, 'updatedAt': 86410, 'elapsed_seconds': 86400, 'interval_seconds': 30,
                       'duration_seconds': 86400, 'samples': 2880, 'unavailable_samples': 0, 'new_events': 0,
                       'active': False, 'stop_reason': 'duration_reached'}

    def review(self): return module.review(self.baseline, self.status, self.samples, [{'maintenance': True}])

    def test_complete_24h_requires_actual_duration_and_terminal_reason(self):
        r = self.review(); self.assertTrue(r['evidence_valid']); self.assertTrue(r['observation_complete_24h'])
        self.assertTrue(r['zero_recorded_errors'])

    def test_active_partial_run_is_valid_but_incomplete(self):
        self.samples = self.samples[:900]
        self.status.update(samples=900, active=True, elapsed_seconds=27000, updatedAt=27010)
        self.status.pop('stop_reason')
        r = self.review(); self.assertTrue(r['evidence_valid']); self.assertFalse(r['observation_complete_24h'])

    def test_signal_stop_does_not_become_duration_completion(self):
        self.status['stop_reason'] = 'signal'; self.assertFalse(self.review()['observation_complete_24h'])

    def test_claimed_duration_with_missing_tail_fails_completion(self):
        self.samples = self.samples[:-20]; self.status['samples'] = len(self.samples)
        self.assertFalse(self.review()['observation_complete_24h'])

    def test_sample_count_mismatch_is_not_repaired(self):
        self.status['samples'] -= 1; self.assertFalse(self.review()['evidence_valid'])

    def test_gap_and_clock_jump_are_detected(self):
        del self.samples[100:110]; self.status['samples'] = len(self.samples)
        self.assertFalse(self.review()['checks']['sample_gaps_within_budget'])
        self.status['updatedAt'] += 1000; self.assertFalse(self.review()['checks']['wall_and_elapsed_consistent'])

    def test_maintenance_does_not_erase_unavailable_or_poll_errors(self):
        self.samples[5]['error'] = 'URLError'; self.status['unavailable_samples'] = 1
        self.samples[6]['health']['poll_error'] = True
        self.samples[6]['health']['routes'][0]['poll_error'] = 'synthetic'
        r = self.review(); self.assertTrue(r['observation_complete_24h']); self.assertFalse(r['zero_recorded_errors'])
        self.assertEqual((r['unavailable_samples'], r['poll_error_samples'], r['route_poll_error_occurrences']), (1, 1, 1))

    def test_duplicate_event_is_rejected_and_sequence_gaps_are_allowed(self):
        event = {'route': 0, 'event': {'seq': 900, 'message_id': 'synthetic-1', 'account_id': 'synthetic', 'conversation_id': 'test-chat'}}
        self.samples[0]['events'] = [event]; self.status['new_events'] = 1
        self.assertTrue(self.review()['evidence_valid'])
        duplicate = copy.deepcopy(event); duplicate['event']['seq'] = 901
        self.samples[1]['events'] = [duplicate]; self.status['new_events'] = 2
        self.assertFalse(self.review()['checks']['no_duplicate_message_ids_per_route'])

    def test_foreign_route_is_rejected(self):
        self.samples[0]['events'] = [{'route': 0, 'event': {'seq': 5, 'message_id': 'synthetic-1', 'account_id': 'foreign', 'conversation_id': 'test-chat'}}]
        self.status['new_events'] = 1; self.assertFalse(self.review()['evidence_valid'])

    def test_elapsed_below_24h_never_completes(self):
        self.status['elapsed_seconds'] = 86399.99
        self.assertFalse(self.review()['observation_complete_24h'])

    def test_frozen_ledger_requires_exact_content_not_just_counts(self):
        event = {'seq': 5, 'message_id': 'synthetic-1', 'account_id': 'synthetic', 'conversation_id': 'test-chat', 'content': 'expected'}
        self.samples[0]['events'] = [{'route': 0, 'event': event}]
        ledger = {'routes': [{'routeIndex': 0, 'account_id': 'synthetic', 'conversation_id': 'test-chat', 'events': [copy.deepcopy(event)]}]}
        self.assertTrue(module.reconcile_ledger(self.baseline, self.samples, ledger)['exact_match'])
        ledger['routes'][0]['events'][0]['content'] = 'changed'
        self.assertFalse(module.reconcile_ledger(self.baseline, self.samples, ledger)['exact_match'])
        ledger['routes'][0]['events'] = []
        self.assertFalse(module.reconcile_ledger(self.baseline, self.samples, ledger)['exact_match'])


if __name__ == '__main__': unittest.main()

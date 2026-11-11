#!/usr/bin/env python3
"""Review private observation files without contacting DingTalk or changing a run.

A complete observation is not a zero-error or unchanged-version stability pass.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def review(baseline, status, samples, maintenance):
    routes = baseline['routes']
    started = status['startedAt']; elapsed = status['elapsed_seconds']
    interval = status['interval_seconds']; duration = status['duration_seconds']
    # Capture performs health + one events GET per route, each with an 8s timeout.
    tail_budget = interval + 8 * (1 + len(routes)) + 5
    gap_budget = 2 * interval + 8 * (1 + len(routes)) + 5
    times = [s['observedAt'] for s in samples]
    gaps = [b - a for a, b in zip(times, times[1:])]
    unavailable = sum('error' in s for s in samples)
    poll_errors = sum(bool(s.get('health', {}).get('poll_error')) for s in samples)
    route_poll_errors = sum(sum(bool(r.get('poll_error')) for r in s.get('health', {}).get('routes', [])) for s in samples)
    received = [e for s in samples for e in s['events']]
    identities = set(); sequences = list(baseline['cursors']); ordered = True; bound = True; duplicates = 0
    for item in received:
        index, event = item['route'], item['event']
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(routes):
            bound = False; continue
        route = routes[index]
        bound &= event['account_id'] == route['accountId'] and event['conversation_id'] == route['conversationId']
        ordered &= isinstance(event['seq'], int) and event['seq'] > sequences[index]
        sequences[index] = event['seq']
        key = (index, event['message_id'])
        duplicates += key in identities; identities.add(key)
    checks = {
        'nonempty_samples': bool(samples),
        'sane_run_parameters': 10 <= duration <= 86400 and .2 <= interval <= 60 and elapsed >= 0,
        'baseline_before_start': baseline['at'] <= started,
        'sample_count_matches_status': status['samples'] == len(samples),
        'unavailable_count_matches_status': status['unavailable_samples'] == unavailable,
        'event_count_matches_status': status['new_events'] == len(received),
        'timestamps_finite_and_increasing': all(isinstance(t, (int, float)) and math.isfinite(t) for t in times) and all(g > 0 for g in gaps),
        'samples_within_run': bool(times) and started <= times[0] <= started + tail_budget and times[-1] <= status['updatedAt'],
        'wall_and_elapsed_consistent': abs(status['updatedAt'] - started - elapsed) <= tail_budget,
        'sample_gaps_within_budget': not gaps or max(gaps) <= gap_budget,
        'event_route_identity_matches_baseline': bool(routes) and bound,
        'event_sequences_increase': ordered,
        'no_duplicate_message_ids_per_route': duplicates == 0,
    }
    complete = (all(checks.values()) and duration >= 86400 and elapsed >= 86400
                and status['active'] is False and status.get('stop_reason') == 'duration_reached'
                and times[-1] >= started + duration - tail_budget)
    return {
        'scope': 'Recorded observation integrity/duration only; not UI acceptance or proof of no lost upstream messages',
        'checks': checks, 'evidence_valid': all(checks.values()), 'observation_complete_24h': complete,
        'zero_recorded_errors': unavailable == poll_errors == route_poll_errors == 0,
        'samples': len(samples), 'elapsed_hours': round(elapsed / 3600, 3),
        'observed_span_seconds': round(times[-1] - times[0], 3) if times else 0,
        'maximum_sample_gap_seconds': round(max(gaps, default=0), 3),
        'gap_budget_seconds': gap_budget, 'tail_budget_seconds': tail_budget,
        'unavailable_samples': unavailable, 'poll_error_samples': poll_errors,
        'route_poll_error_occurrences': route_poll_errors, 'new_events': len(received),
        'duplicate_event_count': duplicates, 'maintenance_records': len(maintenance),
        'active': status['active'], 'stop_reason': status.get('stop_reason'),
        'limits': ['Maintenance records are listed, never subtracted from error counts',
                   'Sparse samples can miss short outages; event sequence gaps do not prove message loss',
                   'Code changes/restarts require separate version/maintenance review',
                   'A completed 24h observation with errors is not a zero-error stability pass'],
    }


def load_review(folder):
    files = {name: (folder / name).read_bytes() for name in ('baseline.json', 'status.json', 'observations.ndjson')}
    maintenance = folder / 'maintenance.ndjson'
    if maintenance.exists(): files[maintenance.name] = maintenance.read_bytes()
    # A live capture may write a sample before replacing status. Never repair counts.
    if (folder / 'status.json').read_bytes() != files['status.json']:
        raise ValueError('Snapshot changed while reading; use a frozen copy')
    report = review(json.loads(files['baseline.json']), json.loads(files['status.json']),
                    [json.loads(line) for line in files['observations.ndjson'].splitlines()],
                    [json.loads(line) for line in files.get('maintenance.ndjson', b'').splitlines()])
    ledger_path = folder / 'ledger.json'
    if ledger_path.exists():
        files[ledger_path.name] = ledger_path.read_bytes()
        ledger = json.loads(files[ledger_path.name])
        samples = [json.loads(line) for line in files['observations.ndjson'].splitlines()]
        report['ledger_reconciliation'] = reconcile_ledger(json.loads(files['baseline.json']), samples, ledger)
        report['evidence_valid'] &= report['ledger_reconciliation']['exact_match']
        report['observation_complete_24h'] &= report['evidence_valid']
    report['sourceSha256'] = {n: hashlib.sha256(data).hexdigest() for n, data in files.items()}
    return report


def reconcile_ledger(baseline, samples, ledger):
    """Compare a contemporaneous frozen local ledger; no upstream loss inference."""
    counts = []; exact = len(ledger['routes']) == len(baseline['routes'])
    for index, route in enumerate(baseline['routes']):
        matching = [r for r in ledger['routes'] if r['routeIndex'] == index]
        captured = [item['event'] for sample in samples for item in sample['events'] if item['route'] == index]
        stored = matching[0]['events'] if len(matching) == 1 else []
        exact &= len(matching) == 1 and matching[0]['account_id'] == route['accountId'] and matching[0]['conversation_id'] == route['conversationId']
        exact &= stored == captured
        counts.append({'route_index': index, 'captured': len(captured), 'persisted_after_baseline': len(stored)})
    return {'exact_match': bool(exact), 'routes': counts,
            'scope': 'Exact frozen local event rows after baseline; not proof that upstream delivered every message'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    try:
        report = load_review(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'evidence_valid': False, 'error_type': type(error).__name__}))
        return 1
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output: args.output.write_text(text)
    print(text, end='')
    return 1 if not report['evidence_valid'] else 2 if args.require_complete and not report['observation_complete_24h'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

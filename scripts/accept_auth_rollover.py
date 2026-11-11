#!/usr/bin/env python3
"""Read-only audit of observed official token metadata rollover, never token values."""
import argparse
from datetime import datetime
import json

from accept_office_files import ROOT, digest, read


def audit():
    folder = ROOT / 'local/auth-rollover-20261112'
    samples = [json.loads(s) for s in (folder / 'samples.ndjson').read_text().splitlines()]
    rollover, after, frozen = (read(folder / n) for n in ('rollover.json', 'after.json', 'frozen.json'))
    first = samples[0]
    old_expiry = first['status']['expires_at']
    changed = [s for s in samples if s.get('status', {}).get('expires_at') != old_expiry]
    old_dt, new_dt = (datetime.fromisoformat(x) for x in (old_expiry, rollover['status']['expires_at']))
    at = datetime.fromisoformat(rollover['at'])
    checks = {
        'frozen_sample_file_intact': digest((folder / 'samples.ndjson').read_bytes()) == frozen['samplesSha256'],
        'collector_source_intact': digest((folder / 'observe.py').read_bytes()) == frozen['collectorSha256'],
        'baseline_still_valid': all(first['status'][k] is True for k in ('success', 'authenticated', 'token_valid', 'refresh_token_valid')),
        'one_changed_expiry_sample': changed == [rollover],
        'expiry_extended': new_dt > old_dt,
        'within_preexpiry_five_minute_window': 0 < (old_dt - at).total_seconds() <= 300,
        'rotated_status_valid': all(rollover['status'][k] is True for k in ('success', 'authenticated', 'token_valid', 'refresh_token_valid')),
        'after_status_same_valid_expiry': after['status']['expires_at'] == rollover['status']['expires_at'] and all(after['status'][k] is True for k in ('success', 'authenticated', 'token_valid', 'refresh_token_valid')),
        'health_healthy_at_and_after': all(s['health']['poll_error'] is False and all(r['poll_error'] is None for r in s['health']['routes']) for s in (rollover, after)),
        'sync_after_rotation_observation': all(r['last_sync']['complete'] is True and datetime.fromisoformat(r['last_sync']['at']).timestamp() > at.timestamp() for r in after['health']['routes']),
        'timer_poll_continued': after['health']['poll_scheduler']['timer_cycles'] > rollover['health']['poll_scheduler']['timer_cycles'],
        'collector_does_not_contain_token_values': all(set(s.get('status', {})) <= {'success','authenticated','refreshed','token_valid','refresh_token_valid','expires_at','refresh_expires_at','reason'} for s in samples),
        'no_auth_config_or_clock_mutation': frozen['credentialOrClockMutations'] == 0 and frozen['readonlyStatusOnly'] is True,
        'maintenance_collection_error_retained': sum('errorType' in s for s in samples) == frozen['collectionErrors'],
    }
    before = read(ROOT / 'local/quote-bridge-20261112/final.json')
    final = read(folder / 'final.json')
    checks['no_new_tasks_messages_or_deliveries'] = all(before['routes'][kind][table] == final['routes'][kind][table] for kind in ('group', 'direct') for table in ('jobs', 'outbox', 'deliveries', 'events', 'runtimeFiles'))
    checks['original_24h_observer_preserved'] = read(folder / 'observer-owner-check.json')['verified'] is True and all(before['observer'][key] == final['observer'][key] for key in ('pid', 'startedAt', 'duration_seconds'))
    late = read(folder / 'after-old-expiry.json')
    checks['after_old_expiry_capture_intact'] = digest((folder / 'after-old-expiry.json').read_bytes()) == frozen['afterOldExpirySha256']
    checks['after_old_expiry_valid_status'] = datetime.fromisoformat(late['at']) > old_dt and late['status']['expires_at'] == rollover['status']['expires_at'] and all(late['status'][k] is True for k in ('success', 'authenticated', 'token_valid', 'refresh_token_valid'))
    checks['both_routes_sync_beyond_old_expiry'] = late['health']['poll_error'] is False and all(r['poll_error'] is None and r['last_sync']['complete'] is True and datetime.fromisoformat(r['last_sync']['at']) > old_dt for r in late['health']['routes'])
    return {'date': '2026-11-12', 'checks': checks, 'samples': len(samples),
            'observedBeforeOldExpirySeconds': round((old_dt - at).total_seconds(), 3),
            'collectionErrors': frozen['collectionErrors'],
            'healthyPollErrorSamples': sum(s.get('health', {}).get('poll_error') is True for s in samples),
            'naturalPreexpiryRollover': True, 'expiredRefreshCredentialRecovery': False,
            'limits': ['Metadata expiry changed; no token values read or copied by collector',
                       'Official CLI runtime refresh observed indirectly; no exclusive attribution to a particular history request',
                       'No revoked/expired refresh token or reauthorization test',
                       'Planned deployment collection error retained; not uninterrupted uptime'],
            'ok': all(checks.values())}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true'); args = p.parse_args()
    result = audit()
    if args.write:
        (ROOT / 'evidence/2026-11-12/auth-rollover-ledger.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

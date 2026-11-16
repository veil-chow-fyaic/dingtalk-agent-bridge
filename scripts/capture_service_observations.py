#!/usr/bin/env python3
"""Bounded read-only service/event observation; private traces stay in local/."""
import argparse
import json
import os
from pathlib import Path
import signal
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from service_observation_evidence import (SCHEMA, safe_version_snapshot, seal,
                                         snapshot_routes, write_json, settle_cutoff, SETTLE_POLICY)

ROOT=Path(__file__).resolve().parents[1]

def capture(root, folder, routes, get, seconds, interval, stop, clock=time.time, monotonic=time.monotonic):
    """Only local HTTP reads and SQLite read transactions. No service lifecycle calls."""
    snapshots = snapshot_routes(root, routes)
    if any('error' in row for row in snapshots):
        write_json(folder / 'baseline-failed.json', {'snapshots': snapshots})
        raise ValueError('Baseline snapshot failed')
    cursors = [row['highSequence'] for row in snapshots]
    version = safe_version_snapshot(root)
    health = get('/v1/health')
    baseline_at = clock()
    started = monotonic(); wall = clock(); cut = wall + seconds
    baseline = {'schemaVersion': SCHEMA, 'at': baseline_at, 'cursors': list(cursors), 'routes': routes,
                'health': health, 'snapshots': snapshots, 'version': version, 'cutoffAt': cut,
                'capturePolicy': SETTLE_POLICY}
    write_json(folder / 'baseline.json', baseline)
    status = {'schemaVersion': SCHEMA, 'active': True, 'pid': os.getpid(), 'startedAt': wall,
              'cutoffAt': cut, 'duration_seconds': seconds, 'interval_seconds': interval,
              'samples': 0, 'unavailable_samples': 0, 'new_events': 0, 'elapsed_seconds': 0}

    def save_status():
        status.update(updatedAt=clock(), elapsed_seconds=monotonic() - started)
        write_json(folder / 'status.json', status)

    reason = 'exception'
    save_status()
    # Explicit empty maintenance log. Manager journal changes are independently
    # retained in every version record, so an empty file cannot erase restarts.
    with (folder / 'maintenance.ndjson').open('x') as out:
        out.flush(); os.fsync(out.fileno())
    try:
        with (folder / 'observations.ndjson').open('x') as out:
            while not stop.is_set() and monotonic() - started < seconds:
                sample = {'observedAt': clock(), 'events': []}
                try:
                    sample['health'] = get('/v1/health')
                    for index, route in enumerate(routes):
                        if stop.is_set() or monotonic() - started >= seconds:
                            raise TimeoutError('Observation deadline')
                        batch = get('/v1/events?' + urlencode({'account_id': route['accountId'],
                            'conversation_id': route['conversationId'], 'after': cursors[index], 'limit': 200}))
                        cursors[index] = batch['next_cursor']
                        sample['events'].extend({'route': index, 'event': e, 'firstObservedAt': clock()}
                                                for e in batch['events'])
                except Exception as exc:
                    status['unavailable_samples'] += 1; sample['error'] = type(exc).__name__
                sample['version'] = safe_version_snapshot(root)
                status['samples'] += 1; status['new_events'] += len(sample['events'])
                out.write(json.dumps(sample, ensure_ascii=False) + '\n'); out.flush(); os.fsync(out.fileno())
                save_status()
                stop.wait(min(interval, max(0, seconds - (monotonic() - started))))
        reason = 'signal' if stop.is_set() else 'duration_reached'
    except BaseException as exc:
        status['error'] = type(exc).__name__
        raise
    finally:
        # Capture even for signal/exception; reviewer will refuse completion.
        # SIGKILL leaves active status or an absent seal; never resume/repair it.
        try:
            rows, attempts = settle_cutoff(root, routes, baseline['cursors'], cut, stop,
                                          snapshot=snapshot_routes, clock=clock) if reason == 'duration_reached' else (
                                              snapshot_routes(root, routes, baseline['cursors']), [])
            ledger = {'schemaVersion': SCHEMA, 'cutoffAt': cut,
                      'routes': rows, 'coverageAttempts': attempts,
                      'version': safe_version_snapshot(root)}
            write_json(folder / 'ledger.json', ledger)
            status.update(active=False, stop_reason=reason)
            save_status()
            seal(folder)
        except BaseException as exc:
            status.update(active=False, stop_reason='finalization_failed', finalization_error=type(exc).__name__)
            save_status()
            raise
    return status


def main():
    os.umask(0o077);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=int,default=600);p.add_argument('--run-id',required=True)
    p.add_argument('--interval',type=float,default=1,help='Sample period in seconds, 0.2..60; use 30 for a 24h watch')
    args=p.parse_args()
    if not 10<=args.seconds<=86400 or not .2<=args.interval<=60 or not args.run_id.replace('-','').isalnum():p.error('Invalid duration/run ID/interval')
    folder=ROOT/'local/service-observations'/args.run_id;folder.mkdir(parents=True,exist_ok=False)
    routes=json.loads((ROOT/'local/service-config.json').read_text())['routes']
    token=(ROOT/'local/runtime/http-token').read_text().strip()
    stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    def get(path):
        request=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token})
        with urlopen(request,timeout=8) as response:return json.load(response)
    print(json.dumps(capture(ROOT, folder, routes, get, args.seconds, args.interval, stop)))

if __name__=='__main__':main()

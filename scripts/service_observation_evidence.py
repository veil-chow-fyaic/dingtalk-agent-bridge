"""Private, read-only cutoff evidence. Never imports a live Bridge or repairs a run."""
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge.routing import route_configs
from dingtalk_bridge.service_manager import Manager

SCHEMA = 2
# These are evidence tolerances, not an assertion of an instantaneous snapshot.
CUTOFF_START_BUDGET = 5
CUTOFF_END_BUDGET = 15
SEALED_FILES = ('baseline.json', 'status.json', 'observations.ndjson',
                'ledger.json', 'maintenance.ndjson')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as output:
        os.chmod(temporary, 0o600)
        json.dump(value, output, ensure_ascii=False, allow_nan=False)
        output.write('\n'); output.flush(); os.fsync(output.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def route_snapshot(root, route, state, index, after, clock=time.time):
    directory = root / 'local/runtime'
    if state:
        directory = directory / 'routes' / state
    path = directory / 'bridge.sqlite3'
    started = clock()
    # BEGIN alone does not acquire a snapshot; the first meta SELECT does.
    # All rows, the upper sequence, and watermark come from that same snapshot.
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        deadline = time.monotonic() + 3
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        db.execute('BEGIN')
        meta = dict(db.execute('SELECT key,value FROM meta'))
        acquired = clock()
        high = db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]
        events = [] if after is None else [dict(json.loads(body), seq=seq) for seq, body in db.execute(
            'SELECT seq,body FROM events WHERE seq>? AND seq<=? ORDER BY seq', (after, high))]
        states = dict(db.execute('SELECT state,count(*) FROM deliveries GROUP BY state'))
        db.rollback()
    return {'routeIndex': index, 'account_id': route['accountId'],
            'conversation_id': route['conversationId'], 'scope': json.loads(meta['scope']),
            'snapshotStartedAt': started, 'snapshotAcquiredAt': acquired, 'snapshotEndedAt': clock(),
            'after': after, 'highSequence': high, 'events': events, 'deliveries': states,
            'watermark': meta.get('watermark'), 'history_window': meta.get('history_window')}


def snapshot_routes(root, routes, cursors=None, clock=time.time):
    rows = []
    for index, (route, state) in enumerate(route_configs({'routes': routes})):
        try:
            rows.append(route_snapshot(root, route, state, index,
                                       None if cursors is None else cursors[index], clock))
        except Exception as exc:
            rows.append({'routeIndex': index, 'error': type(exc).__name__, 'failedAt': clock()})
    return rows


def version_snapshot(root):
    """Source/config fingerprints and owned process records, not memory attestation.

    The existing manager does not record source hashes at process load. Keep
    that absence explicit; matching today's disk cannot establish loaded code.
    """
    root = root.resolve()
    started = time.time()
    manager = Manager(root)
    state = manager.read_state()
    sources = {str(p.relative_to(root)): digest(p.read_bytes())
               for p in sorted((root / 'dingtalk_bridge').glob('*.py'))}
    collectors = {name: digest((root / 'scripts' / name).read_bytes()) for name in (
        'capture_service_observations.py', 'service_observation_evidence.py', 'review_service_observations.py')}
    config_paths = {root / 'local/service-config.json'}
    config_paths.update(Path(c['config']) for c in state['components'])
    configs = {}
    for path in sorted(config_paths):
        path = path.resolve()
        # Hash configuration only; never open arbitrary paths named in a record.
        if not path.is_relative_to((root / 'local').resolve()) or path.suffix != '.json':
            raise ValueError('Unexpected managed configuration path')
        configs[str(path.relative_to(root))] = digest(path.read_bytes())
    components = [{'name': c['name'], 'pid': c['pid'], 'identity': c['identity'],
                   'startedAt': c['startedAt'], 'configSha256': c.get('configSha256'),
                   'configMatches': c.get('configSha256') == configs[str(Path(c['config']).resolve().relative_to(root))],
                   'status': manager.component_status(c)} for c in state['components']]
    journal = root / 'local/runtime/manager-events.ndjson'
    journal_data = journal.read_bytes() if journal.exists() else b''
    return {'startedAt': started, 'endedAt': time.time(), 'sourceSha256': sources,
            'collectorSha256': collectors, 'configSha256': configs, 'components': components,
            'managerJournal': journal_data.decode(), 'managerJournalSha256': digest(journal_data),
            'loadedSourceProven': False,
            'limit': 'Disk fingerprints and process identity only; no startup source attestation'}


def safe_version_snapshot(root):
    try:
        return version_snapshot(root)
    except Exception as exc:
        return {'error': type(exc).__name__, 'at': time.time(), 'loadedSourceProven': False}


def seal(folder):
    write_json(folder / 'completion.json', {'schemaVersion': SCHEMA,
        'sha256': {n: digest((folder / n).read_bytes()) for n in SEALED_FILES}})


def review_cutoff(baseline, status, samples, ledger, maintenance):
    """Fail closed on missing/late/mutated evidence without changing old v1 runs."""
    cut = baseline['cutoffAt']
    checks = {
        'fixed_cut': cut == status['startedAt'] + status['duration_seconds'] == status['cutoffAt'],
        'terminal_duration': status['active'] is False and status.get('stop_reason') == 'duration_reached',
        'ledger_bound': ledger['schemaVersion'] == SCHEMA and ledger['cutoffAt'] == cut,
        'route_count': len(ledger['routes']) == len(baseline['routes']),
        'baseline_route_count': len(baseline['snapshots']) == len(baseline['routes']),
    }
    tails = []
    for index, route in enumerate(baseline['routes']):
        matches = [r for r in ledger['routes'] if r['routeIndex'] == index]
        starts = [r for r in baseline['snapshots'] if r['routeIndex'] == index]
        prefix = 'route_' + str(index) + '_'
        row = matches[0] if len(matches) == 1 else {}
        start = starts[0] if len(starts) == 1 else {}
        checks[prefix + 'captured'] = bool(row) and 'error' not in row and bool(start) and 'error' not in start
        if not checks[prefix + 'captured']:
            continue
        base = baseline['cursors'][index]
        checks[prefix + 'identity'] = all(
            r['scope'] == [route['profile'], route['conversationId']]
            and r['account_id'] == route['accountId'] and r['conversation_id'] == route['conversationId']
            for r in (start, row))
        checks[prefix + 'baseline'] = (start['highSequence'] == base and start['after'] is None
            and start['snapshotStartedAt'] <= start['snapshotAcquiredAt'] <= start['snapshotEndedAt'] <= baseline['at'] <= status['startedAt'])
        checks[prefix + 'timely'] = (cut <= row['snapshotStartedAt'] <= cut + CUTOFF_START_BUDGET
            and row['snapshotStartedAt'] <= row['snapshotAcquiredAt'] <= row['snapshotEndedAt'] <= cut + CUTOFF_END_BUDGET)
        try:
            watermark = datetime.fromisoformat(row['watermark'])
            covered = watermark.tzinfo is not None and watermark.timestamp() >= cut
        except (TypeError, ValueError):
            covered = False
        checks[prefix + 'coverage'] = covered and row['history_window'] is None
        stored = row['events']
        captured = [i['event'] for s in samples for i in s['events'] if i['route'] == index]
        seqs = [e['seq'] for e in stored]
        last = max((e['seq'] for e in captured), default=base)
        checks[prefix + 'sequence_bounds'] = (row['after'] == base and row['highSequence'] >= base
            and all(type(n) is int and base < n <= row['highSequence'] for n in seqs)
            and seqs == sorted(set(seqs))
            and (not seqs and row['highSequence'] == base or bool(seqs) and seqs[-1] == row['highSequence']))
        checks[prefix + 'event_identity'] = all(e['account_id'] == route['accountId']
            and e['conversation_id'] == route['conversationId'] for e in stored)
        checks[prefix + 'sampled_range_exact'] = [e for e in stored if e['seq'] <= last] == captured
        tails.append({'routeIndex': index, 'ledgerOnlyTailEvents': sum(e['seq'] > last for e in stored)})
    versions = [baseline['version'], *[s['version'] for s in samples], ledger['version']]
    first = versions[0]
    checks['version_records_present'] = all('error' not in v for v in versions)
    if checks['version_records_present']:
        checks['source_and_config_unchanged'] = bool(first['sourceSha256']) and all(
            v['sourceSha256'] == first['sourceSha256'] and v['configSha256'] == first['configSha256']
            and v['collectorSha256'] == first['collectorSha256'] for v in versions)
        checks['owned_processes_unchanged'] = bool(first['components']) and all(
            v['components'] == first['components'] and all(c['status'] == 'running' and c['configMatches'] for c in v['components'])
            for v in versions)
        checks['no_recorded_maintenance'] = not maintenance and all(
            v['managerJournal'] == first['managerJournal'] and digest(v['managerJournal'].encode()) == v['managerJournalSha256']
            for v in versions)
    return {'checks': checks, 'cutoff_evidence_valid': all(checks.values()), 'routes': tails,
            # No existing producer can attest loaded modules. Do not trust an input boolean.
            'uniform_loaded_version_proven': False, 'natural_refresh_proven': False,
            'limits': ['Per-route SQLite snapshots, not a shared atomic snapshot or exact instant at cutoff',
                       'Ledger-only tail rows were not observed by HTTP and are counted separately',
                       'Source/config fingerprints are sampled disk evidence, not loaded-code attestation',
                       'Seals detect changed/missing artifacts, not malicious rewriting of all evidence',
                       'Maintenance/errors/late snapshots are never forgiven; no upstream-loss guarantee']}

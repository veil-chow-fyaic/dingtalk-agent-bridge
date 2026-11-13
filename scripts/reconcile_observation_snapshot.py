#!/usr/bin/env python3
"""Compare captured events to a later read-only SQLite snapshot, never repair it.

The event schema has no ingestion timestamp. Rows beyond the captured range
cannot establish what was already persisted at the historical window cutoff.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge.routing import route_configs


def reconcile(baseline,samples,ledgers):
    reports=[];valid=len(ledgers)==len(baseline['routes'])
    for index,route in enumerate(baseline['routes']):
        matches=[x for x in ledgers if x['routeIndex']==index]
        captured=[x['event'] for sample in samples for x in sample['events'] if x['route']==index]
        ledger=matches[0] if len(matches)==1 else {'events':[],'scope':None,'deliveries':{}}
        scoped=ledger['scope']==[route['profile'],route['conversationId']]
        stored=ledger['events'];by_seq={x['seq']:x for x in stored}
        unique=len(by_seq)==len(stored) and len({x['seq'] for x in captured})==len(captured)
        bound=all(x['account_id']==route['accountId'] and x['conversation_id']==route['conversationId']
                  for x in captured+stored)
        correct=sum(by_seq.get(x['seq'])==x for x in captured)
        base=baseline['cursors'][index];last=max((x['seq'] for x in captured),default=base)
        observed_range=[x for x in stored if base<x['seq']<=last]
        exact=sorted(captured,key=lambda x:x['seq'])==sorted(observed_range,key=lambda x:x['seq'])
        ok=scoped and unique and bound and correct==len(captured) and exact
        valid &= ok
        reports.append({'routeIndex':index,'scopeMatches':scoped,'identityBound':bound,'uniqueSequences':unique,
                        'captured':len(captured),'exactlyRetained':correct,'sampledRangeExact':exact,
                        'persistedBeyondLastCapture':sum(x['seq']>last for x in stored),
                        'currentDeliveryStates':ledger['deliveries'],'ok':bool(ok)})
    valid &= all(type(x['route']) is int and 0<=x['route']<len(baseline['routes'])
                 for sample in samples for x in sample['events'])
    return {'capturedRangeReconciled':bool(valid),'routes':reports,'historicalWindowCutoffProven':False,
            'limits':['Later SQLite snapshot; no claim of a contemporaneous end-of-window snapshot',
                      'No ingestion timestamp: additional rows cannot be assigned to historical cutoff',
                      'Preserved captured rows do not prove that upstream supplied every message',
                      'Delivery state counts are current and include historical failures/unknowns unchanged']}


def load_snapshot(root,folder):
    names=('baseline.json','status.json','observations.ndjson','maintenance.ndjson')
    originals={n:(folder/n).read_bytes() for n in names}
    baseline=json.loads(originals['baseline.json']);samples=[json.loads(x) for x in originals['observations.ndjson'].splitlines()]
    ledgers=[];started=time.time()
    for index,(route,state) in enumerate(route_configs({'routes':baseline['routes']})):
        directory=root/'local/runtime'
        if state:directory=directory/'routes'/state
        path=directory/'bridge.sqlite3'
        # No Bridge/Hub constructor, no HTTP, no CLI, no write connection.
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.execute('BEGIN')
            scope=json.loads(db.execute('SELECT value FROM meta WHERE key="scope"').fetchone()[0])
            events=[{'seq':seq,**json.loads(body)} for seq,body in db.execute('SELECT seq,body FROM events ORDER BY seq')]
            states=dict(db.execute('SELECT state,count(*) FROM deliveries GROUP BY state'))
        ledgers.append({'routeIndex':index,'scope':scope,'events':events,'deliveries':states})
    report=reconcile(baseline,samples,ledgers)
    maintenance=[json.loads(x) for x in originals['maintenance.ndjson'].splitlines()]
    version_keys={'codeSha256','gatewaySha256','coreSha256','code','runtimeCommit'}
    report.update(snapshotStartedAt=started,snapshotEndedAt=time.time(),
                  maintenanceRecords=len(maintenance),
                  maintenanceWithVersionMetadata=sum(bool(set(x)&version_keys) for x in maintenance),
                  uniformLoadedVersionCoverageProven=False,
                  originalFilesUnchanged=all((folder/n).read_bytes()==data for n,data in originals.items()),
                  sourceSha256={n:hashlib.sha256(data).hexdigest() for n,data in originals.items()})
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output and args.output.resolve().is_relative_to(args.run_dir.resolve()):
        parser.error('Write the review outside the preserved observation directory')
    report=load_snapshot(args.root.resolve(),args.run_dir.resolve())
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')
    return 0 if report['capturedRangeReconciled'] and report['originalFilesUnchanged'] else 1


if __name__=='__main__':raise SystemExit(main())

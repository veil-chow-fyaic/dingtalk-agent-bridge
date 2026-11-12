#!/usr/bin/env python3
"""Read-only E098 ledger/artifact audit. UI observations are recorded separately."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def audit():
    folder=ROOT/'local/aic-media-20261112'
    labels=['[AIC-E098-JPEG]','[AIC-E098-AV]','[AIC-E098-AV-DELIVERY]']
    matches=[]
    for path in (ROOT/'local/agents').glob('*/tasks.sqlite3'):
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            rows=[dict(r) for r in db.execute('SELECT * FROM jobs')
                  if any(label in r['command'] for label in labels)]
            if rows:matches.append((path,rows))
    assert len(matches)==1
    path,rows=matches[0];base=path.parent
    jobs={label:[r for r in rows if label in r['command']] for label in labels}
    assert all(len(v)==1 for v in jobs.values()) and len(rows)==3
    jpeg,failed,delivery=[jobs[x][0] for x in labels]
    checks={'one_job_per_explicit_command':True,
            'original_av_failure_preserved':failed['state']=='failed' and failed['error']=='JSONDecodeError' and failed['result'] is None,
            'jpeg_and_readonly_delivery_completed':jpeg['state']==delivery['state']=='completed'}
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        outbox={r['id']:[dict(x) for x in db.execute('SELECT * FROM outbox WHERE job_id=?',(r['id'],))] for r in rows}
    checks['ten_original_receipts_confirmed']=sum(map(len,outbox.values()))==10 and all(x['state']=='confirmed' for v in outbox.values() for x in v)
    checks['failed_task_dispatched_no_artifacts']=len(outbox[failed['id']])==2 and all(set(json.loads(x['payload']))=={'text'} for x in outbox[failed['id']])
    evidence=[]
    for job in (jpeg,delivery):
        result=json.loads(job['result'])
        for artifact in result['artifacts']:
            staged=ROOT/artifact['file']
            downloaded=folder/'downloads'/('aic-e098-rotated.jpg.png' if staged.suffix=='.jpg' else staged.name)
            evidence.append({'name':downloaded.name,'bytes':downloaded.stat().st_size,
                             'sha256':sha(downloaded),'matchesStaged':sha(downloaded)==sha(staged)==artifact['sha256']})
    checks['four_client_downloads_match_staged']=len(evidence)==4 and all(x['matchesStaged'] for x in evidence)
    checks['jpeg_encoding_preserved']=(folder/'downloads/aic-e098-rotated.jpg.png').read_bytes().startswith(b'\xff\xd8\xff')
    for suffix,job in [('jpg',jpeg),('wav',failed),('mp4',failed)]:
        original=folder/'input'/('aic-e098-source.'+suffix)
        inputs=list((base/'workspaces/0/inputs'/job['id']).glob('*.'+suffix))
        checks[suffix+'_input_exact']=len(inputs)==1 and sha(original)==sha(inputs[0])
        if suffix!='jpg':
            checks[suffix+'_returned_original']=sha(original)==sha(folder/'downloads'/('0-aic-e098-return.wav' if suffix=='wav' else '1-aic-e098-return.mp4'))
    calls={}
    for job in rows:
        events=[json.loads(x) for x in (base/'runs'/job['id']/'events.jsonl').read_text().splitlines()]
        calls[job['id']]=[t['function'] for e in events if e.get('role')=='assistant' for t in e.get('tool_calls',[])]
    jpeg_calls=calls[jpeg['id']];av_calls=calls[failed['id']];delivery_calls=calls[delivery['id']]
    checks['jpeg_actual_media_read_and_pillow']=any(t['name']=='ReadMediaFile' for t in jpeg_calls) and any('rotate(-90' in t['arguments'] for t in jpeg_calls)
    checks['av_actual_wave_and_ffprobe']=any('import wave' in t['arguments'] and 'ffprobe -v' in t['arguments'] for t in av_calls)
    checks['delivery_only_readonly_hash_tool']=len(delivery_calls)==1 and delivery_calls[0]['name']=='Bash' and 'hashlib' in delivery_calls[0]['arguments'] and not any(x in delivery_calls[0]['arguments'] for x in ('copyfile','write_text','ffprobe','import wave'))
    baseline=json.loads((folder/'before-config-digests.json').read_text())
    checks['active_config_bytes_unchanged']=all(sha(ROOT/'local'/name)==digest for name,digest in baseline.items())
    return {'evidence':'E098','date':'2026-11-12','ok':all(checks.values()),'checks':checks,
            'downloads':evidence,'jobStates':['completed','failed','completed'],
            'jpegModelBashCalls':sum(t['name']=='Bash' for t in jpeg_calls),
            'uiScope':'Manual native UI observations in docs/103; this audit does not operate UI or DWS.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report');args=parser.parse_args()
    result=audit();text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.report:Path(args.report).write_text(text)
    print(text);raise SystemExit(0 if result['ok'] else 1)

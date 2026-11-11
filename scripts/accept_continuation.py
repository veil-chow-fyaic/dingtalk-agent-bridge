#!/usr/bin/env python3
"""Read-only live check of the existing solo route after migration; never sends or subscribes."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]


def main():
    token=(ROOT/'local/runtime/http-token').read_text().strip()
    def api(path):
        req=Request('http://127.0.0.1:18768'+path,headers={'Authorization':'Bearer '+token})
        with urlopen(req,timeout=40) as r:return json.load(r)
    config=json.loads((ROOT/'local/service-config.json').read_text())
    assert len(config['routes'])==1 and config['routes'][0]['stateStorage']=='legacy'
    routes=api('/v1/conversations')['conversations'];assert len(routes)==1
    db=sqlite3.connect((ROOT/'local/runtime/bridge.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:ledger={table:[list(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY 1')] for table in ('events','deliveries')}
    finally:db.close()
    baseline=ROOT/'local/continuation-20261111/before-ledger.json'
    assert baseline.exists(),'Requires the original private migration baseline; do not fabricate one'
    assert ledger==json.loads(baseline.read_text())
    batch=api('/v1/events?after=0&limit=200');assert len(batch['events'])==18
    cursor=batch['next_cursor'];start=time.monotonic()
    resumed=api('/v1/events?after='+str(cursor)+'&wait_seconds=1');elapsed=time.monotonic()-start
    assert resumed['events']==[] and resumed['next_cursor']==cursor and elapsed>=.9
    discovery=api('/v1/discovery');assert discovery['routes_changed'] is False
    assert sum(x['configured'] for x in discovery['conversations'])==1
    command=[sys.executable,'-m','dingtalk_bridge.consume','--name','shadow','--follow','--max-batches','1','--wait-seconds','1']
    consumer=json.loads(subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True,timeout=40).stdout)
    assert consumer['fetched']==0 and consumer['messages']==18 and consumer['readyForRuntime']==0
    assert consumer['mediaParts']==13 and consumer['selfFiltered']==18 and consumer['withIssues']==0
    result={'date':'2026-11-11','live_scope':'existing single-person group','schema_migration':'v1 to v2 preserving legacy state',
        'events':18,'deliveries':len(ledger['deliveries']),'ledger_identical':True,'route_count':1,
        'long_poll_timeout_seconds':round(elapsed,3),'cursor_unchanged':True,'discovery_count':len(discovery['conversations']),
        'discovery_complete':discovery['complete'],'new_routes_activated':0,'new_messages_sent':0,'office_writes':0,
        'consumer_messages':consumer['messages'],'consumer_fetched_after_restart':consumer['fetched'],
        'consumer_media_parts':consumer['mediaParts'],'consumer_self_filtered':consumer['selfFiltered'],'consumer_ready':consumer['readyForRuntime']}
    (ROOT/'evidence/2026-11-11/continuation-acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

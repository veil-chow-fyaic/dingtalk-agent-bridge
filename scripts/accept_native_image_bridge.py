#!/usr/bin/env python3
"""Read-only audit: native bridge PNG and a real Kimi-generated PNG. Never sends."""
import argparse
import json
import sqlite3
import struct
import zlib

from accept_office_files import ROOT, read, digest
from dingtalk_bridge.routing import route_configs


def rows(path, query, parameters=()):
    with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute(query,parameters)]


def same_file(path, original):
    return path.is_file() and path.read_bytes() == original


def audit():
    folder = ROOT / 'local/native-image-bridge-20261111'
    before = read(folder / 'before-ledgers.json')
    route_list = list(route_configs(read(ROOT / 'local/service-config.json')))
    checks = {}
    for cfg, state in route_list:
        db = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
        current = {r['key']:list(r.values()) for r in rows(db, 'SELECT * FROM deliveries ORDER BY key')}
        original = before[cfg['conversationType']]['deliveries']
        checks[cfg['conversationType']+'_old_deliveries_unchanged'] = all(current.get(r[0]) == r for r in original)
    cfg, state = next((c,s) for c,s in route_list if c['conversationType']=='direct')
    db = ROOT / 'local/runtime/routes' / state / 'bridge.sqlite3'
    intent = read(folder / 'direct-intent.json')['request']
    receipt = read(folder / 'direct-reconciled.json')
    deliveries = rows(db, 'SELECT * FROM deliveries WHERE key=?', (intent['idempotency_key'],))
    uploads = rows(db, 'SELECT * FROM image_uploads WHERE key=?', (intent['idempotency_key'],))
    events = [json.loads(r['body']) for r in rows(db, 'SELECT body FROM events WHERE message_id=?', (receipt['message_id'],))]
    original = (ROOT / intent['image']).read_bytes()
    resources = read(folder / 'direct-resources.json').get('downloads', [])
    checks.update(
        intent_bound_to_route=intent['account_id']==cfg['accountId'] and intent['conversation_id']==cfg['group'],
        confirmed_native_delivery=len(deliveries)==1 and deliveries[0]['state']=='confirmed' and receipt.get('image_delivery')=='native',
        durable_upload_media=len(uploads)==1 and uploads[0]['state']=='uploaded' and uploads[0]['media_id'].startswith('$'),
        one_self_history_event=len(events)==1 and events[0]['from_self'] is True and events[0]['sender_id']==cfg['selfSenderId'],
        observed_media_matches_upload=len(events)==1 and any(r.get('resourceId')==uploads[0]['media_id'] for r in events[0]['attachments']),
        original_resources_intact=bool(resources) and all(same_file(ROOT/r['localPath'],original) for r in resources),
        client_download_intact=same_file(folder/'direct-received.png', original),
    )
    scope = json.dumps([cfg['accountId'],cfg['profile'],cfg['group'],'direct'])
    agent_db = ROOT / 'local/agents' / digest(scope.encode())[:24] / 'tasks.sqlite3'
    jobs = rows(agent_db, 'SELECT * FROM jobs ORDER BY id')
    outbox = rows(agent_db, 'SELECT * FROM outbox ORDER BY key')
    old = read(folder/'direct-gateway-before.json')
    checks['old_jobs_unchanged'] = all({r['id']:list(r.values()) for r in jobs}.get(r[0])==r for r in old['jobs'])
    checks['old_agent_deliveries_unchanged'] = all({r['key']:list(r.values()) for r in outbox}.get(r[0])==r for r in old['outbox'])
    checks['fixture_reply_did_not_trigger_task'] = not any(json.loads(j['model'])['id']==receipt['message_id'] for j in jobs)
    tasks = [r for r in jobs if 'DAB-NATIVE-RESULT-20261111-DM' in r['command']]
    checks['one_completed_real_task'] = len(tasks)==1 and tasks[0]['state']=='completed'
    result = None
    if checks['one_completed_real_task']:
        task = tasks[0]
        task_outbox = [r for r in outbox if r['job_id']==task['id']]
        images = [r for r in task_outbox if 'image' in json.loads(r['payload'])]
        checks['task_all_three_replies_confirmed'] = len(task_outbox)==3 and all(r['state']=='confirmed' for r in task_outbox)
        checks['task_one_native_image'] = len(images)==1
        if len(images)==1:
            image_receipt=json.loads(images[0]['receipt'])
            generated_events=[json.loads(r['body']) for r in rows(db,'SELECT body FROM events WHERE message_id=?',(image_receipt['message_id'],))]
            checks['generated_reply_identity'] = len(generated_events)==1 and generated_events[0]['sender_id']==cfg['selfSenderId'] and generated_events[0]['from_self'] is True
            checks['generated_reply_did_not_trigger_task'] = not any(json.loads(j['model'])['id']==image_receipt['message_id'] for j in jobs)
            artifact = ROOT / json.loads(images[0]['payload'])['image']
            data = artifact.read_bytes()
            width,height = struct.unpack('>II',data[16:24])
            chunks=[]; offset=8
            while offset+12 <= len(data):
                length=struct.unpack('>I',data[offset:offset+4])[0]
                if data[offset+4:offset+8]==b'IDAT':chunks.append(data[offset+8:offset+8+length])
                offset+=length+12
            checks['generated_dimensions'] = (width,height)==(96,64)
            checks['generated_pixels'] = data[25]==2 and zlib.decompress(b''.join(chunks))==(b'\0'+bytes([0,100,200])*96)*64
            checks['task_client_download_intact'] = same_file(folder/'task-received.png', data)
            result={'bytes':len(data),'sha256':digest(data),'dimensions':[width,height]}
    build = read(ROOT/'local/bin/dws-image-upload-v1.0.67/dws-image-upload.build.json')
    checks['installed_companion_matches_build'] = digest((ROOT/cfg['imageUploadBinary']).read_bytes())==build['binarySha256']
    checks['addon_matches_build'] = digest((ROOT/'integrations/dws_image_upload/bridge_image_upload.go').read_bytes())==build['addonSha256']
    return {'date':'2026-11-11','scope':'Direct chat native image transport plus real runtime output; UI observations are separate',
            'fixture':{'bytes':len(original),'sha256':digest(original)},'generated':result,
            'group':'not_sent_pending_membership_scope_confirmation',
            'checks':checks,'ok':all(checks.values())}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args()
    report=audit()
    if a.write_evidence:
        (ROOT/'evidence/2026-11-11/native-image-bridge-ledger.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));raise SystemExit(0 if report['ok'] else 1)

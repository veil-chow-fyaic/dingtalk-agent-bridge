#!/usr/bin/env python3
"""Explicit scoped media send; durable intent prevents accidental repeated probes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CASES = {f'{route}-{kind}': (route, field, filename)
         for route in ('group', 'direct')
         for kind, field, filename in (
             ('png', 'image', 'dab-image-001.png'),
             ('pdf', 'file', 'dab-document-001.pdf'),
             ('docx', 'file', 'dab-office-001.docx'),
             ('xlsx', 'file', 'dab-office-001.xlsx'),
             ('zip', 'file', 'dab-archive-001.zip'))}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=CASES)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--reconcile', action='store_true')
    args = parser.parse_args()
    kind, field, filename = CASES[args.case]
    routes = json.loads((ROOT/'local/service-config.json').read_text())['routes']
    matches = [r for r in routes if r['conversationType'] == kind]
    if len(matches) != 1:
        parser.error('Probe requires exactly one route of the selected type')
    route = matches[0]
    selector = {'account_id': route['accountId'], 'conversation_id': route['conversationId']}
    payload = {**selector, 'idempotency_key': 'DAB-MATRIX-20261111-'+args.case,
               field: 'fixtures/'+filename}
    fingerprint = hashlib.sha256(json.dumps([route['profile'], payload,
        hashlib.sha256((ROOT/payload[field]).read_bytes()).hexdigest()], sort_keys=True).encode()).hexdigest()
    directory = ROOT/'local/probes/media-matrix-20261111'
    directory.mkdir(parents=True, exist_ok=True)
    record = directory/(args.case+'.json')
    token = (ROOT/'local/runtime/http-token').read_text().strip()

    def call(path, body=None):
        request = Request('http://127.0.0.1:18768'+path,
            headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'},
            data=None if body is None else json.dumps(body).encode())
        with urlopen(request, timeout=120) as response:
            return json.load(response)

    if record.exists():
        saved = json.loads(record.read_text())
        if saved['fingerprint'] != fingerprint:
            raise RuntimeError('Probe scope/content changed; refusing replay')
        result = call('/v1/reconcile', {**selector, 'idempotency_key': payload['idempotency_key']}) if args.reconcile else call(
            '/v1/deliveries/'+payload['idempotency_key']+'?'+urlencode(selector))
    elif args.reconcile:
        parser.error('No durable intent exists')
    elif args.execute:
        with record.open('x') as out:
            json.dump({'fingerprint': fingerprint, 'state': 'started', 'payload': payload}, out)
        result = call('/v1/send', payload)
    else:
        print(json.dumps({'case': args.case, 'action': 'preview', 'file': payload[field]}))
        return
    record.write_text(json.dumps({'fingerprint': fingerprint, 'receipt': result, 'payload': payload}))
    print(json.dumps({'case': args.case, 'state': result['state'], 'key': result['key']}))


if __name__ == '__main__':
    main()

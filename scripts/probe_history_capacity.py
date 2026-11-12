#!/usr/bin/env python3
"""Synthetic backlog probe. No official binary, credentials, HTTP or native UI.

Exit 2 means some synthetic messages remain unreachable after bounded polls.
This is an unresolved-regression probe, not a passing acceptance certificate.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge.core import Bridge


CONFIG = {'profile': 'synthetic:user', 'group': 'synthetic-backlog', 'name': 'synthetic',
          'selfSenderId': 'synthetic-agent', 'binary': 'never-execute'}


class BoundedHistory:
    def __init__(self, count):
        start = datetime.now(timezone.utc) - timedelta(hours=2)
        self.messages = [{'messageId': f'synthetic-{i}', 'conversationId': CONFIG['group'],
            'senderId': 'synthetic-user', 'text': str(i), 'createTime': (start + timedelta(seconds=i)).isoformat()}
            for i in range(count)]
        self.calls = []

    def call(self, args):
        if args[:2] != ['chat', '+chat-messages']:
            raise AssertionError('Only synthetic history is permitted')
        option = lambda name: args[args.index(name) + 1]
        start, end = option('--start'), option('--end')
        messages = [m for m in self.messages if datetime.fromisoformat(start) <=
                    datetime.fromisoformat(m['createTime']) < datetime.fromisoformat(end)]
        offset = 0
        resumed = '--page-token' in args
        if resumed:
            token = option('--page-token').removeprefix('dws-chat-v1.')
            saved = json.loads(base64.urlsafe_b64decode(token + '=' * (-len(token) % 4)))
            if saved['start'] != start or saved['end'] != end:
                raise AssertionError('Continuation must retain its original time window')
            offset = saved['offset']
        limit = min(int(option('--max-items')), int(option('--page-limit')) * int(option('--limit')))
        selected = messages[offset:offset + limit];next_offset = offset + len(selected)
        more = next_offset < len(messages)
        response = {'messages': selected, 'count': len(selected), 'complete': not more,
                    'partial': False, 'failedCount': 0, 'hasMore': more, 'paginationKnown': True,
                    'stopReason': 'result_limit' if more else 'source_complete',
                    'truncatedByResultLimit': more, 'truncatedByPageLimit': False}
        if more:
            # Opaque synthetic fixture: validates the public binding contract,
            # not the private encoding or server behavior of an official token.
            token = base64.urlsafe_b64encode(json.dumps({'start': start, 'end': end, 'offset': next_offset}).encode()).decode().rstrip('=')
            response['nextPageToken'] = 'dws-chat-v1.' + token
            response['nextPage'] = {'direction': 'newer', 'time': selected[-1]['createTime']}
        self.calls.append({'returned': len(selected), 'resumed': resumed, 'complete': not more})
        return response


def probe(count=1001, rounds=3):
    if not 1001 <= count <= 5000 or not 2 <= rounds <= 8:
        raise ValueError('Probe bounds: 1001..5000 messages and 2..8 polls')
    provider = BoundedHistory(count);syncs = []
    with tempfile.TemporaryDirectory(prefix='dab-synthetic-backlog-') as temp:
        root = Path(temp);bridge = Bridge(root, CONFIG, provider)
        try:
            for index in range(rounds):
                syncs.append(bridge.sync())
                if index == 0:
                    bridge.close();bridge = Bridge(root, CONFIG, provider)
            stored = bridge.db.execute('SELECT count(*) FROM events').fetchone()[0]
            unique = bridge.db.execute('SELECT count(DISTINCT message_id) FROM events').fetchone()[0]
            watermark = bridge.db.execute('SELECT 1 FROM meta WHERE key="watermark"').fetchone() is not None
        finally:bridge.close()
    return {'scope': 'Synthetic official-shaped bounded history and real local SQLite; no real DWS',
        'inputMessages': count, 'polls': rounds, 'restartAfterFirstPoll': True,
        'insertedPerPoll': [s['inserted'] for s in syncs], 'completePerPoll': [s['complete'] for s in syncs],
        'storedMessages': stored, 'uniqueMessages': unique, 'missingMessages': count - stored,
        'calls': provider.calls, 'watermarkPresent': watermark,
        'progressSatisfied': stored == unique == count and any(s['complete'] for s in syncs),
        'realDwsCalls': 0, 'credentialsRead': False, 'newNativeUITest': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--messages', type=int, default=1001)
    parser.add_argument('--rounds', type=int, default=3)
    args = parser.parse_args()
    result = probe(args.messages, args.rounds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['progressSatisfied'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

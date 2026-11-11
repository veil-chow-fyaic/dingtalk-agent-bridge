"""Validate a narrow, explicit official-log reconciliation without resending."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from .text_limits import utf16_units


def read_length_rejection(root, relative_path, delivery, config):
    path = (Path(root) / relative_path).resolve()
    if not path.is_relative_to((Path(root) / 'local').resolve()) or not path.is_file():
        raise ValueError('Rejection evidence must be an existing private local file')
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Rejection evidence too large')
    raw = path.read_bytes()
    records = json.loads(raw)
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise ValueError('Expected official DWS JSON log records')
    requests = []
    for r in records:
        if r.get('msg') != 'jsonrpc_request_body' or r.get('tool_name') != 'send_personal_message':
            continue
        args = r.get('arguments_summary')
        args = json.loads(args) if isinstance(args, str) else args
        if isinstance(args, dict) and args.get('uuid') == delivery['key']:
            requests.append((r, args))
    if len(requests) != 1:
        raise ValueError('Need one official request bound to the original idempotency key')
    request, args = requests[0]
    target_field = 'receiverOpenDingTalkId' if config.get('conversationType', 'group') == 'direct' else 'openConversationId'
    target = config['peerOpenDingTalkId'] if target_field == 'receiverOpenDingTalkId' else config['group']
    if args.get(target_field) != target or args.get('msgType') != 'text':
        raise ValueError('Rejection evidence target/type mismatch')
    execution = request.get('execution_id')
    if not isinstance(execution, str) or not execution:
        raise ValueError('Missing official execution identity')
    starts = [r for r in records if r.get('msg') == 'command_start' and r.get('execution_id') == execution]
    ends = [r for r in records if r.get('msg') == 'command_end' and r.get('execution_id') == execution]
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError('Incomplete official command boundaries')
    start, end = starts[0], ends[0]
    def at(r):
        value = datetime.fromisoformat(r['time'])
        if value.tzinfo is None:
            raise ValueError('Official evidence timestamps need timezone')
        return value
    if not at(start) <= at(request) <= at(end) or (at(end) - at(start)).total_seconds() > 120:
        raise ValueError('Invalid official command time window')
    window = [r for r in records if at(start) <= at(r) <= at(end)]
    if any(r.get('msg') in {'command_start', 'jsonrpc_request_body', 'command_end'} and
           r.get('execution_id') != execution for r in window):
        raise ValueError('Interleaved command evidence cannot bind an unlabelled business error')
    if any(r.get('tool') != 'send_personal_message' or r.get('product') != 'chat' for r in (start, end)) or (
            end.get('success') is not False or end.get('error_reason') != 'invalid_request'):
        raise ValueError('Official command did not report a definite invalid request')
    errors = [r for r in window if r.get('msg') == 'business_error']
    if len(errors) != 1:
        raise ValueError('Ambiguous official business error')
    error = errors[0]
    if (error.get('product'), error.get('tool'), error.get('reason'), error.get('server_error_code')) != (
            'chat', 'send_personal_message', 'invalid_request', 'PARAM_ERROR'):
        raise ValueError('Unsupported rejection evidence')
    match = re.fullmatch(r"sendPersonalMessageByServerPush error: Length of filed: 'textContent.text' cannot greater than (\d+) but actual is (\d+)\.", error.get('errorMsg', ''))
    payload = json.loads(delivery['payload'])
    if (not match or payload.get('kind') != 'text' or not isinstance(payload.get('text'), str) or
            int(match[1]) != 5120 or int(match[2]) <= int(match[1]) or utf16_units(payload['text']) != int(match[2])):
        raise ValueError('Official length error does not match the persisted payload')
    if hashlib.sha256(delivery['payload'].encode()).hexdigest() != delivery['fingerprint']:
        raise ValueError('Persisted payload fingerprint mismatch')
    return raw, hashlib.sha256(raw).hexdigest()

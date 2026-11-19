"""Account-bound native @ evidence and recent context for an admitted OpenClaw group."""
from datetime import datetime, timedelta
import json

from .core import BridgeError, DWS


def mention_message_ids(data, group):
    """Read the fixed DWS list-mentions contract. A partial or malformed page cannot prove absence."""
    result = data.get('result') if isinstance(data, dict) else None
    if not isinstance(result, dict) or not isinstance(result.get('conversationMessagesList'), list):
        raise ValueError('invalid_mention_result')
    # The pinned DWS chatmsg.MessageID contract takes the first non-empty
    # stable identifier in this order. Its list-mentions pagination fixtures
    # also use bare 'id'. Only IDs scoped to this official result can match.
    message_keys = ('openMessageId', 'openMsgId', 'messageId', 'message_id', 'msgId', 'msg_id', 'id')
    group_keys = ('openConversationId', 'openconversation_id', 'conversationId', 'conversation_id', 'chatId', 'chat_id')
    def check_scope(entry, *, required):
        if not isinstance(entry, dict):
            raise ValueError('mention_scope_mismatch')
        available = [entry[k] for k in group_keys if entry.get(k) not in (None, '')]
        if (required and not available) or any(value != group for value in available):
            raise ValueError('mention_scope_mismatch')

    ids = set()
    for conversation in result['conversationMessagesList']:
        check_scope(conversation, required=True)
        if not isinstance(conversation.get('messages'), list):
            raise ValueError('invalid_mention_messages')
        for message in conversation['messages']:
            check_scope(message, required=False)
            mid = next((message[k] for k in message_keys if message.get(k) not in ('', None)), None)
            if type(mid) is not int and (not isinstance(mid, str) or not mid.strip()):
                raise ValueError('missing_mention_identity')
            ids.add(str(mid).strip())
    paging = data.get('paging', {})
    if not isinstance(paging, dict):
        raise ValueError('invalid_mention_paging')
    complete = (result.get('hasMore', paging.get('hasMore')) is False
                and paging.get('hasMore') is not True and not paging.get('truncated')
                and paging.get('sourceExhausted', True) is True and not paging.get('truncatedWithinPage') and not paging.get('partial') and not data.get('hasMore')
                and data.get('complete', True) is True and not data.get('partial'))
    return ids, complete


class GroupMentions:
    def __init__(self, root, route):
        self.dws = DWS(root, route)
        self.group = route['group']
        self.page = None
        self.reading = False
        self.stopping = False

    def stop_when_drained(self, _signal, _frame):
        if not self.reading:
            raise SystemExit(0)
        self.stopping = True

    def check(self, message, seq, cursor):
        # Reuse a completed response only for already-ingested events in its minute.
        # A later insertion with the same timestamp needs a new official observation.
        at = datetime.fromisoformat(message['receivedAt'])
        minute = at.replace(second=0, microsecond=0)
        if self.page is None or self.page[0] != minute or self.page[1] < seq:
            self.reading = True
            try:
                page = self.dws.call(['chat', 'message', 'list-mentions', '--conversation-id', self.group,
                                      '--start', minute.isoformat(), '--end', (minute + timedelta(minutes=1)).isoformat(),
                                      '--limit', '50', '--page-all', '--page-limit', '4', '--max-items', '200'])
                ids, complete = mention_message_ids(page, self.group)
            except (BridgeError, ValueError):
                return None
            finally:
                self.reading = False
                # A routine host reload must let the managed DWS lease finish. The
                # unread poll has not claimed a message, so its successor can resume.
                if self.stopping:
                    raise SystemExit(0)
            self.page = (minute, cursor, ids, complete) if complete else None
        else:
            _, _, ids, complete = self.page
        if message['id'] in ids:
            return True
        if datetime.now(at.tzinfo) < at + timedelta(seconds=15):
            self.page = None
            return None
        return False if complete else None


def recent_group_context(db, mid, allow_senders):
    if not isinstance(allow_senders, list) or any(not isinstance(s, str) for s in allow_senders):
        raise ValueError('invalid_context_senders')
    current = db.execute("""SELECT i.seq, i.model FROM inbox i JOIN host_dispatch d USING(message_id)
                            WHERE i.message_id=? AND d.status IN ('claimed','preparing')""", (mid,)).fetchone()
    if current is None:
        raise ValueError('group_context_requires_claim')
    incoming = json.loads(current['model'])
    if incoming['conversationType'] != 'group' or incoming['senderId'] not in allow_senders:
        raise ValueError('group_context_scope')
    lines = []
    for row in db.execute('SELECT model FROM inbox WHERE seq<? ORDER BY seq DESC LIMIT 16', (current['seq'],)):
        msg = json.loads(row['model']) if row['model'] else None
        if (not msg or msg.get('issues') or msg.get('accountId') != incoming['accountId']
                or msg.get('conversationId') != incoming['conversationId'] or msg.get('fromSelf') is None
                or not msg['fromSelf'] and msg.get('senderId') not in allow_senders):
            continue
        lines.append({'speaker': 'assistant' if msg['fromSelf'] else
                      'current_sender' if msg['senderId'] == incoming['senderId'] else 'other_sender',
                      'text': ''.join(p['text'] for p in msg['parts'] if p['type'] == 'text')[:600],
                      'attachments': sum(p['type'] != 'text' for p in msg['parts'])})
        if len(lines) == 8:
            break
    return list(reversed(lines))

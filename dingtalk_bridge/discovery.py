"""Bounded metadata discovery. Never subscribes, reads message bodies or adds routes."""
from .core import BridgeError


def discover(dws, account_id, *, cursor=0, limit=50, configured=()):
    if type(cursor) is not int or cursor<0 or type(limit) is not int or not 1<=limit<=100:
        raise ValueError('Invalid discovery cursor/limit')
    data=dws.call(['chat','+chat-list','--types','group,p2p','--page-token',str(cursor),'--page-size',str(limit)])
    if not isinstance(data.get('chats'),list):raise BridgeError('Missing conversation list')
    candidates=[];seen=set()
    for item in data['chats']:
        cid=item.get('openConversationId');kind=item.get('conversationType')
        if not isinstance(cid,str) or not cid or kind not in {'group','direct'}:
            raise BridgeError('Unknown conversation identity/type')
        if cid in seen:continue
        seen.add(cid)
        candidates.append({'account_id':account_id,'conversation_id':cid,'conversation_type':kind,
            'name':item.get('name',''),'group_type':item.get('groupType'),
            'configured':cid in configured,'requires_peer_id':kind=='direct'})
    return {'account_id':account_id,'conversations':candidates,
        'complete':data.get('complete') is True and data.get('hasMore') is False and data.get('paginationKnown') is True and not data.get('partial') and not data.get('failedCount'),
        'has_more':data.get('hasMore'),'next_cursor':data.get('nextCursor'),
        'pagination_known':data.get('paginationKnown') is True,'stop_reason':data.get('stopReason'),
        'failed_count':data.get('failedCount',0),'routes_changed':False}

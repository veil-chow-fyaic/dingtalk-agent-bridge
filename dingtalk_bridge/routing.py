"""Runtime-neutral routing. An account is a provider auth context, not a product tenant."""
import hashlib
import threading
from .core import Bridge, DWSCredentialStoreUnavailable, credential_store_diagnostic
from .dws_access import DWSAccess, DWSAccessSuspended, access_diagnostic


def route_configs(config):
    if 'routes' not in config:
        yield {**config,'accountId':config.get('accountId','default'),'conversationType':'group'},None
        return
    routes=config['routes']
    if not isinstance(routes,list) or not routes:raise ValueError('routes must be a non-empty list')
    seen=set();identities=set();accounts={};legacy_used=False
    for raw in routes:
        c={**raw}
        for field in ('accountId','profile','conversationId','binary','conversationType'):
            if not isinstance(c.get(field),str) or not c[field]:raise ValueError('Missing route field: '+field)
        if c['conversationType'] not in {'group','direct'}:raise ValueError('Unknown conversationType')
        if c['conversationType']=='direct' and not c.get('peerOpenDingTalkId'):
            raise ValueError('Direct route requires resolved peerOpenDingTalkId')
        if c['accountId'] in accounts and accounts[c['accountId']]!=c['profile']:
            raise ValueError('Account ID maps to multiple auth contexts')
        accounts[c['accountId']]=c['profile']
        key=(c['accountId'],c['conversationId'])
        identity=(c['profile'],c['conversationId'])
        if key in seen or identity in identities:raise ValueError('Duplicate conversation route')
        seen.add(key);identities.add(identity);c['group']=c['conversationId'];c.setdefault('name','')
        state=hashlib.sha256(('route:'+c['profile']+'\0'+c['conversationId']).encode()).hexdigest()
        if c.get('stateStorage') == 'legacy':
            if legacy_used:raise ValueError('Only one route can retain legacy state')
            legacy_used=True;state=None
        elif c.get('stateStorage') not in (None,'routed'):
            raise ValueError('Unknown stateStorage')
        yield c,state


class Hub:
    def __init__(self,root,config,factory=Bridge):
        self.routes={};self.poll_errors={};self.poll_error_details={};self.status_lock=threading.Lock()
        self.access=DWSAccess(root)
        try:
            for c,state in route_configs(config):
                if c.get('receiveMode','history') not in {'history','stream_hint'}:
                    raise ValueError('Unknown receiveMode')
                key=(c['accountId'],c['group'])
                self.routes[key]=factory(root,c,state_name=state)
                self.poll_errors[key]=None
                self.poll_error_details[key]=None
        except Exception:
            self.close();raise
    def select(self,account_id=None,conversation_id=None):
        if account_id is None and conversation_id is None and len(self.routes)==1:
            return next(iter(self.routes.values()))
        if not account_id or not conversation_id:raise ValueError('account_id and conversation_id required')
        try:return self.routes[(account_id,conversation_id)]
        except KeyError:raise ValueError('Unknown account/conversation route') from None
    def conversations(self):
        return [{'account_id':a,'conversation_id':c,'conversation_type':b.config.get('conversationType','group'),
                 'name':b.config.get('name','')} for (a,c),b in self.routes.items()]
    def discover(self,account_id=None,**options):
        from .discovery import discover
        accounts={a:b for (a,_),b in self.routes.items()}
        if account_id is None and len(accounts)==1:account_id=next(iter(accounts))
        if account_id not in accounts:raise ValueError('Select a configured account_id')
        b=accounts[account_id]
        return discover(b.dws,account_id,configured={c for a,c in self.routes if a==account_id},**options)
    def poll(self,stop=None):
        for key,b in self.routes.items():
            if stop is not None and stop.is_set():break
            try:
                b.sync();error=None;detail=None
            except Exception as exc:
                detail=access_diagnostic(exc.reason) if isinstance(exc,DWSAccessSuspended) else None
                error=type(exc).__name__
            with self.status_lock:
                self.poll_errors[key]=error;self.poll_error_details[key]=detail
    def health(self):
        rows=[]
        for route in self.conversations():
            key=(route['account_id'],route['conversation_id'])
            row={**route,**self.routes[key].health()}
            with self.status_lock:
                error=self.poll_errors[key];detail=self.poll_error_details[key]
                detail=dict(detail) if detail else None
            # A valid CLI response may still report failed/incomplete history.
            # Derive this from the persisted sync result so explicit /sync and
            # process restart cannot hide it. Safe budget paging is progress,
            # even when the page adds no new events; it is not a poll failure.
            sync=row.get('last_sync')
            if (error is None and sync and sync.get('complete') is False
                    and sync.get('continuing') is not True):
                error='HistoryIncomplete'
            row.update(poll_error=error,poll_error_detail=detail)
            rows.append(row)
        if len(rows)==1:return {**rows[0],'route_count':1,'runtime_required':False,'dws_access':self.access.status()}
        return {'mode':'experimental','route_count':len(rows),'routes':rows,'runtime_required':False,
                'events':sum(r['events'] for r in rows),'poll_error':any(r['poll_error'] for r in rows),
                'dws_access':self.access.status()}
    def close(self):
        for b in self.routes.values():b.close()

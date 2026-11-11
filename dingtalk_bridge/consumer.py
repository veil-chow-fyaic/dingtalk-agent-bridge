"""Durable shadow inbox independent of runtime choice. No send or model execution."""
import fcntl
import hashlib
import json
from itertools import islice
from pathlib import Path
import sqlite3
from .message_model import normalize,media_parts,materialize


class HydrationPending(Exception):
    """A caller-owned download is in flight; keep the current durable state."""


class Inbox:
    def __init__(self,root,config,name='shadow',state_name=None):
        if not name or not all(c.isalnum() or c in '_-' for c in name):raise ValueError('invalid_consumer_name')
        self.root=Path(root).resolve();self.config=config
        self.cache_root=self.root/'local/runtime'
        if state_name:self.cache_root=self.cache_root/'routes'/state_name
        self.cache_root=self.cache_root/'downloads'
        directory=self.root/'local/consumers'/name;directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.lock=(directory/'process.lock').open('a')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:self.lock.close();raise ValueError('consumer_already_owned')
        self.db=sqlite3.connect(directory/'inbox.sqlite3')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS inbox(seq INTEGER PRIMARY KEY,message_id TEXT UNIQUE NOT NULL,
            raw TEXT NOT NULL,model TEXT,state TEXT NOT NULL,error TEXT,attempts INTEGER NOT NULL DEFAULT 0);
        ''')
        scope=json.dumps([config.get('accountId','default'),config['profile'],config['group'],config.get('selfSenderId'),config.get('historyTimezone','Asia/Shanghai')])
        prior=self.db.execute('SELECT value FROM meta WHERE key="scope"').fetchone()
        if prior and prior[0]!=scope:self.close();raise ValueError('consumer_scope_mismatch')
        with self.db:self.db.execute('INSERT OR IGNORE INTO meta VALUES ("scope",?)',(scope,))
        (directory/'inbox.sqlite3').chmod(0o600)
    @property
    def cursor(self):
        row=self.db.execute('SELECT value FROM meta WHERE key="cursor"').fetchone()
        return int(row[0]) if row else 0
    def ingest(self,batch):
        events=batch['events'];cursor=self.cursor;last=cursor
        with self.db:
            for event in events:
                seq=event['seq'];mid=event['message_id']
                if type(seq) is not int or seq<=last or not isinstance(mid,str) or not mid:
                    raise ValueError('invalid_event_order_or_identity')
                if event.get('conversation_id')!=self.config['group'] or event.get('account_id',self.config.get('accountId','default'))!=self.config.get('accountId','default'):
                    raise ValueError('cross_scope_batch')
                try:
                    model=normalize(event,self.config)
                    state='pending_media' if list(media_parts(model)) else 'normalized'
                    error=None
                except (ValueError,KeyError,TypeError) as exc:
                    model=None;state='quarantined';error=type(exc).__name__
                self.db.execute('INSERT INTO inbox(seq,message_id,raw,model,state,error) VALUES (?,?,?,?,?,?)',
                    (seq,mid,json.dumps(event,ensure_ascii=False),json.dumps(model,ensure_ascii=False),state,error))
                last=seq
            if type(batch['next_cursor']) is not int or batch['next_cursor']!=last:raise ValueError('cursor_does_not_match_batch')
            self.db.execute('INSERT OR REPLACE INTO meta VALUES ("cursor",?)',(str(last),))
        return len(events)
    def hydrate(self,download,include_self=False,limit=20,eligible=None):
        if type(limit) is not int or limit<1:raise ValueError('Invalid hydration limit')
        candidates=self.db.execute('SELECT * FROM inbox WHERE state IN ("pending_media","media_failed") ORDER BY attempts,seq')
        def selected(row):
            model=json.loads(row['model'])
            return (include_self or model['fromSelf'] is False) and (eligible is None or eligible(model))
        rows=list(islice((r for r in candidates if selected(r)),limit))
        completed=failed=0
        for row in rows:
            model=json.loads(row['model'])
            if model['fromSelf'] is not False and not include_self:continue
            try:
                materialize(model,download(row['message_id']),self.root,self.cache_root)
                state,error='normalized',None;completed+=1
            except HydrationPending:continue
            except Exception as exc:
                state,error='media_failed',type(exc).__name__;failed+=1
            with self.db:self.db.execute('UPDATE inbox SET model=?,state=?,error=?,attempts=attempts+1 WHERE seq=?',
                (json.dumps(model,ensure_ascii=False),state,error,row['seq']))
        return {'completed':completed,'failed':failed}
    def ready(self):
        result=[]
        for row in self.db.execute('SELECT seq,model FROM inbox WHERE state="normalized" ORDER BY seq'):
            model=json.loads(row['model'])
            if model['fromSelf'] is False and not model['issues']:
                valid=True
                for part in media_parts(model):
                    path=Path(part.get('path','')).resolve()
                    if not path.is_relative_to(self.cache_root.resolve()) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=part.get('sha256'):
                        valid=False;break
                if valid:result.append({'seq':row['seq'],'message':model})
                else:
                    with self.db:self.db.execute('UPDATE inbox SET state="media_failed",error="cache_changed" WHERE seq=?',(row['seq'],))
        return result
    def summary(self):
        ready_count=len(self.ready())
        states={r[0]:r[1] for r in self.db.execute('SELECT state,count(*) FROM inbox GROUP BY state')}
        models=[json.loads(r[0]) for r in self.db.execute('SELECT model FROM inbox WHERE model != "null"')]
        return {'cursor':self.cursor,'states':states,'messages':sum(states.values()),'readyForRuntime':ready_count,
            'selfFiltered':sum(m['fromSelf'] is True for m in models),'unknownSender':sum(m['fromSelf'] is None for m in models),
            'withIssues':sum(bool(m['issues']) for m in models),'quotes':sum('quote' in m for m in models),
            'mediaParts':sum(len(list(media_parts(m))) for m in models),'autoReply':False}
    def close(self):
        self.db.close();fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close()

"""Durable shadow inbox independent of runtime choice. No send or model execution."""
import errno
import fcntl
import hashlib
import json
from itertools import islice
from pathlib import Path
import sqlite3
from .message_model import completes_history,normalize,media_parts,materialize,truncated_history


def _resolve_cache_path(path):
    try:
        return path.resolve(strict=True)
    except RuntimeError as exc:
        # Python 3.11 pathlib wraps only symlink loops in RuntimeError.
        # Keep unrelated runtime/programming errors visible to the caller.
        cause=exc.__context__
        if not isinstance(cause,OSError) or cause.errno!=errno.ELOOP:raise
        raise OSError(errno.ELOOP,'cache_symlink_loop') from exc


class HydrationPending(Exception):
    """A caller-owned download is in flight; keep the current durable state."""


def execution_scope(route):
    """Keep the gateway's existing scope and on-disk lock name across host choices."""
    scope = json.dumps([route['accountId'], route['profile'], route['group'],
                        route.get('conversationType', 'group')])
    return scope, hashlib.sha256(scope.encode()).hexdigest()[:24]


def acquire_consumer_lock(root, name):
    if not name or not all(c.isalnum() or c in '_-' for c in name):
        raise ValueError('invalid_consumer_name')
    directory = Path(root) / 'local/consumers' / name
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (directory / 'process.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise ValueError('consumer_already_owned') from None
    return lock


class Inbox:
    def __init__(self,root,config,name='shadow',state_name=None):
        self.root=Path(root).resolve();self.config=config
        self.cache_root=self.root/'local/runtime'
        if state_name:self.cache_root=self.cache_root/'routes'/state_name
        self.cache_root=self.cache_root/'downloads'
        self.lock=acquire_consumer_lock(self.root,name)
        directory=Path(self.lock.name).parent
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
    @property
    def revision_cursor(self):
        row = self.db.execute('SELECT value FROM meta WHERE key="revision_cursor"').fetchone()
        return int(row[0]) if row else 0

    def read_cursors(self):
        return {'after':self.cursor, 'after_revision':self.revision_cursor}

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
            first_repaired = None
            if 'revisions' in batch or 'next_revision_cursor' in batch:
                previous = self.revision_cursor
                for item in batch['revisions']:
                    rev, event = item['revision'], item['event']
                    seq = event['seq']
                    if type(rev) is not int or rev <= previous or type(seq) is not int or not 0 < seq <= last:
                        raise ValueError('invalid_history_revision')
                    previous = rev
                    if (event.get('conversation_id')!=self.config['group']
                            or event.get('account_id')!=self.config.get('accountId','default')
                            or event.get('conversation_type')!=self.config.get('conversationType','group')):
                        raise ValueError('cross_scope_revision')
                    old = self.db.execute('SELECT message_id,raw FROM inbox WHERE seq=?', (seq,)).fetchone()
                    if old is None:  # Cursor-only activation intentionally skipped this original.
                        continue
                    if old['message_id'] != event['message_id']:
                        raise ValueError('history_revision_identity_mismatch')
                    before = json.loads(old['raw'])
                    if not truncated_history(before['raw']):
                        continue  # Already imported complete; preserve hydration and execution.
                    if not completes_history(before, event):
                        raise ValueError('history_revision_identity_mismatch')
                    model = normalize(event,self.config)
                    if model['issues']:
                        raise ValueError('incomplete_history_revision')
                    state = 'pending_media' if any(media_parts(model)) else 'normalized'
                    self.db.execute('''UPDATE inbox SET raw=?,model=?,state=?,error=NULL,attempts=0
                        WHERE seq=?''', (json.dumps(event,ensure_ascii=False),json.dumps(model,ensure_ascii=False),state,seq))
                    first_repaired = min(seq, first_repaired) if first_repaired is not None else seq
                if type(batch['next_revision_cursor']) is not int or batch['next_revision_cursor'] != previous:
                    raise ValueError('revision_cursor_does_not_match_batch')
                self.db.execute('INSERT OR REPLACE INTO meta VALUES ("revision_cursor",?)',(str(previous),))
        self.first_repaired_seq = first_repaired
        return len(events)
    def hydrate(self,download,include_self=False,limit=20,eligible=None,priority_message_id=None):
        if type(limit) is not int or limit<1:raise ValueError('Invalid hydration limit')
        # Consume the caller's outstanding result before the bounded candidate
        # window. Otherwise newer zero-attempt rows can starve its owner.
        candidates=self.db.execute('SELECT * FROM inbox WHERE state IN ("pending_media","media_failed") '
            'ORDER BY (message_id=?) DESC,attempts,seq',(priority_message_id,))
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
        rows=self.db.execute('SELECT seq,model FROM inbox WHERE state="normalized" ORDER BY seq')
        return list(self.iter_ready(rows))

    def iter_ready(self, rows):
        """Revalidate originals before yielding any selected normalized inbox row."""
        for row in rows:
            model=json.loads(row['model'])
            if model['fromSelf'] is False and not model['issues']:
                valid=True;error='cache_changed'
                for part in media_parts(model):
                    try:
                        path=_resolve_cache_path(Path(part.get('path','')))
                        if not path.is_relative_to(_resolve_cache_path(self.cache_root)) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=part.get('sha256'):
                            valid=False;break
                    except OSError:
                        # A missing/unreadable original belongs to this message;
                        # keep later input available without downloading here.
                        valid=False;error='cache_unavailable';break
                if valid:yield {'seq':row['seq'],'message':model}
                else:
                    with self.db:self.db.execute('UPDATE inbox SET state="media_failed",error=? WHERE seq=?',(error,row['seq']))
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

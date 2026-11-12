"""Synthetic wall-clock progression, never changing the host clock or real state."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge.core import Bridge, BridgeError


class WindowHistory:
    def __init__(self, route, times):
        self.messages=[{'messageId':'synthetic-window-'+str(i),'conversationId':route['group'],
                       'senderId':'synthetic-peer','text':'synthetic window boundary',
                       'createTime':t.isoformat()} for i,t in enumerate(times)]
        self.calls=[];self.fail=False

    def call(self,args):
        if args[:2]!=['chat','+chat-messages']:raise AssertionError('history only')
        opt=lambda name:args[args.index(name)+1]
        start,end=(datetime.fromisoformat(opt(n)) for n in ('--start','--end'))
        self.calls.append({'start':start,'end':end,'arguments':list(args)})
        if self.fail:raise BridgeError('synthetic offline')
        messages=[m for m in self.messages if start<=datetime.fromisoformat(m['createTime'])<end]
        return {'messages':messages,'count':len(messages),'complete':True,'hasMore':False,
                'partial':False,'failedCount':0,'stopReason':'source_complete'}


class HistoryOutageWindowTests(unittest.TestCase):
    now=datetime(2026,11,12,6,0,tzinfo=timezone.utc)

    @contextmanager
    def worker(self,kind,times):
        with tempfile.TemporaryDirectory(prefix='synthetic-outage-window-') as folder:
            route={'profile':'synthetic:user','group':'synthetic-'+kind,'name':'synthetic',
                   'accountId':'synthetic-account','selfSenderId':'synthetic-self',
                   'conversationType':kind,'peerOpenDingTalkId':'synthetic-peer','binary':'never-execute'}
            provider=WindowHistory(route,times);worker=Bridge(Path(folder),route,provider)
            try:yield worker,provider
            finally:worker.close()

    def sync_at(self,worker,now,deep=False):
        with patch('dingtalk_bridge.core.datetime') as clock:
            clock.now.return_value=now;clock.fromisoformat.side_effect=datetime.fromisoformat
            return worker.sync(deep=deep)

    def meta(self,worker,key):
        row=worker.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return row[0] if row else None

    def restart(self,worker,provider):
        root,config=worker.root,worker.config
        worker.close()
        # Reuse the object reference held by worker() so its finalizer closes
        # the new connection, not the already-closed old one.
        replacement=Bridge(root,config,provider)
        worker.__dict__.clear();worker.__dict__.update(replacement.__dict__)

    def test_72_hour_watermark_is_not_clamped_to_24_hour_deep_lookback(self):
        watermark=self.now-timedelta(hours=72)
        times=[watermark-timedelta(minutes=5),watermark,watermark+timedelta(hours=1),
               self.now-timedelta(hours=25),self.now-timedelta(seconds=1),self.now]
        for kind in ('group','direct'):
            with self.subTest(kind=kind),self.worker(kind,times) as (worker,provider):
                with worker.db:
                    for key in ('watermark','last_deep_sync'):
                        worker.db.execute('INSERT INTO meta VALUES(?,?)',(key,watermark.isoformat()))
                self.restart(worker,provider)
                result=self.sync_at(worker,self.now)
                self.assertEqual(provider.calls[0]['start'],watermark-timedelta(minutes=5))
                self.assertEqual(provider.calls[0]['end'],self.now)
                self.assertEqual(result['inserted'],5);self.assertTrue(result['deep'])
                self.assertEqual(self.meta(worker,'watermark'),self.now.isoformat())
                self.assertEqual(self.sync_at(worker,self.now+timedelta(seconds=1))['inserted'],1)
                self.assertEqual(worker.db.execute('SELECT count(*) FROM events').fetchone()[0],6)
                # Same body/time-range overlap is deduplicated by message ID.
                self.assertEqual(self.sync_at(worker,self.now+timedelta(seconds=2))['inserted'],0)
                target='--group' if kind=='group' else '--open-dingtalk-id'
                self.assertIn(target,provider.calls[0]['arguments'])

    def test_failed_pre_outage_window_finishes_before_downtime_tail_is_read(self):
        old_end=self.now-timedelta(hours=72)
        times=[old_end-timedelta(hours=1),old_end,old_end+timedelta(hours=1),
               self.now-timedelta(hours=25),self.now-timedelta(seconds=1)]
        for kind in ('group','direct'):
            with self.subTest(kind=kind),self.worker(kind,times) as (worker,provider):
                provider.fail=True
                with self.assertRaises(BridgeError):self.sync_at(worker,old_end)
                original=self.meta(worker,'history_window')
                self.assertIsNone(self.meta(worker,'watermark'))
                self.restart(worker,provider);provider.fail=False
                self.assertEqual(self.meta(worker,'history_window'),original)
                self.assertEqual(self.sync_at(worker,self.now)['inserted'],1)
                self.assertEqual(provider.calls[1]['end'],old_end)
                self.assertEqual(self.meta(worker,'watermark'),old_end.isoformat())
                # Completing the frozen old window is not caught-up-to-now.
                self.assertEqual(self.sync_at(worker,self.now)['inserted'],4)
                self.assertEqual(provider.calls[2]['start'],old_end-timedelta(minutes=5))
                self.assertEqual(provider.calls[2]['end'],self.now)
                self.assertEqual(worker.db.execute('SELECT count(*) FROM events').fetchone()[0],5)
                self.assertEqual(self.meta(worker,'watermark'),self.now.isoformat())

    def test_no_watermark_bootstrap_is_only_24_hours_not_all_history(self):
        times=[self.now-timedelta(hours=25),self.now-timedelta(hours=24),self.now-timedelta(seconds=1)]
        for kind in ('group','direct'):
            with self.subTest(kind=kind),self.worker(kind,times) as (worker,provider):
                result=self.sync_at(worker,self.now,deep=True)
                self.assertEqual(provider.calls[0]['start'],self.now-timedelta(hours=24))
                self.assertEqual(result['inserted'],2)
                self.assertIsNone(worker.db.execute('SELECT 1 FROM events WHERE message_id="synthetic-window-0"').fetchone())
                self.assertTrue(result['complete'])  # Completeness of this range only.


if __name__=='__main__':unittest.main()

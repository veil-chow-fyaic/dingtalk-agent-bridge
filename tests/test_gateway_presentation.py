"""User-visible gateway outputs using the normal intake, executor and outbox paths."""
import hashlib
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest

from dingtalk_bridge.agent_gateway import Gateway
from dingtalk_bridge.agent_runtime import RuntimeFailure
from dingtalk_bridge.text_limits import PERSONAL_TEXT_UNITS, utf16_units
from test_agent_gateway import FakeAPI, FakeRuntime
from test_routing_consumer import CFG, event


class GatewayPresentationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.route = {**CFG, 'conversationType': 'direct'}
        self.settings = {'allowedSenderIds': ['self', 'other'], 'allowSelfCommands': True,
                         'runtime': {'kind': 'kimi', 'binary': 'unused'}}
        self.api = FakeAPI()
        self.runtime = FakeRuntime()
        self.gateway = Gateway(self.root, self.route, None, self.settings, self.api, self.runtime)
        self.addCleanup(lambda: self.gateway.close())

    def reopen(self, **options):
        self.gateway.close()
        self.gateway = Gateway(self.root, self.route, None, {**self.settings, **options}, self.api, self.runtime)

    def task(self, seq, text, sender='other'):
        self.api.events.append(event(seq, text=text, sender=sender))
        self.gateway.intake()
        self.assertTrue(self.gateway.execute_one())

    def test_group_and_private_literals_retain_whitespace_and_harness_markup(self):
        text = '  [Agent] 宿主原文\r\n' + '🙂' * 3000 + '\n  '
        self.runtime.run = lambda *args: {'text':text, 'files': []}
        self.task(1, '[Agent] 我在引用别人的回复。')
        self.gateway.flush()
        self.assertEqual(self.gateway.db.execute('SELECT command FROM jobs').fetchone()[0], '[Agent] 我在引用别人的回复。')
        for group in [False, True]:
            if group:
                self.route = CFG
                self.reopen()
                self.task(2, '/agent group')
                self.gateway.flush()
            chunks = [value['text'] for key, value in self.api.sends.items() if self.gateway.db.execute(
                'SELECT 1 FROM outbox WHERE key=?',(key,)).fetchone()]
            self.assertEqual(''.join(chunks), text)
            self.assertTrue(all(0 < utf16_units(chunk) <= PERSONAL_TEXT_UNITS for chunk in chunks))
            self.assertGreater(len(chunks), 1)

    def test_file_only_outputs_keep_names_even_with_collisions(self):
        name = '总结 (终版)🙂.txt'
        def run(prompt, workspace, *args):
            files = []
            for folder in ('a', 'b'):
                rel = Path('exports') / folder / name
                (workspace / rel.parent).mkdir()
                (workspace / rel).write_text(folder)
                files.append(str(rel))
            return {'text':'','files':files}
        self.runtime.run = run
        self.task(1, '请发两份文件')
        self.gateway.flush()
        sends = list(self.api.sends.values())
        self.assertEqual(len(sends), 2)
        for value, content in zip(sends, [b'a', b'b']):
            self.assertEqual(Path(value['file']).name, name)
            self.assertEqual((self.root / value['file']).read_bytes(), content)
            self.assertEqual(value['expected_sha256'], hashlib.sha256(content).hexdigest())

    def test_inline_image_syntax_is_sent_verbatim_as_text(self):
        text = '源代码 ![图](should-not-be-read.png)\n'
        self.runtime.run = lambda *args: {'text':text,'files':[]}
        self.task(1, '贴出示例')
        self.gateway.flush()
        reply, = self.api.sends.values()
        self.assertEqual(reply['text'], text)
        self.assertNotIn('file', reply)

    def test_exact_retry_after_upgrading_or_switching_presentation(self):
        self.reopen(chatPresentation='diagnostic')
        self.task(1, '诊断')
        before = dict(self.gateway.db.execute('SELECT key,payload FROM outbox'))
        self.api.fail_once = True
        self.gateway.flush()
        self.reopen()
        self.gateway.intake()
        self.gateway.flush()
        self.assertFalse(self.gateway.execute_one())
        for key, raw in before.items():
            self.assertEqual(self.api.sends[key], {'idempotency_key':key,**json.loads(raw)})
        self.assertEqual(len(before), 3)
        self.assertTrue(any('[Agent] 已接收任务' in raw for raw in before.values()))
        self.task(2, '普通任务')
        self.gateway.flush()
        new = [v for k, v in self.api.sends.items() if k not in before]
        self.assertEqual([v['text'] for v in new if 'text' in v], ['完成'])
        self.assertEqual(len(new), 2)

    def test_authorized_self_echo_and_lost_http_response(self):
        self.runtime.run = lambda *args: {'text':'/agent cancel','files':[]}
        self.task(1, '请输出一条例子')
        self.api.fail_once = True
        self.gateway.flush()
        key, = self.api.sends
        echo = event(2, text='/agent cancel', sender='self')
        # The FakeAPI echoes its key as the verified native message ID.
        echo['message_id'] = echo['raw']['messageId'] = key
        self.api.events.extend([echo, event(3, text='/agent cancel', sender='self')])
        self.gateway.intake()
        self.assertEqual(self.gateway.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
        self.gateway.flush()
        self.reopen()
        self.gateway.intake()
        self.gateway.flush()
        self.assertEqual(list(r[0] for r in self.gateway.db.execute('SELECT seq FROM jobs ORDER BY seq')), [1, 3])
        self.assertEqual([v['text'] for v in self.api.sends.values()], ['/agent cancel','当前没有正在执行或等待的任务。'])

    def test_upgrade_does_not_promote_previously_ignored_inbox_rows(self):
        self.reopen(chatPresentation='diagnostic')
        self.api.events = [event(1,text='[Agent] previously ignored')]
        self.gateway.inbox.ingest(self.api('/v1/events?after=0'))
        # A v1 tasks ledger predates the cursor introduced by this upgrade.
        with self.gateway.db:
            self.gateway.db.execute('DELETE FROM meta WHERE key="legacy_prefix_cursor"')
        self.reopen()
        self.task(2, '[Agent] brand new literal')
        self.assertEqual(list(r[0] for r in self.gateway.db.execute('SELECT seq FROM jobs')), [2])
        self.reopen()
        self.gateway.intake()
        self.assertFalse(self.gateway.execute_one())

    def test_friendly_status_and_delivery_failures_have_no_trace_identifier(self):
        self.api.events = [event(1,text='/agent status')]
        self.gateway.intake()
        self.gateway.flush()
        self.assertEqual(next(iter(self.api.sends.values()))['text'], '当前没有待处理的任务。')
        self.task(2, 'do work')
        def reject_one(path, data=None):
            if path == '/v1/send' and data.get('file'):
                return {'state':'rejected','message_id':None}
            return self.api(path,data)
        self.gateway.api = reject_one
        self.gateway.flush()
        self.gateway.flush()
        job = self.gateway.db.execute('SELECT id FROM jobs WHERE seq=2').fetchone()[0]
        issue = self.api.sends['agent-'+job+'-delivery-issue']['text']
        self.assertIn('部分回复未送达', issue)
        self.assertNotIn(job[:8], issue)
        self.assertNotIn('[Agent]', issue)

    def test_system_notice_with_custom_prefix_is_not_a_self_command_after_crash(self):
        self.settings.update(chatPresentation='diagnostic', prefix='[Agent]')
        self.reopen()
        self.api.events = [event(1, text='[Agent] first',sender='self'), event(2, text='[Agent] second',sender='self')]
        self.gateway.intake()
        self.assertEqual(list(row[0] for row in self.gateway.db.execute('SELECT seq FROM jobs ORDER BY seq')), [1, 2])
        def die_after_send(path, data=None):
            self.api(path, data)
            raise SystemExit('fixture: crash between transport and recording receipt')
        self.gateway.api = die_after_send
        with self.assertRaises(SystemExit):
            self.gateway.flush()
        key, = self.api.sends
        with sqlite3.connect(self.gateway.local/'tasks.sqlite3') as reader:
            self.assertEqual(reader.execute('SELECT send_attempted FROM outbox WHERE key=?',(key,)).fetchone()[0], 1)
        self.reopen()
        echo = event(3, text=self.api.sends[key]['text'], sender='self')
        echo['message_id'] = echo['raw']['messageId'] = key
        self.api.events.extend([echo, event(4, text='[Agent] status',sender='self'), event(5, text='work',sender='other')])
        self.gateway.intake()
        self.assertEqual(list(row[0] for row in self.gateway.db.execute('SELECT seq FROM jobs ORDER BY seq')), [1, 2, 5])
        self.gateway.flush()
        self.gateway.intake()
        self.assertEqual(list(row[0] for row in self.gateway.db.execute('SELECT seq FROM jobs ORDER BY seq')), [1, 2, 4, 5])

    def test_old_pending_notice_is_conservatively_migrated_with_identical_payload(self):
        self.reopen(chatPresentation='diagnostic')
        self.api.events = [event(1, text='/agent first',sender='other')]
        self.gateway.intake()
        key, raw = self.gateway.db.execute('SELECT key,payload FROM outbox').fetchone()
        with self.gateway.db:
            self.gateway.db.execute('ALTER TABLE outbox DROP COLUMN send_attempted')
        self.reopen()
        self.assertEqual(tuple(self.gateway.db.execute('SELECT key,payload,send_attempted FROM outbox').fetchone()),
                         (key, raw, 1))
        self.api.events.append(event(2, text='/agent status',sender='self'))
        self.gateway.intake()
        self.assertEqual(self.gateway.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
        self.gateway.flush()
        self.gateway.intake()
        self.assertEqual(self.gateway.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)
        self.assertEqual(self.api.sends[key], {'idempotency_key':key,**json.loads(raw)})

    def test_older_flusher_cannot_make_pending_send_look_unattempted_after_restart(self):
        self.reopen(chatPresentation='diagnostic')
        self.api.events = [event(1, text='/agent status', sender='self')]
        self.gateway.intake()
        key, raw, attempted = self.gateway.db.execute('SELECT key,payload,send_attempted FROM outbox').fetchone()
        self.assertEqual(attempted, 0)
        # A v1 flusher can attempt this v2 row and lose its HTTP response
        # without touching the column it doesn't know about.
        self.api('/v1/send', {'idempotency_key':key, **json.loads(raw)})
        self.reopen()
        self.api.events.append(event(2, text='/agent new', sender='self'))
        self.gateway.intake()
        self.assertEqual(self.gateway.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
        self.gateway.flush()
        self.gateway.intake()
        self.assertEqual(self.gateway.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)

    def test_failed_task_keeps_diagnostics_out_of_chat(self):
        def unavailable(*args):
            raise RuntimeFailure('runtime_terminal_missing','unknown')
        self.runtime.run = unavailable
        self.task(1, '处理文件')
        self.gateway.flush()
        reply, = self.api.sends.values()
        self.assertEqual(reply['text'], '暂时无法确认任务是否完成。请先核对已有结果，再决定是否继续。')
        state = self.gateway.db.execute('SELECT state,error FROM jobs').fetchone()
        self.assertEqual(tuple(state), ('failed','runtime_terminal_missing'))

    def test_invalid_mode_fails_before_creating_state(self):
        other = self.root/'uncreated'
        with self.assertRaisesRegex(ValueError, 'chatPresentation'):
            Gateway(other, self.route, None, {**self.settings,'chatPresentation':'prodcut'}, self.api, self.runtime)
        self.assertFalse(other.exists())

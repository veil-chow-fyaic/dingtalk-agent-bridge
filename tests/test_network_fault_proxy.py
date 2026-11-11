import asyncio
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts.network_fault_proxy import TunnelProxy


class NetworkFaultProxyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        async def echo(reader, writer):
            try:
                while data := await reader.read(65536):
                    writer.write(data); await writer.drain()
            finally:
                writer.close(); await writer.wait_closed()
        self.echo = await asyncio.start_server(echo, '127.0.0.1', 0)
        self.destination = self.echo.sockets[0].getsockname()[1]
        self.proxy = TunnelProxy(self.folder, [('127.0.0.1', self.destination)])
        self.server = await asyncio.start_server(self.proxy.handle, '127.0.0.1', 0)
        self.port = self.server.sockets[0].getsockname()[1]
        self.enforce = asyncio.create_task(self.proxy.enforce())
        self.writers = []

    async def asyncTearDown(self):
        for writer in self.writers:
            writer.close(); await writer.wait_closed()
        self.enforce.cancel(); await asyncio.gather(self.enforce, return_exceptions=True)
        for server in (self.server, self.echo):
            server.close(); await server.wait_closed()
        await asyncio.sleep(.05)
        self.temp.cleanup()

    async def connect(self, destination=None):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        self.writers.append(writer)
        target = destination or f'127.0.0.1:{self.destination}'
        writer.write(f'CONNECT {target} HTTP/1.1\r\nProxy-Authorization: never-log-me\r\n\r\n'.encode())
        await writer.drain()
        header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 2)
        return reader, writer, header

    def fault(self, start, end):
        (self.folder / 'offline.json').write_text(json.dumps({'startedAt': start, 'expiresAt': end}))

    async def test_cut_active_tunnel_deny_new_then_restore_without_payload_logging(self):
        reader, writer, header = await self.connect(); self.assertIn(b'200', header)
        payload = bytes(range(256)) + b'secret-test-data'
        writer.write(payload); await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(payload)), 2), payload)
        self.fault(time.time(), time.time() + 30)
        self.assertEqual(await asyncio.wait_for(reader.read(1), 2), b'')
        _, _, blocked = await self.connect(); self.assertIn(b'503', blocked)
        (self.folder / 'offline.json').unlink()
        _, _, restored = await self.connect(); self.assertIn(b'200', restored)
        logs = (self.folder / 'proxy.ndjson').read_text()
        self.assertIn('closed_on_fault', logs)
        self.assertNotIn('secret-test-data', logs); self.assertNotIn('never-log-me', logs)

    async def test_fault_auto_expires(self):
        self.fault(time.time() - 2, time.time() - 1)
        _, _, header = await self.connect(); self.assertIn(b'200', header)

    async def test_wrong_destination_denied(self):
        self.proxy.domains = ('approved.invalid',)
        _, _, header = await self.connect('unapproved.invalid:443')
        self.assertIn(b'403', header); self.assertEqual(self.proxy.next_id, 0)

    async def test_malformed_or_unbounded_fault_fails_closed(self):
        (self.folder / 'offline.json').write_text('broken')
        _, _, header = await self.connect(); self.assertIn(b'503', header)
        self.fault(time.time(), time.time() + 1000)
        _, _, header = await self.connect(); self.assertIn(b'503', header)

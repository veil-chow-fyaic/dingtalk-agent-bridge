#!/usr/bin/env python3
"""Loopback-only CONNECT tunnel for explicit, bounded network acceptance tests.

No TLS interception, payload/headers/credentials logging, or system proxy changes.
Only caller-selected hosts/domains on port 443 are allowed. Removing/expiring offline.json
restores new connections; existing tunnels are closed when the fault starts.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import time


class TunnelProxy:
    def __init__(self, folder, allowed, domains=()):
        self.folder = Path(folder)
        self.allowed = set(allowed)
        self.domains = tuple(domains)
        self.connections = {}
        self.next_id = 0
        self.server = None

    def record(self, event, **fields):
        with (self.folder / 'proxy.ndjson').open('a') as out:
            out.write(json.dumps({'at': time.time(), 'event': event, **fields}) + '\n')

    def offline(self):
        try:
            value = json.loads((self.folder / 'offline.json').read_text())
        except FileNotFoundError:
            return False
        # A malformed flag fails closed; operator must remove it explicitly.
        except (ValueError, OSError):
            return True
        start, end = value.get('startedAt'), value.get('expiresAt')
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not 0 < end - start <= 180:
            return True
        return start <= time.time() < end

    async def pipe(self, reader, writer):
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()

    async def handle(self, reader, client):
        upstream = None
        tasks = []
        ident = None
        try:
            head = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
            if len(head) > 8192:
                return
            method, target, version = head.split(b'\r\n', 1)[0].decode('ascii').split()
            host, port = target.rsplit(':', 1)
            port = int(port)
            allowed = (host, port) in self.allowed or port == 443 and any(host == d or host.endswith('.' + d) for d in self.domains)
            if method != 'CONNECT' or version != 'HTTP/1.1' or not allowed:
                client.write(b'HTTP/1.1 403 Forbidden\r\n\r\n'); await client.drain()
                self.record('denied_destination', host=host, port=port)
                return
            if self.offline():
                client.write(b'HTTP/1.1 503 Service Unavailable\r\n\r\n'); await client.drain()
                self.record('denied_offline', host=host, port=port)
                return
            remote, upstream = await asyncio.wait_for(asyncio.open_connection(host, port), 10)
            # Fault could have started during DNS/connect.
            if self.offline():
                self.record('denied_after_connect', host=host, port=port)
                return
            self.next_id += 1
            ident = self.next_id
            self.connections[ident] = (client, upstream)
            self.record('opened', connection=ident, host=host, port=port)
            client.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            await client.drain()
            tasks = [asyncio.create_task(self.pipe(reader, upstream)), asyncio.create_task(self.pipe(remote, client))]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except (OSError, ValueError, asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            self.record('connection_error')
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            for writer in (client, upstream):
                if writer:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except OSError:
                        pass
            if ident is not None:
                self.connections.pop(ident, None)
                self.record('closed', connection=ident)

    async def enforce(self):
        previous = False
        while True:
            blocked = self.offline()
            if blocked != previous:
                self.record('fault_started' if blocked else 'fault_ended')
                previous = blocked
            if blocked:
                for ident, writers in list(self.connections.items()):
                    if not writers[0].is_closing():
                        self.record('closed_on_fault', connection=ident)
                        for writer in writers:
                            writer.close()
            await asyncio.sleep(.1)

    async def run(self):
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.server = await asyncio.start_server(self.handle, '127.0.0.1', 0, limit=8192)
        port = self.server.sockets[0].getsockname()[1]
        (self.folder / 'proxy-state.json').write_text(json.dumps({'pid': os.getpid(), 'port': port, 'startedAt': time.time()}) + '\n')
        task = asyncio.create_task(self.enforce())
        stop = asyncio.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_running_loop().add_signal_handler(sig, stop.set)
        try:
            await stop.wait()
        finally:
            self.server.close(); await self.server.wait_closed()
            task.cancel(); await asyncio.gather(task, return_exceptions=True)
            for writers in list(self.connections.values()):
                for writer in writers:
                    writer.close()
            self.record('proxy_stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', required=True)
    parser.add_argument('--host', action='append', default=[], help='Exact permitted TLS hostname; repeat as needed')
    parser.add_argument('--domain', action='append', default=[], help='Explicit permitted TLS domain and its subdomains')
    args = parser.parse_args()
    os.umask(0o077)
    if not (args.host or args.domain) or any('/' in h or ':' in h or not h or h.startswith('.') for h in args.host + args.domain):
        parser.error('Hosts must be exact hostnames without port or URL')
    asyncio.run(TunnelProxy(args.folder, [(h, 443) for h in args.host], args.domain).run())

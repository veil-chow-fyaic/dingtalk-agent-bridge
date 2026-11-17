"""The local transport bind is independent of host-name resolution."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import unittest
from unittest.mock import patch

from dingtalk_bridge.__main__ import LoopbackHTTPServer


class LoopbackServerTests(unittest.TestCase):
    def test_ephemeral_bind_retains_socket_options_and_actual_port_without_dns(self):
        with patch('socket.getfqdn', side_effect=AssertionError('forbidden hostname lookup')) as fqdn, \
                patch('socket.gethostbyaddr', side_effect=AssertionError('forbidden reverse lookup')) as reverse:
            with LoopbackHTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler) as server:
                self.assertIsInstance(server, ThreadingHTTPServer)
                self.assertEqual(server.server_address, server.socket.getsockname())
                self.assertEqual(server.server_name, '127.0.0.1')
                self.assertEqual(server.server_port, server.server_address[1])
                self.assertGreater(server.server_port, 0)
                self.assertNotEqual(server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0)
            self.assertEqual(server.socket.fileno(), -1)
            fqdn.assert_not_called(); reverse.assert_not_called()

    def test_nonliteral_or_nonloopback_bind_is_rejected_before_dns(self):
        with patch('socket.getfqdn', side_effect=AssertionError('forbidden hostname lookup')) as fqdn:
            for host in ('0.0.0.0', 'localhost', '192.0.2.1'):
                with self.subTest(host=host), self.assertRaisesRegex(ValueError, 'literal 127.0.0.1'):
                    LoopbackHTTPServer((host, 0), BaseHTTPRequestHandler)
            fqdn.assert_not_called()

    def test_occupied_requested_port_still_fails_instead_of_selecting_another(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0)); occupied.listen(1)
            with self.assertRaises(OSError):
                LoopbackHTTPServer(occupied.getsockname(), BaseHTTPRequestHandler)


if __name__ == '__main__':
    unittest.main()

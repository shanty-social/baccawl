import os
import tempfile
import socket
import unittest
from io import BytesIO

from conduit_client.server import (
    SSHManagerClient, SSHManagerServer, Command, DomainCommand, TunnelCommand,
)


class BytesSocket(BytesIO):
    def recv(self, num=None):
        return self.read(num)


class CommandTestCase(unittest.TestCase):
    SOCKET_TUNNEL = BytesSocket(
        b'\x7f\x00\x80\x04\x95t\x00\x00\x00\x00\x00\x00\x00\x8c\x15conduit_'
        b'client.server\x94\x8c\rTunnelCommand\x94\x93\x94)\x81\x94}\x94(\x8c'
        b'\x07command\x94K\x02\x8c\x07address\x94\x8c\x0810.0.1.2\x94\x8c\x04'
        b'port\x94M\xd2\x04\x8c\x06domain\x94\x8c\nfoobar.com\x94ub.'
    )
    SOCKET_DOMAIN = BytesSocket(
        b'\x92\x00\x80\x04\x95\x87\x00\x00\x00\x00\x00\x00\x00\x8c\x15conduit_'
        b'client.server\x94\x8c\rDomainCommand\x94\x93\x94)\x81\x94}\x94(\x8c'
        b'\x07command\x94K\x02\x8c\x06domain\x94\x8c\nfoobar.com\x94\x8c\t'
        b'arguments\x94}\x94(\x8c\x08username\x94\x8c\x03foo\x94\x8c\x08'
        b'password\x94\x8c\x03bar\x94uub.'
    )

    def test_pack_tunnel(self):
        packed = TunnelCommand(
            Command.COMMAND_ADD,
            '10.0.1.2',
            1234,
            'foobar.com'
        ).pack()
        reference = self.SOCKET_TUNNEL.getvalue()
        self.assertEqual(len(reference), len(packed))
        self.assertEqual(reference, packed)

    def test_unpack_tunnel(self):
        command = Command.unpack(self.SOCKET_TUNNEL)
        self.assertIsInstance(command, TunnelCommand)
        self.assertEqual(command.address, '10.0.1.2')
        self.assertEqual(command.port, 1234)
        self.assertEqual(command.domain, 'foobar.com')

    def test_pack_domain(self):
        packed = DomainCommand(
            Command.COMMAND_ADD,
            'foobar.com',
            {
                'username': 'foo',
                'password': 'bar',
            }
        ).pack()
        reference = self.SOCKET_DOMAIN.getvalue()
        self.assertEqual(len(reference), len(packed))
        self.assertEqual(reference, packed)

    def test_unpack_domain(self):
        command = Command.unpack(self.SOCKET_DOMAIN)
        self.assertIsInstance(command, DomainCommand)
        self.assertEqual(command.domain, 'foobar.com')
        self.assertEqual(
            command.arguments,
            {
                'username': 'foo',
                'password': 'bar',
            }
        )


class ServerTestCase(unittest.TestCase):
    def test_shutdown(self):
        path = tempfile.mktemp()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(path)
            sock.listen()
            s = SSHManagerServer(path)
            client, _ = sock.accept()
            try:
                Command(Command.COMMAND_NOOP).send(client)
                self.assertTrue(s._queue.get())
            finally:
                client.close()


class ClientTestCase(unittest.TestCase):
    def test_start(self):
        client = SSHManagerClient()
        client.ping()
        client.disconnect()
        self.assertIsNone(client._server)

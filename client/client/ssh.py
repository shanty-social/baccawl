import os
import threading
import logging
import socket
from select import select
from os.path import isfile

import paramiko


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

SSH_KEY = os.getenv('SSH_KEY', '/etc/sshc/ssh.key')
SSH_HOST = os.getenv('SSH_HOST', 'homeland-social.com')
SSH_PORT = int(os.getenv('SSH_PORT', 2222))
SSH_USER = os.getenv('SSH_USER', 'default')
BUFFER_SIZE = 1024 * 32
DISABLED_ALGORITHMS = dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"])
MANAGER = None


def _forward(server, channel):
    LOGGER.debug('Tunnel opened')
    try:
        while True:
            r = select([server, channel], [], [])[0]
            if server in r:
                data = server.recv(1024)
                if len(data) == 0:
                    break
                channel.send(data)
            if channel in r:
                data = channel.recv(1024)
                if len(data) == 0:
                    break
                server.send(data)

    finally:
        channel.close()
        server.close()
        LOGGER.debug('Tunnel closed')


def _create_forward_handler(domain, addr, port):
    def _handler(channel, src_addr, dst_addr):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LOGGER.debug('connecting to %s:%i for %s', addr, port, domain)
        server.connect((addr, port))

        t = threading.Thread(
            target=_forward, args=(server, channel), daemon=True)
        t.start()

    return _handler


class SSHManager:
    def __init__(self, host, port, user, key):
        self._host = host
        self._port = port
        self._user = user
        self._key = key
        self._ssh = None
        self._tunnels = {}

    @property
    def connected(self):
        return self._ssh is not None

    @property
    def transport(self):
        return self._ssh.get_transport()

    @property
    def tunnels(self):
        return self._tunnels

    def connect(self):
        if self.connected:
            return
        LOGGER.debug(
            'Establishing ssh connection to: %s:%i', self._host, self._port)
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        try:
            self._ssh.connect(
                hostname=self._host, port=self._port, username=self._user,
                pkey=self._key, look_for_keys=False,
                disabled_algorithms=DISABLED_ALGORITHMS
            )

        except paramiko.SSHException:
            self._ssh = None
            raise

        LOGGER.debug('Established ssh connection')
        self.transport.set_keepalive(30)

        for domain, (addr, port, _) in self._tunnels.items():
            remote_port = self._setup_tunnel(domain, addr, port)
            self._tunnels[domain] = (addr, port, remote_port)

    def disconnect(self):
        if not self.connected:
            return
        self._ssh.close()
        self._ssh = None

    def _check_connection(self):
        if not self.connected:
            self.connect()
        if not self.transport.is_alive():
            self.disconnect()
            self.connect()

        try:
            self.transport.send_ignore()

        except EOFError:
            self.disconnect()
            self.connect()

    def _setup_tunnel(self, domain, addr, port):
        self.transport.open_session()
        remote_port = self.transport.request_port_forward(
            '0.0.0.0',
            0,
            _create_forward_handler(domain, addr, port)
        )
        try:
            self._ssh.exec_command(f'tunnel {domain} {remote_port}')

        except Exception:
            LOGGER.exception('error adding tunnel')
            raise

        return remote_port

    def add_tunnel(self, domain, addr, port):
        try:
            self._check_connection()

        except paramiko.SSHException:
            return

        remote_port = self._setup_tunnel(domain, addr, port)
        self._tunnels[domain] = (addr, port, remote_port)

    def del_tunnel(self, domain):
        (_, _, remote_port) = self._tunnels.pop(domain)
        self.transport.cancel_port_forward('0.0.0.0', remote_port)

    def poll(self):
        try:
            self._check_connection()

        except paramiko.SSHException:
            return


def load_key(path=None):
    "Generate a client key for use with the library."
    if path is not None:
        if isfile(path):
            LOGGER.debug('Loading key from: %s', path)
            return paramiko.RSAKey.from_private_key_file(path)
    LOGGER.debug('Saving new to key: %s', path)
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(path)
    return key


def add_tunnel(*args):
    global MANAGER
    if MANAGER is None:
        MANAGER = SSHManager(
            host=SSH_HOST, port=SSH_PORT, user=SSH_USER, key=load_key(SSH_KEY))
    MANAGER.add_tunnel(*args)


def del_tunnel(*args):
    global MANAGER
    if MANAGER is None:
        return
    MANAGER.del_tunnel(*args)
    if len(MANAGER.tunnels) == 0:
        MANAGER.disconnect()
        MANAGER = None


def poll():
    if MANAGER is None:
        return
    MANAGER.poll()

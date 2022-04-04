import os
import threading
import logging
import socket
from select import select
from os.path import isfile

import paramiko


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

SSH_KEY_FILE = os.getenv('SSH_KEY_FILE', None)
SSH_HOST_KEYS_FILE = os.getenv('SSH_HOST_KEYS_FILES', None)
SSH_HOST = os.getenv('SSH_HOST', 'ssh.homeland-social.com')
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
        if SSH_HOST_KEYS_FILE:
            self._ssh.load_host_keys(SSH_HOST_KEYS_FILE)
            self._ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
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
            self._setup_tunnel(domain, addr, port)

    def disconnect(self):
        if not self.connected:
            return
        self._ssh.close()
        self._ssh = None

    def _check_connection(self, connect=False):
        if not connect and len(self.tunnels) == 0:
            self.disconnect()
            return
        if not self.connected:
            self.connect()
        if not self.transport.is_alive():
            self.disconnect()

        try:
            self.transport.send_ignore()

        except EOFError:
            self.disconnect()

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

        self._tunnels[domain] = (addr, port, remote_port)

    def add_tunnel(self, domain, addr, port):
        # Check if there is an existing tunnel for this domain.
        existing = self._tunnels.get(domain)
        if existing:
            if existing[:2] == [addr, port]:
                # Same don't make any change.
                return
            self.del_tunnel(domain)
        self._check_connection(connect=True)
        self._setup_tunnel(domain, addr, port)

    def del_tunnel(self, domain):
        try:
            remote_port = self._tunnels.pop(domain)[2]
        except KeyError:
            return
        self.transport.cancel_port_forward('0.0.0.0', remote_port)

    def poll(self):
        try:
            self._check_connection()

        except paramiko.SSHException:
            return


def load_key(path=SSH_KEY_FILE):
    "Generate a client key for use with the library."
    if path is not None:
        if isfile(path):
            LOGGER.debug('Loading key from: %s', path)
            return paramiko.RSAKey.from_private_key_file(path)
    LOGGER.info('Generating new private key')
    key = paramiko.RSAKey.generate(2048)
    if path is not None:
        LOGGER.debug('Saving new to key: %s', path)
        key.write_private_key_file(path)
    return key


def save_host_keys(keys, path=SSH_HOST_KEYS_FILE):
    "Saves host keys where ssh client will look for them."
    if path is None:
        raise FileNotFoundError('SSH_HOST_KEYS_FILE file not defined')
    with open(path, 'w') as f:
        f.write('\n'.join(keys))


def create_manager(host=SSH_HOST, port=SSH_PORT, user=SSH_USER, key=None):
    if key is None:
        key = SSH_KEY_FILE
    if isinstance(key, str):
        key = load_key(key)
    return SSHManager(host, port, user, key=key)

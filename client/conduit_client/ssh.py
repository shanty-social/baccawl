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


class Tunnel:
    def __init__(self, domain, addr=None, port=None, remote_port=None):
        self.domain = domain
        self.addr = addr
        self.port = port
        self.remote_port = remote_port

    def __str__(self):
        remote_port = f', remote_port={self.remote_port}' \
            if self.remote_port else ''
        return (f'Tunnel, domain: {self.domain}, addr: {self.addr}:{self.port}'
                f'{remote_port}')

    def __eq__(self, other):
        return self.domain == other.domain and \
               self.addr == other.addr and \
               self.port == other.port


class Forwarder:
    "Uses select to forward data over tunnels."
    def __init__(self):
        self._handles = {}
        self._event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _close(self, *socks):
        for s in socks:
            try:
                s.close()
            except socket.error:
                pass
            self._handles.pop(s, None)

    def _run(self):
        while True:
            if not self._handles and self._event.wait():
                self._event.clear()
            for r in select(self._handles, [], [])[0]:
                try:
                    s = self._handles[r]
                except KeyError:
                    continue
                try:
                    data = r.recv(BUFFER_SIZE)
                except socket.error:
                    self._close(r, s)
                    continue
                if len(data) == 0:
                    self._close(r, s)
                    continue
                s.send(data)

    def create_handler(self, domain, addr, port):
        def _handler(channel, *args):
            LOGGER.debug('connecting to %s:%i for %s', addr, port, domain)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.connect((addr, port))
            self._handles[server] = channel
            self._handles[channel] = server
            self._event.set()
        return _handler


class SSHManager:
    def __init__(self, host, port, user, key):
        self._host = host
        self._port = port
        self._user = user
        self._key = key
        self._ssh = None
        self._tunnels = {}
        self._forwarder = Forwarder()

    @property
    def connected(self):
        if self._ssh is None:
            return False

        try:
            if not self.transport.is_alive():
                LOGGER.debug('Transport not alive')
                self.disconnect()
                return False

            self.transport.send_ignore()
            return True

        except Exception:
            LOGGER.exception('Not connected')
            self.disconnect()
            return False

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
        self.transport.open_session()

        for tunnel in self._tunnels.values():
            self._setup_tunnel(tunnel)

    def disconnect(self):
        if not self.connected:
            return
        LOGGER.info('Disconnecting from: %s:%i', self._host, self._port)
        self._ssh.close()
        self._ssh = None

    def _check_connection(self, connect=False):
        if not connect and len(self.tunnels) == 0:
            self.disconnect()
            return
        self.connect()

    def _setup_tunnel(self, tunnel):
        tunnel.remote_port = self.transport.request_port_forward(
            '0.0.0.0',
            0,
            self._forwarder.create_handler(
                tunnel.domain, tunnel.addr, tunnel.port),
        )
        try:
            self._ssh.exec_command(
                f'tunnel {tunnel.domain} {tunnel.remote_port}')

        except Exception:
            LOGGER.exception('error adding tunnel')
            raise

        self._tunnels[tunnel.domain] = tunnel

    def add_tunnel(self, tunnel):
        # Check if there is an existing tunnel for this domain.
        existing = self._tunnels.get(tunnel.domain)
        if existing:
            LOGGER.debug(
                'Comparing tunnels: (%s) == (%s)',
                tunnel, existing,
            )
            if existing == tunnel:
                LOGGER.debug('Matched, leaving')
                return
            self.del_tunnel(tunnel)
        # NOTE: Connection must be up in order to add tunnel.
        self._check_connection(connect=True)
        self._setup_tunnel(tunnel)

    def del_tunnel(self, tunnel):
        try:
            tunnel = self._tunnels.pop(tunnel.domain)
        except KeyError:
            return
        self.transport.cancel_port_forward('0.0.0.0', tunnel.remote_port)

    def list_tunnels(self):
        return self._tunnels.values()

    def poll(self):
        try:
            self._check_connection()

        except Exception:
            LOGGER.exception('Error polling')
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
    keys = set(keys)
    with open(path, 'r') as f:
        existing = set(f.read().split('\n'))
    with open(path, 'a') as f:
        f.write('\n'.join(keys.difference(existing)))


def create_manager(host=SSH_HOST, port=SSH_PORT, user=SSH_USER, key=None):
    if key is None:
        key = SSH_KEY_FILE
    if isinstance(key, str):
        key = load_key(key)
    return SSHManager(host, port, user, key=key)

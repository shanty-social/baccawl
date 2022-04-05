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
            if not self._handles:
                self._event.wait()
                self._event.clear()
            for r in select(self._handles, [], [])[0]:
                try:
                    s = self._handles[r]
                except KeyError:
                    continue
                data = r.recv(1024)
                if len(data) == 0:
                    self._close(r, s)
                else:
                    s.send(data)

    def create_handler(self, domain, addr, port):
        def _handler(channel, src_addr, dst_addr):
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            LOGGER.debug('connecting to %s:%i for %s', addr, port, domain)
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
                self.disconnect()
                return False

        except Exception:
            LOGGER.exception('Not connected')
            return False

        try:
            self.transport.send_ignore()

        except EOFError:
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
        self.connect()

    def _setup_tunnel(self, domain, addr, port):
        self.transport.open_session()
        remote_port = self.transport.request_port_forward(
            '0.0.0.0',
            0,
            self._forwarder.create_handler(domain, addr, port),
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
            LOGGER.debug(
                'Comparing tunnels: (%s:%i) == (%s:%i)',
                addr,
                port,
                *existing[:2],
            )
            if existing[:2] == [addr, port]:
                LOGGER.debug('Matched, leaving')
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

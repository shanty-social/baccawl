import os
import subprocess
import shutil
import queue
import socket
import struct
import pickle
import tempfile
import threading
import logging
from select import select
from os.path import dirname, basename

from conduit_client import ssh


PYTHON = shutil.which('python3')
MODULE_PATH = dirname(dirname(__file__))
MODULE_NAME = basename(dirname(__file__))

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.NullHandler())


def _set_if_not_none(d, key, value):
    value = value if value is not None else os.getenv(key)
    if value is None:
        return
    d[key] = value


class Command:
    COMMAND_NOOP = 0
    COMMAND_DEL = 1
    COMMAND_ADD = 2
    COMMAND_STOP = 3

    COMMANDS = {
        COMMAND_NOOP: 'noop',
        COMMAND_DEL: 'del',
        COMMAND_ADD: 'add',
        COMMAND_STOP: 'stop',
    }

    def __init__(self, command):
        self.command = command

    def __str__(self):
        return f'{self.__class__.__name__}: command={self.name}'

    @property
    def name(self):
        return self.COMMANDS[self.command]

    @staticmethod
    def unpack(s, timeout=None):
        if timeout:
            r = select([s], [], [], timeout)[0]
            if s not in r:
                raise TimeoutError('Socket not readable')
        size = struct.unpack('H', s.recv(2))[0]
        return pickle.loads(s.recv(size))

    def pack(self):
        data = pickle.dumps(self)
        return struct.pack('H', len(data)) + data

    def send(self, s):
        s.send(self.pack())

    def apply(self, manager):
        pass


class DomainCommand(Command):
    def __init__(self, command, domain, arguments):
        super().__init__(command)
        self.domain = domain
        self.arguments = arguments


class TunnelCommand(Command):
    def __init__(self, command, address, port, domain):
        super().__init__(command)
        self.address = address
        self.port = port
        self.domain = domain

    def apply(self, manager):
        if self.command == Command.COMMAND_ADD:
            manager.add_tunnel(self.domain, self.address, self.port)
        elif self.command == Command.COMMAND_DEL:
            manager.del_tunnel(self.domain)


class SSHManagerServer:
    def __init__(self, sock_name):
        self._sock_name = sock_name
        self._queue = queue.Queue()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.connect(self._sock_name)

            while True:
                try:
                    cmd = Command.unpack(s)

                except Exception:
                    LOGGER.exception('Error reading command.')
                    continue

                LOGGER.debug('Received command: %s, acking', cmd)
                Command(Command.COMMAND_NOOP).send(s)

                if cmd.command == Command.COMMAND_STOP:
                    LOGGER.info('Exiting')
                    os._exit(0)

                self._queue.put(cmd)

        finally:
            s.close()

    def run_forever(self):
        manager = ssh.create_manager()
        while True:
            manager.poll()
            try:
                command = self._queue.get(timeout=10.0)
            except queue.Empty:
                continue
            if not isinstance(command, TunnelCommand):
                continue
            command.apply(manager)


class SSHManagerClient:
    def __init__(self, host=None, port=None, user=None, key=None):
        self._env = {}
        _set_if_not_none(self._env, 'SSH_HOST', host)
        _set_if_not_none(self._env, 'SSH_PORT', port)
        _set_if_not_none(self._env, 'SSH_USER', user)
        _set_if_not_none(self._env, 'SSH_KEY_FILE', key)
        self._sock_name = None
        self._listen = None
        self._socket = None
        self._server = None

    def __del__(self):
        self.close()

    def close(self):
        if self._socket:
            self._socket.close()
            self._socket = None
        if self._listen:
            self._listen.close()
            self._listen = None

    def _start_server(self):
        self._sock_name = tempfile.mktemp()
        self._listen = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._listen.bind(self._sock_name)
        self._listen.listen()
        self._server = subprocess.Popen(
            [PYTHON, '-m', MODULE_NAME, self._sock_name],
            cwd=MODULE_PATH,
            env=self._env
        )
        self._socket, _ = self._listen.accept()

    def disconnect(self, timeout=None):
        self._send_command(Command(Command.COMMAND_STOP))
        self.close()
        os.remove(self._sock_name)
        self._server.wait(timeout)
        self._server = None

    def _send_command(self, cmd):
        if self._server is None:
            self._start_server()
        cmd.send(self._socket)
        r = Command.unpack(self._socket, timeout=1.0)
        assert r.command == Command.COMMAND_NOOP, 'Missing acknowledgment'

    def ping(self):
        self._send_command(Command(Command.COMMAND_NOOP))

    def add_tunnel(self, domain, address, port):
        self._send_command(
            TunnelCommand(Command.COMMAND_ADD, address, port, domain)
        )

    def del_tunnel(self, domain):
        self._send_command(
            TunnelCommand(Command.COMMAND_DEL, None, None, domain)
        )


def start_server(sock_name):
    LOGGER.addHandler(logging.StreamHandler())
    LOGGER.setLevel(logging.DEBUG)

    server = SSHManagerServer(sock_name)
    server.run_forever()

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
from conduit_client.ssh import Tunnel


PYTHON = shutil.which('python3')
MODULE_PATH = dirname(dirname(__file__))
MODULE_NAME = basename(dirname(__file__))

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.NullHandler())


def _set_if_not_none(d, key, value):
    value = value if value is not None else os.getenv(key)
    if value is None:
        return
    d[key] = str(value)


class Command:
    COMMAND_NOOP = 0
    COMMAND_DEL = 1
    COMMAND_ADD = 2
    COMMAND_STOP = 3
    COMMAND_LIST = 4

    COMMANDS = {
        COMMAND_NOOP: 'noop',
        COMMAND_DEL: 'del',
        COMMAND_ADD: 'add',
        COMMAND_STOP: 'stop',
        COMMAND_LIST: 'list',
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
        data = s.recv(2)
        if not data:
            raise EOFError()
        size = struct.unpack('H', data)[0]
        return pickle.loads(s.recv(size))

    def pack(self):
        data = pickle.dumps(self)
        return struct.pack('H', len(data)) + data

    def send(self, s):
        s.send(self.pack())

    def apply(self, manager, server):
        pass


class DomainCommand(Command):
    def __init__(self, command, domain, arguments):
        super().__init__(command)
        self.domain = domain
        self.arguments = arguments


class ListCommand(Command):
    def apply(self, manager, socket):
        for tunnel in manager.tunnels.values():
            TunnelCommand(COMMAND_ADD, tunnel).send(socket)


class TunnelCommand(Command):
    def __init__(self, command, tunnel):
        super().__init__(command)
        self.tunnel = tunnel

    def apply(self, manager, socket):
        if self.command == Command.COMMAND_ADD:
            manager.add_tunnel(self.tunnel)
        elif self.command == Command.COMMAND_DEL:
            manager.del_tunnel(self.tunnel)


class SSHManagerServer:
    def __init__(self, sock_name):
        self._sock_name = sock_name
        self._queue = queue.Queue()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()
        self._manager = ssh.create_manager()

    def _read(self):
        noop = Command(Command.COMMAND_NOOP)
        try:
            self._socket.connect(self._sock_name)

            while True:
                try:
                    cmd = Command.unpack(self._socket)

                except EOFError:
                    LOGGER.error('EOF encountered, exiting')
                    os._exit(1)

                except Exception:
                    LOGGER.exception('Error reading command.')
                    continue

                LOGGER.debug('Received command: %s, acking', cmd)

                if cmd.command == Command.COMMAND_LIST:
                    cmd.apply(self._manager, self._socket)
                    noop.send(self._socket)
                    continue

                elif cmd.command == Command.COMMAND_STOP:
                    LOGGER.info('Exiting')
                    os._exit(0)

                noop.send(self._socket)
                self._queue.put(cmd)

        finally:
            self._socket.close()

    def run_forever(self):
        while True:
            self._manager.poll()
            try:
                command = self._queue.get(timeout=10.0)
            except queue.Empty:
                continue
            if not isinstance(command, TunnelCommand):
                continue
            try:
                command.apply(self._manager, self._socket)
            except Exception:
                LOGGER.exception('Error handling command')


class SSHManagerClient:
    def __init__(self, host=None, port=None, user=None, key=None,
                 host_keys=None):
        self._env = {}
        _set_if_not_none(self._env, 'SSH_HOST', host)
        _set_if_not_none(self._env, 'SSH_PORT', port)
        _set_if_not_none(self._env, 'SSH_USER', user)
        _set_if_not_none(self._env, 'SSH_KEY_FILE', key)
        _set_if_not_none(self._env, 'SSH_HOST_KEYS_FILE', host_keys)
        self._sock_name = None
        self._listen = None
        self._socket = None
        self._server = None
        self._lock = threading.Lock()

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
        if self._server is not None and self._server.poll() is None:
            return
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
        try:
            self._send_command(Command(Command.COMMAND_STOP))
        except EOFError:
            pass
        self.close()
        os.remove(self._sock_name)
        self._server.wait(timeout)
        self._server = None

    def _send_command(self, cmd):
        reply = []
        self._lock.acquire(timeout=1.0)
        try:
            self._start_server()
            cmd.send(self._socket)

            while True:
                cmd = Command.unpack(self._socket, timeout=1.0)
                if cmd.command == Command.COMMAND_NOOP:
                    break
                reply.append(cmd)

            return reply

        finally:
            self._lock.release()

    def ping(self):
        self._send_command(Command(Command.COMMAND_NOOP))

    def add_tunnel(self, tunnel):
        self._send_command(
            TunnelCommand(
                Command.COMMAND_ADD, tunnel)
        )

    def del_tunnel(self, domain):
        self._send_command(
            TunnelCommand(Command.COMMAND_DEL, tunnel)
        )

    def list_tunnels(self):
        reply = self._send_command(
            ListCommand(Command.COMMAND_LIST)
        )
        return [r.tunnel for r in reply]

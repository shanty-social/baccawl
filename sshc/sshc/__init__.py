import os
import time
import threading
import logging
import socket
from select import select

import paramiko


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

CONDUIT_HOST = os.getenv('CONDUIT_HOST', 'homeland-social.com')
CONDUIT_PORT = int(os.getenv('CONDUIT_PORT', 2222))
BUFFER_SIZE = 1024**2


def gen_key():
    "Generate a client key for use with the library."
    pass


class Connection:
    def __init__(self, tunnel, channel):
        self._tunnel = tunnel
        self._channel = channel
        self._socket = None
        self._closing = False
        self._channel_done = False
        self._socket_done = False
        self._connect()

    def _connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LOGGER.debug('connecting to %s:%i', self._tunnel.addr, self._tunnel.port)
        self._socket.connect((self._tunnel.addr, self._tunnel.port))

    def close(self):
        self._channel.close()
        self._socket.close()

    def poll(self):
        total = 0
        if self._socket is None:
            return total
        while True:
            size = 0
            r, w, _ = select([self._socket], [self._socket], [], 0)
            if self._socket in r and self._channel.send_ready():
                data = self._socket.recv(BUFFER_SIZE)
                size += len(data)
                self._channel.sendall(data)
            if self._socket in w and self._channel.recv_ready():
                data = self._channel.recv(BUFFER_SIZE)
                size += len(data)
                self._socket.sendall(data)
            if size == 0:
                break
            total += size
        return total


class Tunnel:
    def __init__(self, client, hostname, addr, port):
        self._client = client
        self.hostname = hostname
        self.addr = addr
        self.port = port
        self._remote_port = None
        self._connections = []

    def _handle_connection(self, channel, src_addr, dst_addr):
        self._connections.append(Connection(self, channel))

    def _connect(self):
        if self._remote_port is not None:
            return
        LOGGER.debug('Establishing tunnel')
        ssh = self._client._ssh
        transport = ssh.get_transport()
        transport.open_session()
        self._remote_port = transport.request_port_forward(
            '0.0.0.0', 0, self._handle_connection)
        try:
            ssh.exec_command(f'open {self.hostname} {self.port}')

        except Exception as e:
            LOGGER.exception('error finalizing tunnel')

    def shutdown(self):
        self._client._ssh.cancel_port_forward(self._remote_port)
        while self._connections:
            self._connections.pop().close()

    def poll(self):
        "Moves data over connections."
        self._connect()
        data_moved = 0
        for conn in self._connections:
            try:
                data_moved += conn.poll()

            except Exception as e:
                LOGGER.exception('error polling connection')

        return data_moved


class SSHC:
    _check_interval = 30

    def __init__(self, uuid, key, host=CONDUIT_HOST, port=CONDUIT_PORT):
        self._ssh = None
        self._uuid = uuid
        self._key = key
        self._host = host
        self._port = port
        self._tunnels = {}
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._stop = False
        self._manager = threading.Thread(
            target=self._manage_connection, daemon=True)
        self._manager.start()

    def _connect(self):
        if self._ssh is not None:
            return
        LOGGER.debug('Establishing ssh connection')
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        self._ssh.connect(
            hostname=self._host, port=self._port, username=self._uuid,
            pkey=self._key, look_for_keys=False
        )
        LOGGER.debug('Established ssh connection')

    def _disconnect(self):
        if self._ssh is None:
            return
        self._ssh.close()
        self._ssh = None

    def _manage_connection(self):
        "Manages the SSH connection."
        while not self._stop:
            try:
                with self._lock:
                    tunnels = list(self._tunnels.values())

                if len(tunnels) == 0:
                    # No active tunnels, close SSH and wait for a new tunnel.
                    self._disconnect()
                    self._event.wait()
                    self._event.clear()

                else:
                    # We have active tunnels, ensure we are connected, then
                    # move data.
                    self._connect()
                    total = 0
                    for tunnel in tunnels:
                        try:
                            total += tunnel.poll()

                        except Exception as e:
                            LOGGER.exception('error polling tunnel')
                    if total:
                        # Data moved, try again.
                        continue
                    # We moved no data, so sleep a bit.
                    time.sleep(0.01)

            except Exception as e:
                LOGGER.exception('error in connection manager')

    def add_tunnel(self, hostname, addr, port):
        "Open a new tunnel for HTTP traffic."
        with self._lock:
            self._tunnels[hostname] = Tunnel(self, hostname, addr, port)
        self._event.set()

    def del_tunnel(self, hostname):
        "Close an existing tunnel."
        with self._lock:
            self._tunnels[hostname].shutdown()
            del self._tunnels[hostname]

    def stop(self):
        self._stop = True

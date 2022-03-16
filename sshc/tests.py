import unittest
import uuid
import logging
import socket
import time
import threading
from io import StringIO

from stopit import async_raise
import paramiko
from paramiko.py3compat import decodebytes

from sshc import SSHC


HOST_KEY_DATA = StringIO(
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIICWgIBAAKBgQDTj1bqB4WmayWNPB+8jVSYpZYk80Ujvj680pOTh2bORBjbIAyz\n"
    "oWGW+GUjzKxTiiPvVmxFgx5wdsFvF03v34lEVVhMpouqPAYQ15N37K/ir5XY+9m/\n"
    "d8ufMCkjeXsQkKqFbAlQcnWMCRnOoPHS3I4vi6hmnDDeeYTSRvfLbW0fhwIBIwKB\n"
    "gBIiOqZYaoqbeD9OS9z2K9KR2atlTxGxOJPXiP4ESqP3NVScWNwyZ3NXHpyrJLa0\n"
    "EbVtzsQhLn6rF+TzXnOlcipFvjsem3iYzCpuChfGQ6SovTcOjHV9z+hnpXvQ/fon\n"
    "soVRZY65wKnF7IAoUwTmJS9opqgrN6kRgCd3DASAMd1bAkEA96SBVWFt/fJBNJ9H\n"
    "tYnBKZGw0VeHOYmVYbvMSstssn8un+pQpUm9vlG/bp7Oxd/m+b9KWEh2xPfv6zqU\n"
    "avNwHwJBANqzGZa/EpzF4J8pGti7oIAPUIDGMtfIcmqNXVMckrmzQ2vTfqtkEZsA\n"
    "4rE1IERRyiJQx6EJsz21wJmGV9WJQ5kCQQDwkS0uXqVdFzgHO6S++tjmjYcxwr3g\n"
    "H0CoFYSgbddOT6miqRskOQF3DZVkJT3kyuBgU2zKygz52ukQZMqxCb1fAkASvuTv\n"
    "qfpH87Qq5kQhNKdbbwbmd2NxlNabazPijWuphGTdW0VfJdWfklyS2Kr+iqrs/5wV\n"
    "HhathJt636Eg7oIjAkA8ht3MQ+XSl9yIJIS8gVpbPxSw5OMfw0PjVE7tBdQruiSc\n"
    "nvuQES5C9BMHjF39LZiGH1iLQy7FgdHyoP+eodI7\n"
    "-----END RSA PRIVATE KEY-----"
)
HOST_KEY = paramiko.RSAKey(file_obj=HOST_KEY_DATA)

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.StreamHandler())


class CancelError(Exception):
    pass


class SSHServer(paramiko.ServerInterface):
    def __init__(self, test_server):
        self._test_server = test_server

    def check_channel_request(self, kind, channel_id):
        return paramiko.OPEN_SUCCEEDED
    
    def check_auth_password(self, username, password):
        LOGGER.debug('password auth')
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        LOGGER.debug('publickey auth')
        return paramiko.AUTH_SUCCESSFUL

    def check_port_forward_request(self, address, port):
        self._test_server.port_forward.set()
        LOGGER.debug('port forward request')
        return 1234

    def check_channel_exec_request(self, channel, command):
        self._test_server.exec_request.set()
        LOGGER.debug('exec request')
        return True

    def check_channel_shell_request(self, channel):
        LOGGER.debug('shell request')
        return True


class TestServer:
    def __init__(self, port=0):
        self._port = port
        self._socket = None
        self._thread = None
        self.started = threading.Event()
        self.client_connected = threading.Event()
        self.port_forward = threading.Event()
        self.exec_request = threading.Event()
        self.data_sent = threading.Event()
        self._start()

    @property
    def port(self):
        return self._port

    def _handle_client(self):
        client, addr = self._socket.accept()
        try:
            self.client_connected.set()
            t = paramiko.Transport(client)
            #t.set_gss_host(socket.getfqdn(''))
            try:
                t.load_server_moduli()

            except CancelError:
                raise

            except:
                LOGGER.exception('no moduli -- gex unsupported')

            t.add_server_key(HOST_KEY)
            t.start_server(server=SSHServer(self))
            LOGGER.debug('accepting')
            t.accept()

            self.exec_request.wait()
            self.port_forward.wait()

            c = t.open_forwarded_tcpip_channel(
                ('127.0.0.1', 4321), ('127.0.0.1', 1234))
            c.send('Hello world.')

            self.data_sent.set()

        finally:
            client.close()

    def _run(self):
        self.started.set()
        try:
            while True:
                try:
                    self._handle_client()

                except BlockingIOError:
                    time.sleep(0.001)
                    continue

                except CancelError:
                    return

                except Exception as e:
                    LOGGER.exception('failure handling client')

        finally:
            self._socket.close()

    def _start(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setblocking(False)
        self._socket.bind(('127.0.0.1', self._port))
        self._port = self._socket.getsockname()[1]
        self._socket.listen(100)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        async_raise(self._thread.ident, CancelError)
        self._thread.join()


class LocalHost:
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(('127.0.0.1', 0))
        self.port = self._socket.getsockname()[1]
        self.data_recv = threading.Event()
        self._socket.listen(100)
        self._thread = None
        self._buffer = b''
        self._start()

    def _run(self):
        while True:
            client, addr = self._socket.accept()
            self._buffer += client.recv(12)
            self.data_recv.set()

    def _start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()


class SSHServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = TestServer()
        self.server.started.wait()

    def tearDown(self):
        self.server.stop()


class SSHCTestCase(SSHServerTestCase):
    def test_sshc(self):
        l = LocalHost()
        c = SSHC(
            str(uuid.uuid4()), HOST_KEY, host='127.0.0.1', port=self.server.port)
        self.assertFalse(self.server.client_connected.is_set())
        c.add_tunnel('foo.com', '127.0.0.1', l.port)
        if not self.server.client_connected.wait(1):
            self.fail('Client did not connect')
        if not self.server.exec_request.wait(1):
            self.fail('Exec request not received')
        if not self.server.port_forward.wait(1):
            self.fail('Port forward not received')
        if not l.data_recv.wait(5):
            self.fail('Data not received')
        self.assertEqual(l._buffer, b'Hello world.')


unittest.main()

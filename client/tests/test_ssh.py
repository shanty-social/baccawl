import unittest
import threading
import socket
import logging
import select
import random
import asyncio
from io import StringIO

import paramiko

from conduit_client.ssh import SSH
from conduit_client.tunnel import Tunnel


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
HOST_KEY = paramiko.RSAKey(file_obj=StringIO('''-----BEGIN RSA PRIVATE KEY-----
MIICWgIBAAKBgQDTj1bqB4WmayWNPB+8jVSYpZYk80Ujvj680pOTh2bORBjbIAyz
oWGW+GUjzKxTiiPvVmxFgx5wdsFvF03v34lEVVhMpouqPAYQ15N37K/ir5XY+9m/
d8ufMCkjeXsQkKqFbAlQcnWMCRnOoPHS3I4vi6hmnDDeeYTSRvfLbW0fhwIBIwKB
gBIiOqZYaoqbeD9OS9z2K9KR2atlTxGxOJPXiP4ESqP3NVScWNwyZ3NXHpyrJLa0
EbVtzsQhLn6rF+TzXnOlcipFvjsem3iYzCpuChfGQ6SovTcOjHV9z+hnpXvQ/fon
soVRZY65wKnF7IAoUwTmJS9opqgrN6kRgCd3DASAMd1bAkEA96SBVWFt/fJBNJ9H
tYnBKZGw0VeHOYmVYbvMSstssn8un+pQpUm9vlG/bp7Oxd/m+b9KWEh2xPfv6zqU
avNwHwJBANqzGZa/EpzF4J8pGti7oIAPUIDGMtfIcmqNXVMckrmzQ2vTfqtkEZsA
4rE1IERRyiJQx6EJsz21wJmGV9WJQ5kCQQDwkS0uXqVdFzgHO6S++tjmjYcxwr3g
H0CoFYSgbddOT6miqRskOQF3DZVkJT3kyuBgU2zKygz52ukQZMqxCb1fAkASvuTv
qfpH87Qq5kQhNKdbbwbmd2NxlNabazPijWuphGTdW0VfJdWfklyS2Kr+iqrs/5wV
HhathJt636Eg7oIjAkA8ht3MQ+XSl9yIJIS8gVpbPxSw5OMfw0PjVE7tBdQruiSc
nvuQES5C9BMHjF39LZiGH1iLQy7FgdHyoP+eodI7
-----END RSA PRIVATE KEY-----'''))


class ServerImplementation(paramiko.ServerInterface):
    def __init__(self, server):
        self.server = server

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_publickey(self, username, key):
        #if (username == "robey") and (key == self.pub_key):
        return paramiko.AUTH_SUCCESSFUL
        #return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "publickey"

    def check_port_forward_request(self, address, port):
        return port or random.randint(1024, 65535)

    def cancel_port_forward_request(self, address, port):
        self.server.tunnel_closed.set()

    def check_channel_exec_request(self, channel, command):
        self.server.tunnel_opened.set()
        self.server.tunnels_opened.append(command)
        channel.send_exit_status(0)
        return True


class Server:
    def __init__(self, host='localhost', port=0):
        self._host = host
        self._port = port
        self._running = threading.Event()
        self._stopping = threading.Event()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.connected = threading.Event()
        self.authenticated = threading.Event()
        self.tunnel_opened = threading.Event()
        self.tunnel_closed = threading.Event()
        self.tunnels_opened = []

    @property
    def port(self):
        if not self._running.is_set():
            return None
        return self._server.getsockname()[1]

    def _reset(self):
        self.tunnel_opened.clear()
        self.tunnel_closed.clear()
        self.tunnels_opened = []
        self.authenticated.clear()
        self.connected.clear()

    def _run(self):
        try:
            self._server.bind((self._host, self._port))
            self._server.listen(100)
        except Exception as e:
            LOGGER.exception(e)
            return

        self._running.set()

        select_list = [self._server]
        while not self._stopping.is_set():
            if select_list != select.select(select_list, [], [], 0.1)[0]:
                continue

            try:
                client, addr = self._server.accept()
            except Exception as e:
                LOGGER.exception(e)
                continue
            LOGGER.info('Accepted client %s', addr)
            self.connected.set()

            t = paramiko.Transport(client, gss_kex=False)
            try:
                t.set_gss_host(socket.getfqdn(""))
                t.load_server_moduli()
                t.add_server_key(HOST_KEY)
                s = ServerImplementation(self)
                t.start_server(server=s)

                self.authenticated.set()

                self.tunnel_opened.wait(1.0)
                self.tunnel_closed.wait(2.0)

            except Exception as e:
                LOGGER.exception(e)
                continue

            finally:
                try:
                    t.close()
                except:
                    pass

            self._reset()

        self._server.close()
        self._running.clear()

    def start(self):
        t = threading.Thread(target=self._run)
        t.start()
        self._running.wait()

    def stop(self):
        self._stopping.set()


class TunnelTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.server = Server()
        self.server.start()
    
    @classmethod
    def tearDownClass(self):
        self.server.stop()

    def setUp(self):
        self.client = SSH(
            host='localhost',
            port=self.server.port,
            loop=asyncio.new_event_loop()
        )
        self.client.start()

    def tearDown(self):
        self.client.stop()

    def test_connect(self):
        self.client.tunnels['foo.com'] = Tunnel('foo.com', 'localhost', 1337)
        tunnel_opened = self.server.tunnel_opened.wait(400.0)
        self.client.tunnels.clear()
        self.assertTrue(self.client.connected)
        self.assertTrue(tunnel_opened)
        tunnel_closed = self.server.tunnel_closed.wait(1.0)
        self.assertTrue(tunnel_closed)

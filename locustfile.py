import time
from uuid import uuid4
import json
import gevent
from pprint import pformat

from faker import Faker
import websocket
from locust import HttpUser, task, between, events

FAKE = Faker()


def compare_dict(one, two):
    one = set(one.items())
    two = set(two.items())
    return not bool(one.symmetric_difference(two))


class WSClient(object):
    def __init__(self, host):
        self.host = 'ws://test_host.shanty.local:8080/'
        self.ws = websocket.WebSocket()
        self.ws.settimeout(10)
        self.ws.connect(self.host)
        # Eat the first "handshake message" from echo server.
        self._recv()

    @events.quitting.add_listener
    def close(self):
        self.ws.close()

    def _recv(self):
        g = gevent.spawn(self.ws.recv)
        return g.get(block=True, timeout=10)

    def _send(self, payload):
        # Low-level send operation.
        g = gevent.spawn(self.ws.send, json.dumps(payload))
        g.get(block=True, timeout=2)
        r = self._recv()
        return json.loads(r), len(r)

    def send(self, payload):
        payload.update({
            'message_id': uuid4().hex,
        })
        start_time = time.time()
        error = None
        try:
            r, r_len = self._send(payload)
        except Exception as e:
            error = e

        if not error:
            try:
                assert compare_dict(r, payload), '%s != %s' % (pformat(r), pformat(payload))
            except AssertionError as e:
                error = e

        elapsed = time.time() - start_time
        if error:
            events.request_failure.fire(
                request_type='ws', name='send', response_time=elapsed,
                exception=error, response_length=0)
        else:
            events.request_success.fire(
                request_type='ws', name='send', response_time=elapsed,
                response_length=r_len)


class User(HttpUser):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws = WSClient(self.host)

    @task
    def hello(self):
        self.client.get('hello/')

    @task
    def ws(self):
        data = {
            'name': FAKE.name(),
            'address': FAKE.address(),
            'bio': FAKE.text(),
        }
        self.ws.send(data)

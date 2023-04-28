import unittest
import asyncio
from http import HTTPStatus

import requests

from conduit_client.api import REST
from conduit_client.tunnel import Tunnels, Tunnel


class APITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = REST()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def setUp(self):
        self.server.tunnels['foo.com'] = Tunnel('foo.com', 'localhost', 1337)
        self.server.tunnels.changed.clear()

    def test_get(self):
        r = requests.get(
            f'http://localhost:{self.server.port}/tunnels/',
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.OK)
        self.assertFalse(self.server.tunnels.changed.is_set())
        self.assertDictEqual(r.json(), self.server.tunnels.to_dict())

    def test_get_one(self):
        r = requests.get(
            f'http://localhost:{self.server.port}/tunnels/foo.com',
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.OK)
        self.assertFalse(self.server.tunnels.changed.is_set())
        self.assertDictEqual(r.json(), self.server.tunnels['foo.com'].to_dict())

    def test_get_missing(self):
        r = requests.get(
            f'http://localhost:{self.server.port}/tunnels/foobar.com',
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(self.server.tunnels.changed.is_set())

    def test_set_same(self):
        r = requests.post(
            f'http://localhost:{self.server.port}/tunnels/',
            json={ 'foo.com': { 'host': 'localhost', 'port': 1337 }},
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.OK)
        self.assertDictEqual(r.json(), {
            'foo.com': {
                'domain': 'foo.com',
                'host': 'localhost',
                'port': 1337,
            },
        })
        self.assertFalse(self.server.tunnels.changed.is_set())

    def test_set_diff(self):
        r = requests.post(
            f'http://localhost:{self.server.port}/tunnels/',
            json={ 'foo.com': { 'host': 'localhost', 'port': 1024 }},
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.CREATED)
        self.assertDictEqual(r.json(), {
            'foo.com': {
                'domain': 'foo.com',
                'host': 'localhost',
                'port': 1024,
            },
        })
        self.assertTrue(self.server.tunnels.changed.is_set())

    def test_set_one_same(self):
        r = requests.post(
            f'http://localhost:{self.server.port}/tunnels/foo.com',
            json={ 'host': 'localhost', 'port': 1337 },
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.OK)
        self.assertDictEqual(r.json(), {
            'foo.com': {
                'domain': 'foo.com',
                'host': 'localhost',
                'port': 1337,
            },
        })
        self.assertFalse(self.server.tunnels.changed.is_set())

    def test_set_one_diff(self):
        r = requests.post(
            f'http://localhost:{self.server.port}/tunnels/foo.com',
            json={ 'host': 'localhost', 'port': 1024 },
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.CREATED)
        self.assertDictEqual(r.json(), {
            'foo.com': {
                'domain': 'foo.com',
                'host': 'localhost',
                'port': 1024,
            },
        })
        self.assertTrue(self.server.tunnels.changed.is_set())

    def test_delete(self):
        r = requests.delete(
            f'http://localhost:{self.server.port}/tunnels/',
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.NO_CONTENT)
        self.assertIsNone(self.server.tunnels.get('foo.com'))
        self.assertTrue(self.server.tunnels.changed.is_set())

    def test_delete_one(self):
        r = requests.delete(
            f'http://localhost:{self.server.port}/tunnels/foo.com',
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.NO_CONTENT)
        self.assertIsNone(self.server.tunnels.get('foo.com'))
        self.assertTrue(self.server.tunnels.changed.is_set())

    def test_delete_missing(self):
        r = requests.delete(
            f'http://localhost:{self.server.port}/tunnels/foobar.com',
            timeout=1.0
        )
        self.assertEqual(r.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(self.server.tunnels.changed.is_set())

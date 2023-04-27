import unittest

from conduit_client.tunnel import Tunnels, Tunnel


class TunnelTestCase(unittest.TestCase):
    def test_init(self):
        with self.assertRaises(TypeError):
            tunnel = Tunnel()

    def test_str(self):
        tunnel = Tunnel('foo.com', 'localhost', 1337)
        self.assertEqual(str(tunnel), 'foo.com->localhost:1337')
        tunnel.remote_port = 1337
        self.assertEqual(str(tunnel), 'foo.com:1337->localhost:1337')

    def test_from_dict(self):
        tunnel = Tunnel.from_dict({
            'domain': 'foo.com',
            'host': 'localhost',
            'port': 1337,
        })
        self.assertEqual(str(tunnel), 'foo.com->localhost:1337')
        tunnel = Tunnel.from_dict({
            'domain': 'foo.com',
            'host': 'localhost',
            'port': 1337,
            'remote_port': 1337,
        })
        self.assertEqual(str(tunnel), 'foo.com:1337->localhost:1337')

    def test_to_dict(self):
        tunnel = Tunnel('foo.com', 'localhost', 1337)
        self.assertDictEqual(tunnel.to_dict(), {
            'domain': 'foo.com',
            'host': 'localhost',
            'port': 1337,
            'remote_port': 0,
        })


class TunnelsAddTestCase(unittest.TestCase):
    def setUp(self):
        self.tunnels = Tunnels()

    def test_add(self):
        self.assertFalse(self.tunnels.changed.is_set())
        self.tunnels['foo.com'] = Tunnel('foo.com', 'localhost', 1337)
        self.assertTrue(self.tunnels.changed.is_set())


class TunnelsRemoveTestCase(unittest.TestCase):
    def setUp(self):
        self.tunnels = Tunnels()
        self.tunnels['foo.com'] = Tunnel('foo.com', 'localhost', 1337)
        self.tunnels.changed.clear()

    def test_pop(self):
        self.assertFalse(self.tunnels.changed.is_set())
        self.tunnels.pop('foo.com')
        self.assertTrue(self.tunnels.changed.is_set())

    def test_delete(self):
        self.assertFalse(self.tunnels.changed.is_set())
        del self.tunnels['foo.com']
        self.assertTrue(self.tunnels.changed.is_set())

    def test_to_dict(self):
        self.assertDictEqual(self.tunnels.to_dict(), {
            'foo.com': {
                'domain': 'foo.com',
                'host': 'localhost',
                'port': 1337,
                'remote_port': 0,
            }
        })

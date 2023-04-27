import asyncio
import logging


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())


class Tunnel:
    def __init__(self, domain, host, port, remote_port=0):
        self.domain = domain
        self.host = host
        self.port = port
        self.remote_port = remote_port

    @staticmethod
    def from_dict(dict):
        return Tunnel(
            dict['domain'],
            dict['host'],
            dict['port'],
            remote_port=dict.get('remote_port', 0)
        )

    def __str__(self):
        source = self.domain if self.remote_port == 0 \
                             else f'{self.domain}:{self.remote_port}'
        dest = f'{self.host}:{self.port}'
        return f'{source}->{dest}'

    def to_dict(self):
        return {
            'domain': self.domain,
            'host': self.host,
            'port': self.port,
            'remote_port': self.remote_port,
        }


class Tunnels(dict):
    def __init__(self, *args, **kwargs):
        self.changed = asyncio.Event()
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        self.changed.set()
        super().__setitem__(key, value)

    def __delitem__(self, key):
        self.changed.set()
        super().__delitem__(key)

    def pop(self, *args, **kwargs):
        self.changed.set()
        super().pop(*args, **kwargs)

    def clear(self, *args, **kwargs):
        self.changed.set()
        super().clear(*args, **kwargs)

    def to_dict(self):
        return {
            key: value.to_dict() for key, value in self.items()
        }

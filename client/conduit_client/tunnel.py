import threading
import logging


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class Tunnel:
    def __init__(self, domain, host, port):
        self.domain = domain
        self.host = host
        self.port = port

    @staticmethod
    def from_dict(dict):
        return Tunnel(
            dict['domain'],
            dict['host'],
            dict['port'],
        )

    def __str__(self):
        dest = f'{self.host}:{self.port}'
        return f'{self.domain}->{dest}'

    def __eq__(self, other):
        return self.domain == other.domain and \
               self.host == other.host and \
               self.port == other.port

    def to_dict(self):
        return {
            'domain': self.domain,
            'host': self.host,
            'port': self.port,
        }


class Tunnels(dict):
    def __init__(self, *args, **kwargs):
        self.changed = threading.Event()
        self.lock = threading.RLock()
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        current = self.get(key)
        with self.lock:
            super().__setitem__(key, value)
        if current is None or current != value: self.changed.set()

    def __delitem__(self, key):
        has_key = key in self
        with self.lock:
            super().__delitem__(key)
        if has_key: self.changed.set()

    def __eq__(self, other):
        self_keys = set(self.keys())
        other_keys = set(self.values())
        self_values = set(self.values())
        other_values = set(other.values())
        return self_keys == other_keys and \
               self_values == other_values

    def pop(self, key, *args, **kwargs):
        has_key = key in self
        with self.lock:
            super().pop(key, *args, **kwargs)
        if has_key: self.changed.set()

    def clear(self, *args, **kwargs):
        has_keys = bool(self)
        with self.lock:
            super().clear(*args, **kwargs)
        if has_keys: self.changed.set()

    def set(self, values):
        with self.lock:
            self.clear()
            self.update(values)
        if values: self.changed.set()

    def to_dict(self):
        return {
            key: value.to_dict() for key, value in self.items()
        }

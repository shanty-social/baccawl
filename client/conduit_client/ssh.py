import logging
import asyncio
import threading

import asyncssh

from conduit_client.tunnel import Tunnels, Tunnel


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())


class Channel:
    def __init__(self, tunnel, listener):
        self.tunnel = tunnel
        self.listener = listener


class SSH:
    def __init__(self, host='localhost', port=22, tunnels=None, host_key=None,
                 loop=None):
        self._host = host
        self._port = port
        self.tunnels = tunnels or Tunnels()
        self._host_key = host_key
        self.channels = {}
        self._loop = loop or asyncio.new_event_loop()
        self._connection = None
        self._stopping = threading.Event()

    @property
    def connected(self):
        return self._connection is not None

    async def _connect(self):
        if self.connected:
            LOGGER.debug('Already connected')
            return

        LOGGER.debug('Connecting ssh')
        # TODO: host key should be provided by API.
        if self._host_key is not None:
            known_hosts = asyncio.import_known_hosts(f'{self._host} {self._host_key}')
        else:
            known_hosts = None
        # TODO: key should be provided by API.
        client_keys = [asyncssh.generate_private_key('ecdsa-sha2-nistp256')]
        options = asyncssh.SSHClientConnectionOptions(
            known_hosts=known_hosts,
            client_keys=client_keys,
        )
        self._connection = await asyncssh.connect(
            self._host, self._port, options=options)

    async def _disconnect(self):
        if not self.connected:
            return

        LOGGER.debug('Disconnecting ssh')
        self._connection.close()
        self._connection = None

    async def _open_channel(self, name, tunnel):
        if not self.connected:
            await self._connect()

        LOGGER.debug('Opening channel %s', tunnel)
        l = await self._connection.forward_remote_port(
            '0.0.0.0', 0, tunnel.host, tunnel.port)
        self.channels[name] = Channel(tunnel, l)
        p = await self._connection.create_process(f'tunnel {tunnel.domain} {l.get_port()}')
        LOGGER.info('Command return code=%i', p.returncode)

    async def _close_channel(self, name, channel):
        LOGGER.debug('Closing channel %s', channel.tunnel)
        channel.listener.close()
        await channel.listener.wait_closed()
        del self.channels[name]
        if not self.channels:
            await self._disconnect()

    async def _setup_channels(self):
        LOGGER.info('Channel config change detected.')
        add, remove = {}, {}
        with self.tunnels.lock:
            for name, tunnel in self.tunnels.items():
                if name not in self.channels:
                    add[name] = tunnel

            for name, channel in self.channels.items():
                if name not in self.tunnels:
                    remove[name] = channel

        LOGGER.info(
            'Adding %i and removing %i from %i', len(add), len(remove), len(self.channels))
        for name, tunnel in add.items():
            try:
                await self._open_channel(name, tunnel)
            except:
                continue
        for name, channel in remove.items():
            try:
                await self._close_channel(name, channel)
            except Exception as e:
                LOGGER.exception(e)
                continue

    async def _run(self):
        while not self._stopping.is_set():
            changed = await self._loop.run_in_executor(
                None, self.tunnels.changed.wait, 0.1)
            if not changed:
                continue
            self.tunnels.changed.clear()
            try:
                await self._setup_channels()
            except Exception as e:
                LOGGER.exception(e)

    def _run_in_thread(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run())

    def start(self, loop=None):
        t = threading.Thread(target=self._run_in_thread)
        t.start()

    def stop(self):
        self._stopping.set()

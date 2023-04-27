import logging
import asyncio
import threading

import asyncssh

from conduit_client.tunnel import Tunnels, Tunnel


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())


class SSH:
    def __init__(self, tunnels=None, loop=None):
        self.tunnels = tunnels or Tunnels()
        self._loop = loop or asyncio.new_event_loop()
        self._connection = None
        self._stopping = asyncio.Event()

    async def connect(self):
        if self._connection is not None:
            LOGGER.debug('Already connected')
            return

        LOGGER.debug('Connecting ssh')
        self._connection = await asyncssh.connect(self.ssh_host)

    async def disconnect(self):
        LOGGER.debug('Disconnecting ssh')
        await self._connection.disconnect()
        self._connection = None

    async def setup_tunnels(self):
        add, remove = set(), set()
        for tunnel in self.tunnel_config.keys():
            if tunnel not in self.tunnels:
                add.add(tunnel)
        for tunnel in self.tunnels.keys():
            if tunnel not in self.tunnel_config:
                remove.add(tunnel)
        if add:
            LOGGER.debug('Adding %i tunnels', len(add))
            await self.connect()
        for tunnel in add:
            self.tunnels[tunnel] = Tunnel(self.tunnel_config[tunnel])
            await self.tunnels[tunnel].start()
        if remove:
            LOGGER.debug('Removing %i tunnels', len(remove))
        for tunnel in remove:
            await self.tunnels[tunnel].stop()
            del self.tunnels[tunnel]
        if not self.tunnels:
            await self.disconnect()

    async def _run(self):
        while not self._stopping.is_set():
            await self.setup_tunnels()
            await self.tunnel_config_changed

    def _run_in_thread(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run())

    def start(self, loop=None):
        t = threading.Thread(target=self._run_in_thread)
        t.start()

    def stop(self):
        self._stopping.set()

import asyncio
import logging

from conduit_client.api import REST
from conduit_client.ssh import SSH
from conduit_client.tunnel import Tunnels


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class TunnelServer:
    def __init__(self):
        self.tunnels = Tunnels()
        self.api = REST(self.tunnels)
        self.ssh = SSH(self.tunnels)
        self.quit = asyncio.Event()

    async def _run_forever(self, loop):
        # Start HTTP rest API.
        loop.create_task(self.api._run())

        # Start SSH server.
        loop.create_task(self.ssh._run())

        while not self.quit.is_set():
            await asyncio.sleep(0.1)

    def run_forever(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_forever(loop))

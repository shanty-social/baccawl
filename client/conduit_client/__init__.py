import asyncio

from conduit_client.api import REST
from conduit_client.ssh import SSH


class TunnelServer:
    def __init__(self, args):
        self.api = REST(self)
        self.ssh = SSH(self)
        self.quit = asyncio.Event()
        self.domains = {}

    async def _run_forever(self):
        loop = asyncio.get_event_loop()

        # Start HTTP rest API.
        loop.create_task(self.api._run_forever())

        # Start SSH server.
        loop.create_task(self.ssh._run_forever())

        while not self.quit.is_set():
            asyncio.sleep(0.1)

    def run_forever(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_forever())

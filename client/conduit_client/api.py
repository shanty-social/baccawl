import logging
import asyncio
import threading
import time
from http import HTTPStatus

from aiohttp import web

from conduit_client.tunnel import Tunnels, Tunnel


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())


class REST:
    def __init__(self, tunnels=None, host='localhost', port=0, loop=None):
        self.tunnels = Tunnels() if tunnels is None else tunnels
        self._host = host
        self._port = port
        self._loop = loop or asyncio.new_event_loop()
        self._running = threading.Event()
        self._stopping = threading.Event()
        self._app = web.Application()
        self._app.router.add_route(
            '*', '/tunnels/{domain:.*}', self._handle_tunnels)
        self._app.router.add_route('*', '/key/', self._handle_key)
        self._app.router.add_route('get', '/status/', self._handle_status)
        self._runner = None
        self._site = None

    @property
    def port(self):
        if not self._running.is_set():
            raise ValueError('Cannot determine port if not running')
        return self._site._server.sockets[0].getsockname()[1]

    async def _handle_status(self, request):
        pass

    async def _handle_key(self, request):
        pass

    async def _handle_tunnels(self, request):
        domain = request.match_info.get('domain')

        if request.method == 'GET':
            if not domain:
                obj = self.tunnels
            else:
                try:
                    obj = self.tunnels[domain]
                except KeyError:
                    return web.Response(status=HTTPStatus.NOT_FOUND)
            return web.json_response(obj.to_dict())

        elif request.method == 'POST':
            obj = await request.json()
            if not domain:
                tunnels = Tunnels()
                for domain, data in obj.items():
                    data['domain'] = domain
                    tunnels[domain] = Tunnel.from_dict(data)
                if self.tunnels != tunnels:
                    self.tunnels.set(tunnels)
            else:
                obj['domain'] = domain
                self.tunnels[domain] = Tunnel.from_dict(obj)

            status = HTTPStatus.CREATED if self.tunnels.changed.is_set() \
                                        else HTTPStatus.OK
            return web.json_response(self.tunnels.to_dict(), status=status)

        elif request.method == 'DELETE':
            if not domain:
                self.tunnels.clear()
            else:
                try:
                    self.tunnels.pop(domain)
                except KeyError:
                    return web.Response(status=HTTPStatus.NOT_FOUND)
            return web.Response(status=HTTPStatus.NO_CONTENT)

    async def _run(self):
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        self._running.set()
        await self._loop.run_in_executor(None, self._stopping.wait)
        LOGGER.info('Stopping server on %i', self.port)
        await self._runner.cleanup()

    def _run_in_thread(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run())

    def start(self):
        t = threading.Thread(target=self._run_in_thread)
        t.start()
        self._running.wait()

    def stop(self):
        self._stopping.set()

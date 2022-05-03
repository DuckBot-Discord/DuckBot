from aiohttp import web
from .ipc_base import IPCBase, route


class DuckBotIPC(IPCBase):
    @route("/ping", method="get")
    async def ping(self, request):
        return web.json_response({"latency": self.bot.latency})

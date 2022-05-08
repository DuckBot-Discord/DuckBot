import functools
import json
from aiohttp import web
from .ipc_base import IPCBase, route


class DuckBotIPC(IPCBase):
    @route("/stats", method="get")
    async def ping(self, request: web.Request):
        return web.json_response(
            {
                "guilds": len(self.bot.guilds),
                "users": sum(g.member_count or 0 for g in self.bot.guilds),
            }
        )

    @route("/users/{id}", method="get")
    async def get_user(self, request: web.Request):
        id = int(request.match_info["id"])
        user = await self.bot.get_or_fetch_user(int(id))
        if not user:
            return web.json_response({"error": "User not found."}, status=404)
        return web.json_response(user._to_minimal_user_json())

    @route("/commands", method="get")
    async def get_commands(self, request: web.Request):
        return web.json_response(
            {
                c.name: {
                    "aliases": c.aliases or [],
                    "help": c.help,
                    "brief": c.brief,
                    "cog": c.cog_name,
                    "used": await self.bot.pool.fetchval(
                        "SELECT COUNT(*) FROM commands WHERE command = $1", c.name
                    ),
                }
                for c in self.bot.commands
            },
            dumps=functools.partial(json.dumps, indent=4),
        )

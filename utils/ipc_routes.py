from aiohttp import web
from typing import Union
from discord.ext.commands import Group, Command

from utils.bases.command import DuckCommand, DuckGroup
from utils.bases.ipc_base import IPCBase, route


def command_dict(command: Union[DuckCommand, Command]) -> dict:
    return {
        "aliases": command.aliases,
        "help_mapping": getattr(command, "help_mapping", None),
        "help": command.help,
        "brief": command.brief,
        "children": {c.name: command_dict(c) for c in command.commands} if isinstance(command, (Group, DuckGroup)) else None,
        "qualified_name": command.qualified_name,
        "signature": command.signature,
    }


class DuckBotIPC(IPCBase):
    @route("/stats", method="get")
    async def ping(self, request: web.Request):
        return web.json_response(
            {
                "guilds": len(self.bot.guilds),
                "users": {
                    "total": sum(g.member_count or 0 for g in self.bot.guilds),
                    "unique": len(self.bot.users),
                },
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
        data = {
            name: {
                "description": cog.description,
                "brief": cog.emoji,
                "emoji": cog.emoji,
                "commands": {c.name: command_dict(c) for c in cog.get_commands()},
            }
            for name, cog in self.bot.cogs.items()
            if not getattr(cog, 'hidden', True)
        }
        return web.json_response(data)

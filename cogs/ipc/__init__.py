import inspect
import logging

from discord.ext import commands

from .command_routes import CommandRoutes
from .guild_routes import GuildRoutes


class IPC(CommandRoutes, GuildRoutes):
    """ The IPC class is used to handle all Inter-Process communication to the webserver. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for n, f in inspect.getmembers(self):
            if n.startswith("get_") or n.startswith("set_"):
                self.bot.ipc.endpoints[n] = f.__call__

    @commands.Cog.listener()
    async def on_ipc_error(self, endpoint: str, error: Exception):
        """ Called when a server error happens. """
        logging.error(f"IPC Error in endpoint: {endpoint}", exc_info=error)


def setup(bot):
    bot.add_cog(IPC(bot))

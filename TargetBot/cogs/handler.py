
import typing, discord, asyncio
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, discord.ext.commands.errors.CommandNotFound) or isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            return
        raise error

def setup(bot):
    bot.add_cog(help(bot))

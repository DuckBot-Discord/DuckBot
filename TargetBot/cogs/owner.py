import typing, discord, asyncio, json
from discord.ext import commands

class owner_only_commands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(owner_only_commands(bot))

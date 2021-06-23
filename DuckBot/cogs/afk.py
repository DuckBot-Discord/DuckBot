import typing, discord, asyncio
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

class afk(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(afk(bot))

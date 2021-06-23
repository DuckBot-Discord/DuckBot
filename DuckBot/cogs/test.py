import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers
import datetime

class test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # nothing being tested...

def setup(bot):
    bot.add_cog(test(bot))

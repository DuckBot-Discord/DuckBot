import discord
import random

from discord.ext import commands


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """🧪 Test commands. 💀 May not work or not be what you think they'll be."""

    def __init__(self, bot):
        self.bot = bot

import random

import discord
from discord.ext import commands
import quickchart

from DuckBot.__main__ import DuckBot
from DuckBot.helpers.context import CustomContext


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = '🧪'
        self.select_brief = 'Beta Commands (WIP)'

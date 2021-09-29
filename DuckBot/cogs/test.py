import discord
from discord.ext import commands
from jishaku.paginators import WrappedPaginator

from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers.helper import generate_youtube_bar


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    @commands.command()
    async def bar(self, ctx: CustomContext, position: int, duration: int, length: int):
        await ctx.send(generate_youtube_bar(position, duration, length))



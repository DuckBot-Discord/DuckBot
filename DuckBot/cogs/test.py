import discord
import typing
import emoji
from DuckBot.helpers import paginator
from DuckBot.helpers.time_inputs import ShortTime
from discord.ext import commands
from DuckBot.__main__ import DuckBot


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    @commands.command(name="in")
    async def _in_command(self, ctx, *, relative_time: ShortTime):
        """
        Shows a time in everyone's time-zone
          note that: `relative_time` must be a short time!
        for example: 1d, 5h, 3m or 25s, or a combination of those, like 3h5m25s (without spaces between these times)
        """

        await ctx.send(f"{discord.utils.format_dt(relative_time.dt, style='F')} ({discord.utils.format_dt(relative_time.dt, style='R')})")

    def __init__(self, bot):
        self.bot: DuckBot = bot

import discord
import typing
import emoji
from DuckBot.helpers import paginator
from discord.ext import commands

from DuckBot.__main__ import DuckBot


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    @commands.command(usage="")
    @commands.guild_only()
    async def emojilist(self, ctx, guild: typing.Optional[discord.Guild]):
        """ Lists this server's emoji """
        guild = guild if guild and (await self.bot.is_owner(ctx.author)) else ctx.guild
        emotes = [f"{str(e)} **|** {e.name} **|** [`{str(e)}`]({e.url})" for e in guild.emojis]
        menu = paginator.ViewPaginator(paginator.ServerEmotesEmbedPage(data=emotes, guild=guild), ctx=ctx)
        await menu.start()


    def __init__(self, bot):
        self.bot: DuckBot = bot

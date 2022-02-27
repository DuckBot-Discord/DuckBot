import discord
from discord.ext import commands
from utils import DuckCog
from utils.context import DuckContext


class PrefixChanges(DuckCog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.command(name='prefix', aliases=['prefixes'])
    async def prefix(self, ctx: DuckContext, *, prefixes: str = None):
        """
        Adds a prefix for this server (you can have up to 25 prefixes)
        """
        if prefixes is None:
            prefixes = await self.bot.get_prefix(ctx.message, raw=True)
            embed = discord.Embed(title='Current Prefixes')
            embed.description = '\n'.join(prefixes)
            return await ctx.send(embed=embed)

        # TODO: finish this, went to sleep.



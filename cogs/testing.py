import discord

from utils import DuckCog, DuckContext, command
from utils.converters import PartiallyMatch


class Testing(DuckCog):
    @command()
    async def test(self, ctx: DuckContext, primary: PartiallyMatch[discord.TextChannel, discord.StageChannel]):
        return await ctx.send(f'{primary}')


async def setup(bot):
    await bot.add_cog(Testing(bot))

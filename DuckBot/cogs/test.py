import discord, asyncio, typing, aiohttp, random, json, yaml, re
from discord.ext import commands, menus
from errors import HigherRole
from jishaku.models import copy_context_with
import contextlib


class test(commands.Cog):
    """🧪 Test commands. 💀 May not work"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="raise", help="Testing handling custom errors")
    async def _raise(self, ctx):
        raise HigherRole()

    @commands.command(help="Another error handling test")
    async def test(self, ctx):
        await ctx.send(f"{ctx.author} hi")

    @commands.command()
    async def sudo(self, ctx: commands.Context, target: discord.User, *, command_string: str):
        """
        Run a command as someone else.

        This will try to resolve to a Member, but will use a User if it can't find one.
        """

        if ctx.guild:
            # Try to upgrade to a Member instance
            # This used to be done by a Union converter, but doing it like this makes
            #  the command more compatible with chaining, e.g. `jsk in .. jsk su ..`
            target_member = None

            with contextlib.suppress(discord.HTTPException):
                target_member = ctx.guild.get_member(target.id) or await ctx.guild.fetch_member(target.id)

            target = target_member or target

        alt_ctx = await copy_context_with(ctx, author=target, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            if alt_ctx.invoked_with is None:
                return await ctx.send('This bot has been hard-configured to ignore this user.')
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.invoke(alt_ctx)


def setup(bot):
    bot.add_cog(test(bot))

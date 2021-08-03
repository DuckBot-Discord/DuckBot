import discord, asyncio, typing, aiohttp, random, json, yaml, re, psutil, pkg_resources, time, datetime
from discord.ext import commands, menus
from errors import HigherRole
from jishaku.models import copy_context_with
import contextlib


class test(commands.Cog):
    """🧪 Test commands. 💀 May not work or not be what you think they'll be."""
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="raise", help="Testing handling custom errors")
    async def _raise(self, ctx):
        raise HigherRole()

    @commands.command(help="Another error handling test")
    async def test(self, ctx):
        await ctx.send(f"{ctx.author} hi")

def setup(bot):
    bot.add_cog(test(bot))

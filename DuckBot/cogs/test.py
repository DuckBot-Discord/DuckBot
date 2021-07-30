import discord, asyncio, typing, aiohttp, random, json, yaml, re
from discord.ext import commands, menus
from errors import HigherRole

class test(commands.Cog):
    """🧪 Test commands. 💀 May not work"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="raise", help="Testing handling custom errors")
    async def _raise(self, ctx):
        raise HigherRole()

    @commands.command(help="Another error handling test")
    async def test(self, ctx, member: discord.Member, *, text):
        await ctx.send(f"{member} {text}")

def setup(bot):
    bot.add_cog(test(bot))

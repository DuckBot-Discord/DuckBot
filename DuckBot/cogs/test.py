import discord, asyncio, typing, aiohttp, random, json, yaml, re
from discord.ext import commands, menus
from errors import HigherRole

class test(commands.Cog):
    """🧪 Test commands. 💀 May not work"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        raise HigherRole()

def setup(bot):
    bot.add_cog(test(bot))

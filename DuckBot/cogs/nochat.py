import json, random, discord, aiohttp, typing, asyncio
from random import randint
from discord.ext import commands


class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

"""    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id == 833059290319028264 or message.channel.id == 838385196423839744 or message.channel.id == 837493793829814272: return
        if message.guild.id == 816240056003461133:
            await message.delete()
            await message.channel.send("Drama lockdown also goes for staff!", delete_after=5)

"""
def setup(bot):
    bot.add_cog(help(bot))

import discord, random
from discord.ext import commands, tasks
from random import randint

class auto_quack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.duck.start()

    @tasks.loop(minutes=5)
    async def duck(self):
        value = randint(0, 100)
        if value == 1:
            channel = self.bot.get_channel(814543488423166013)
            await channel.send("quack")

def setup(bot):
    bot.add_cog(auto_quack(bot))

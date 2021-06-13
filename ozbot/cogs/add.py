import discord, random, datetime, asyncio
from discord.ext import commands, tasks
from random import randint

class auto_quack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.remrole.start()

    @tasks.loop(minutes=15)
    async def remrole(self):
        role = self.bot.get_guild(706624339595886683).get_role(851498082033205268)
        for members in role.members:
            date = members.joined_at
            now = datetime.datetime.now()
            diff = now - date
            hours = diff.total_seconds() / 60 /60
            if hours >= 336:
                await members.remove_roles(role)
            await asyncio.sleep(5)

def setup(bot):
    bot.add_cog(auto_quack(bot))

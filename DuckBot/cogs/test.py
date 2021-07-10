import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers
import datetime

class test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=5)
        try: await ctx.message.delete(delay = 5)
        except: pass

    @commands.command()
    @commands.is_owner()
    async def paginator(self, ctx):
        paginator = commands.Paginator()
        paginator.add_line('some line')
        paginator.add_line('what is this')

        for page in paginator.pages:
            await ctx.send(page)

def setup(bot):
    bot.add_cog(test(bot))

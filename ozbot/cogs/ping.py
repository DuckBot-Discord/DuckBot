import discord, asyncio
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        message = await ctx.send(embed=embed)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await asyncio.sleep(0.6)
        embed = discord.Embed(title='', description=f'**{round (self.bot.latency * 1000)} ms**', color=ctx.me.color)
        await message.edit(embed=embed)

    @commands.command(aliases = ['source', 'code'])
    async def sourcecode(self, ctx):
        embed=discord.Embed(title="", description="**[Here's my source code](https://github.com/LeoCx1000/discord-bots)**", color=ctx.me.color)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(help(bot))

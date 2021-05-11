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

def setup(bot):
    bot.add_cog(help(bot))

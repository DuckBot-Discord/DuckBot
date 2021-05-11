import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers
import datetime

class test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    """self.duck_t.start()
    self.duck2_t.start()"""

    @commands.command()
    async def test(self, ctx):
        if ctx.message.author.id == 349373972103561218:
            await ctx.send(self.bot.activity)

    @commands.command()
    async def playsong(self, ctx):
        embed = discord.Embed(title='🎶 DuckBot music', description="ain't nobody got processing power for that!", color=ctx.me.color)

        embed.add_field(name='Spotify', value='https://www.spotify.com/', inline=True)
        embed.add_field(name='Youtube', value='https://music.youtube.com/', inline=True)
        embed.add_field(name='Apple Music', value='https://www.apple.com/apple-music/', inline=True)
        embed.add_field(name='TIDAL', value='https://tidal.com/', inline=True)
        embed.add_field(name='Amazon Music', value='https://music.amazon.com/', inline=True)
        embed.add_field(name='Deezer', value='https://www.deezer.com/', inline=True)
        await ctx.send(embed=embed)

    @test.error
    async def test_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"""```⚠ {error}```""")
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return


def setup(bot):
    bot.add_cog(test(bot))

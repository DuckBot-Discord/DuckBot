import discord, asyncio, typing, aiohttp, random, json, yaml
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sendembed(self, ctx, *, data):
        try:
            dictionary = json.loads(data)
        except:
            await ctx.send("json data malformed")
            return
        embed = discord.Embed().from_dict(dictionary)
        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("json data malformed")
            return
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(help(bot))

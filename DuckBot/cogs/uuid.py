import json, random, discord, aiohttp, typing
from random import randint
from discord.ext import commands


class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def uuid(self, ctx, *, argument: typing.Optional[str] = ''):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                embed = discord.Embed(color = ctx.me.color)
                if cs.status == 204:
                    embed.add_field(name='⚠ ERROR ⚠', value=f"`{argument}` is not a minecraft username!")

                elif cs.status == 400:
                    embed.add_field(name="⛔ ERROR ⛔", value="ERROR 400! Bad request.")
                else:
                    res = await cs.json()
                    user = res["name"]
                    uuid = res["id"]
                    embed.add_field(name=f'Minecraft username: `{user}`', value=f"**UUID:** `{uuid}`")

                await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(help(bot))

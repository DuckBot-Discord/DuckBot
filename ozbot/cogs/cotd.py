import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        var = 1
        self.change_color.start()

    @tasks.loop(minutes=60.0)
    async def change_color(self):
        await self.bot.wait_until_ready()
        if datetime.datetime.now().hour == 5:
            color = random.randint(0, 0xFFFFFF)
            await self.bot.get_guild(706624339595886683).get_role(800407956323434556).edit(colour=color)
            await self.bot.get_guild(706624339595886683).get_role(800295689585819659).edit(colour=color)
            channel = self.bot.get_channel(799503231989973022)
            embcol = color
            color = f'{hex(color)}'.replace('0x', '').upper()
            embed = discord.Embed(description=f"Color of the day changed to {color}", color=embcol)
            embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{color}/16x16")
            await channel.send(embed=embed)
            await asyncio.sleep(43200)


    @commands.command(aliases=["color"])
    @commands.has_permissions(manage_nicknames=True)
    async def cotd(self, ctx, color: typing.Optional[discord.Colour] = discord.Colour.default, tag = "-n"):
        await self.bot.wait_until_ready()
        if tag == "-r": color = random.randint(0, 0xFFFFFF)
        await self.bot.get_guild(706624339595886683).get_role(800407956323434556).edit(colour=color)
        await self.bot.get_guild(706624339595886683).get_role(800295689585819659).edit(colour=color)
        await ctx.message.delete()
        embcol = color
        embed = discord.Embed(description=":sparkles:", color=embcol)
        await ctx.send(embed=embed, delete_after=3)
        channel = self.bot.get_channel(799503231989973022)
        if tag == "-r": color = f'{hex(color)}'.replace('0x', '').upper()
        embed = discord.Embed(description=f"Daily color manually changed to {color}", color=embcol)
        imcolor = f"{color}"
        imcolor = imcolor.replace("#", "")
        embed.set_thumbnail(url=f" https://singlecolorimage.com/get/{imcolor}/16x16")
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(help(bot))

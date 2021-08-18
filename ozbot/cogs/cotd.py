import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks

class daily_color(commands.Cog):
    """🎨 A role that changes color every day."""
    def __init__(self, bot):
        self.bot = bot
        self.var = 0

        self.remrole.start()
        self.daily_task.start()

    def cog_unload(self):
        self.daily_task.cancel()
        self.remrole.cancel()

    @tasks.loop(hours=24)
    async def daily_task(self):
        if self.var == 0:
            self.var == 1
            color = random.randint(0, 0xFFFFFF)
            await self.bot.get_guild(706624339595886683).get_role(800407956323434556).edit(colour=color)
            await self.bot.get_guild(706624339595886683).get_role(800295689585819659).edit(colour=color)
            channel = self.bot.get_channel(869282490160926790)
            embcol = color
            color = f'{hex(color)}'.replace('0x', '').upper()
            embed = discord.Embed(description=f"Color of the day changed to {color}", color=embcol)
            embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{color}/16x16")
            await channel.send(embed=embed)
            print(self.daily_task.current_loop)

    @daily_task.before_loop
    async def wait_until_7am(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now().astimezone()
        next_run = now.replace(hour=5, minute=0, second=0)

        if next_run < now:
            next_run += datetime.timedelta(days=1)

        await discord.utils.sleep_until(next_run)





    @commands.command(aliases=["color", "setcolor"], help="Changes the Color of the Day. use \"-r\" to randomize it", usage="<#HEX | -r>")
    @commands.has_permissions(manage_nicknames=True)
    async def cotd(self, ctx, color: typing.Optional[discord.Colour], tag: typing.Optional[str]):
        if color == None and tag == None: return await ctx.send("`!cotd <#HEX | -r>` Missing hex code. `-r` to randomize", delete_after=5)
        if tag == "-r": color = random.randint(0, 0xFFFFFF)
        await self.bot.get_guild(706624339595886683).get_role(800407956323434556).edit(colour=color)
        await self.bot.get_guild(706624339595886683).get_role(800295689585819659).edit(colour=color)
        await ctx.message.delete()
        embcol = color
        embed = discord.Embed(description=":sparkles:", color=embcol)
        await ctx.send(embed=embed, delete_after=3)
        channel = self.bot.get_channel(869282490160926790)
        if tag == "-r": color = f'{hex(color)}'.replace('0x', '').upper()
        embed = discord.Embed(description=f"Daily color manually changed to {color}", color=embcol)
        imcolor = f"{color}"
        imcolor = imcolor.replace("#", "")
        embed.set_thumbnail(url=f" https://singlecolorimage.com/get/{imcolor}/16x16")
        await channel.send(embed=embed)



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

    @remrole.before_loop
    async def wait_until_bot_ready(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(daily_color(bot))

import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks

async def do_cotd(ctx: commands.Context, color: discord.Color = None, manual: bool = False):
    color = color or discord.Color.random()
    guild = ctx.bot.get_guild(706624339595886683)
    await guild.get_role(800407956323434556).edit(colour=color)
    await guild.get_role(800295689585819659).edit(colour=color)
    log_channel = guild.get_channel(869282490160926790)
    embed = discord.Embed(color=color)
    embed.set_author(icon_url=f"https://singlecolorimage.com/get/{str(color)[1:]}/64x64",
                    name=f"Color of the day{' manually ' if manual is True else ' '}changed to {color}")

    if manual is True:
        embed.set_footer(text=f"Requested by {ctx.author}",
                         icon_url=ctx.author.display_avatar.url)

        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed, delete_after = 1)
    await log_channel.send(embed=embed)
    return color

class daily_color(commands.Cog):
    """🎨 A role that changes color every day."""
    def __init__(self, bot):
        self.bot = bot

        self.remrole.start()
        self.daily_task.start()

    def cog_unload(self):
        self.daily_task.cancel()
        self.remrole.cancel()

    @tasks.loop(hours=24)
    async def daily_task(self):
        await do_cotd(ctx)

    @daily_task.before_loop
    async def wait_until_midnight(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now().astimezone()
        next_run = now.replace(hour=5, minute=0, second=2)

        if next_run < now:
            next_run += datetime.timedelta(days=1)

        await discord.utils.sleep_until(next_run)

    @commands.command(aliases=["color", "setcolor"])
    @commands.has_permissions(manage_nicknames=True)
    async def cotd(self, ctx, color: typing.Optional[discord.Colour] = None):
        """
        Changes the Color of the day, run the command withour a colour to randomize it.
        """
        await do_cotd(ctx, color, manual=True)

    @tasks.loop(minutes=15)
    async def remrole(self):
        role = self.bot.get_guild(706624339595886683).get_role(851498082033205268)
        for members in role.members:
            date = members.joined_at
            now = discord.utils.utcnow()
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

import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers, menus
import datetime


class banembed(menus.ListPageSource):
    def __init__(self, data, per_page=15):
        super().__init__(data, per_page=per_page)


    async def format_page(self, menu, entries):
        embed = discord.Embed(title=f"Server bans ({len(entries)})",
                              description="\n".join(entries))
        embed.set_footer(text="To unban do .unban [number]\nMore user info do .baninfo [number]")
        return embed

class Confirm(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result

class test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(5)
        try:
            await ctx.message.delete()
            return
        except: return

#------------------------------------------------------------------------------#
#--------------------------------- UNBAN --------------------------------------#
#------------------------------------------------------------------------------#

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def unban(self, ctx, number: typing.Optional[int]):
        if not ctx.channel.permissions_for(ctx.me).ban_members:
            await ctx.send("i'm missing the ban_members permission :pensive:")

        if not number:
            try:
                bans = await ctx.guild.bans()
            except:
                await ctx.send('Missing permission to see server bans')
                return

            desc = []
            number = 1
            for ban_entry in bans:
                desc.append(f"**{number}) {ban_entry.user}**")
                number = number + 1
            pages = menus.MenuPages(source=banembed(desc), clear_reactions_after=True)
            await pages.start(ctx)
            return

        if number <=0:
            embed=discord.Embed(color=0xFF0000,
            description=f"__number__ must be greater than 1\nsyntax: `{ctx.prefix}unban [number]`\n To get the number use the `{ctx.prefix}unban` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send('Missing permission to see server bans')
            return

        try:
            ban_entry = bans[number]
        except:
            embed=discord.Embed(color=0xFF0000,
            description=f"That member was not found. \nsyntax: `{ctx.prefix}unban [number]`\n To get the number use the `{ctx.prefix}unban` command")
            await ctx.send(embed=embed)
            return

        confirm = await Confirm(f'are you sure you want to unban {ban_entry.user}?').prompt(ctx)
        if confirm:
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f'unbanned {ban_entry.user}')
        else:
            await ctx.send('cancelled!')

#------------------------------------------------------------------------------#
#-------------------------------- BAN LIST ------------------------------------#
#------------------------------------------------------------------------------#

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def bans(self, ctx):
        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send('Missing permission to see server bans')

        desc = []
        number = 1
        for ban_entry in bans:
            desc.append(f"**{number}) {ban_entry.user}**")
            number = number + 1
        pages = menus.MenuPages(source=banembed(desc), clear_reactions_after=True)
        await pages.start(ctx)

#------------------------------------------------------------------------------#
#-------------------------------- BAN INFO ------------------------------------#
#------------------------------------------------------------------------------#

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def baninfo(self, ctx, number: typing.Optional[int]):
        if not ctx.channel.permissions_for(ctx.me).ban_members:
            await ctx.send("i'm missing the ban_members permission :pensive:")

        if not number:
            try:
                bans = await ctx.guild.bans()
            except:
                await ctx.send("i'm missing the ban_members permission :pensive:")
                return

            desc = []
            number = 1
            for ban_entry in bans:
                desc.append(f"**{number}) {ban_entry.user}**")
                number = number + 1
            pages = menus.MenuPages(source=banembed(desc), clear_reactions_after=True)
            await pages.start(ctx)
            return

        if number <=0:
            embed=discord.Embed(color=0xFF0000,
            description=f"__number__ must be greater than 1\nsyntax: `{ctx.prefix}baninfo [number]`\n To get the number use the `{ctx.prefix}baninfo` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return

        try:
            ban_entry = bans[number]
        except:
            embed=discord.Embed(color=0xFF0000,
            description=f"That member was not found. \nsyntax: `{ctx.prefix}baninfo [number]`\n To get the number use the `{ctx.prefix}baninfo` command")
            await ctx.send(embed=embed)
            return

        date = ban_entry.user.created_at
        embed=discord.Embed(color = ctx.me.color,
        description=f"""```yaml
       user: {ban_entry.user}
    user id: {ban_entry.user.id}
     reason: {ban_entry.reason}
 created at: {date.strftime("%b %-d %Y at %-H:%M")} UTC
```""")
        embed.set_author(name=ban_entry.user, icon_url=ban_entry.user.avatar_url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(test(bot))

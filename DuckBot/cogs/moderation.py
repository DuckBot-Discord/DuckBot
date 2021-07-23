import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers, menus
import datetime

class banembed(menus.ListPageSource):
    """Commands to moderate a server"""
    def __init__(self, data, per_page=15):
        super().__init__(data, per_page=per_page)


    async def format_page(self, menu, entries):
        embed = discord.Embed(title=f"Server bans ({len(entries)})",
                              description="\n".join(entries))
        embed.set_footer(text=f"To unban do db.unban [entry]\nMore user info do db.baninfo [entry]")
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


class moderation(commands.Cog):
    """Your typical moderation stuff, for all server admins"""
    def __init__(self, bot):
        self.bot = bot

    #--------------- FUNCTIONS ---------------#

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await ctx.message.delete(delay=5)
        return

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=5)
        await ctx.message.delete(delay=5)

    #### .uinfo {user} ####
    # gives user info

    # all the emoji are from the bots.gg discord server.
    # If your bot is in there, it'll be able to use them
    def get_user_badges(self, user):
        author_flags = user.public_flags
        flags = dict(author_flags)
        emoji_flags = ""
        if flags['staff'] is True:
            emoji_flags = f"{emoji_flags} <:staff:314068430787706880>"
        if flags['partner'] is True:
            emoji_flags = f"{emoji_flags} <:partnernew:754032603081998336>"
        if flags['hypesquad'] is True:
            emoji_flags = f"{emoji_flags} <:hypesquad:314068430854684672>"
        if flags['bug_hunter'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter:585765206769139723>"
        if flags['hypesquad_bravery'] is True:
            emoji_flags = f"{emoji_flags} <:bravery:585763004218343426>"
        if flags['hypesquad_brilliance'] is True:
            emoji_flags = f"{emoji_flags} <:brilliance:585763004495298575>"
        if flags['hypesquad_balance'] is True:
            emoji_flags = f"{emoji_flags} <:balance:585763004574859273>"
        if flags['early_supporter'] is True:
            emoji_flags = f"{emoji_flags} <:supporter:585763690868113455>"
        if user.premium_since:
            emoji_flags = f"{emoji_flags} <:booster4:585764446178246657>"
        if flags['bug_hunter_level_2'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter_gold:850843414953984041>" #not from bots.gg
        if flags['verified_bot_developer'] is True:
            emoji_flags = f"{emoji_flags} <:earlybotdev:850843591756349450>" #not from bots.gg
        if emoji_flags == "": emoji_flags = None
        return emoji_flags

    @commands.command(help="Shows a user's information", aliases = ['userinfo', 'ui', 'whois', 'whoami'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def uinfo(self, ctx, user: typing.Optional[discord.Member]):
        if not user: user = ctx.author
        # BADGES
        badges = self.get_user_badges(user)
        if badges: badges = f"\n<:store_tag:658538492409806849>**Badges:**{badges}"
        else: badges = ''
        # USERID
        userid = f"\n<:greyTick:596576672900186113>**ID:** `{user.id}`"
        # NICKNAME
        if user.nick: nick = f"\n<:nickname:850914031953903626>**Nickname:** `{user.nick}`"
        else: nick = ""
        # CREATION DATE
        date = user.created_at.strftime("%b %-d %Y at %-H:%M")
        created = f"\n<:invite:658538493949116428>**Created:** `{date} UTC`"
        # JOIN DATE
        if user.joined_at:
            date = user.joined_at.strftime("%b %-d %Y at %-H:%M")
            joined = f"\n<:joined:849392863557189633>**joined:** `{date} UTC`"
        else: joined = ""
        # GUILD OWNER
        if user is ctx.guild.owner:
            owner = f"\n<:owner:585789630800986114>**Owner:** <:check:314349398811475968>"
        else: owner = ""
        # BOT
        if user.bot:
            bot = f"\n<:botTag:230105988211015680>**Bot:** <:check:314349398811475968>"
        else: bot = ""
        # BOOSTER SINCE
        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else: boost = ""

        # Join Order
        order = f"\n<:moved:848312880666640394>**Join position:** `{sorted(ctx.guild.members, key=lambda user: user.joined_at).index(user) + 1}`"

        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else: boost = ""
        # ROLES
        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role: continue
            roles = f"{roles} {role.mention}"
        if roles != "":
            roles = f"\n<:role:808826577785716756>**roles:** {roles}"
        # EMBED
        embed = discord.Embed(color=ctx.me.color, description=f"""{badges}{owner}{bot}{userid}{created}{nick}{joined}{order}{boost}{roles}""")
        embed.set_author(name=user, icon_url=user.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        await ctx.send(embed=embed)


#------------------------------------------------------------#
#------------------------ KICK ------------------------------#
#------------------------------------------------------------#

    @commands.command(help="Kicks a member from the server", usage="<member>, [reason]")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, kick_members=True)
    async def kick(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if member == None:
            await self.error_message(ctx, 'You must specify a member to kick')
            return
        elif member == ctx.author:
            await self.error_message(ctx, 'You can\'t kick yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            await self.error_message(ctx, 'I\'m not high enough in role hierarchy to kick that member!')
            return
        if member.top_role <= ctx.author.top_role:
            if member.guild_permissions.ban_members == False and member.guild_permissions.kick_members == False and member.guild_permissions.manage_messages == False:
                try:
                    mem_embed=discord.Embed(description=f"**{ctx.message.author}** has kicked you from **{ctx.guild.name}**", color=ctx.me.color)
                    if reason: mem_embed.set_footer(text=f'reason: {reason}')
                    await member.send(embed=mem_embed)
                    await member.kick(reason=reason)
                    if reason:
                        embed=discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed=discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}""", color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ✅')
                    await ctx.send(embed=embed)
                except discord.HTTPException:
                    await member.kick(reason=reason)
                    if reason:
                        embed=discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed=discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}""", color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ❌')
                    await ctx.send(embed=embed)
            else:
                await self.error_message(ctx, 'you can\'t kick another moderator')
                return
        else:
            await self.error_message(ctx, 'Member is higher than you in role hierarchy')
            return

#-----------------------------------------------------------#
#------------------------ BAN ------------------------------#
#-----------------------------------------------------------#

    @commands.command(help="Bans a member from the server", usage="<member> [reason]")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    async def ban(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if member == None:
            await self.error_message(ctx, 'You must specify a member to kick')
            return
        elif member == ctx.author:
            await self.error_message(ctx, 'You can\'t kick yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            await self.error_message(ctx, 'I\'m not high enough in role hierarchy to kick that member!')
            return
        if member.top_role <= ctx.author.top_role:
            if member.guild_permissions.ban_members == False and member.guild_permissions.kick_members == False and member.guild_permissions.manage_messages == False:
                try:
                    mem_embed=discord.Embed(description=f"**{ctx.message.author}** has banned you from **{ctx.guild.name}**", color=ctx.me.color)
                    if reason: mem_embed.set_footer(text=f'reason: {reason}')
                    await member.send(embed=mem_embed)
                    await member.ban(reason=reason)
                    if reason:
                        embed=discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed=discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}""", color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ✅')
                    await ctx.send(embed=embed)
                except discord.HTTPException:
                    await member.ban(reason=reason)
                    if reason:
                        embed=discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed=discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}""", color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ❌')
                    await ctx.send(embed=embed)
            else:
                await self.error_message(ctx, 'you can\'t ban another moderator!')
                return

        else:
            await self.error_message(ctx, 'Member is higher than you in role hierarchy')
            return

#------------------------------------------------------------#
#------------------------ NICK ------------------------------#
#------------------------------------------------------------#

    @commands.command(help="Sets yours or someone else's nick # leave empty to remove nick", aliases = ['sn', 'nick'], usage="<member> [new nick]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True, manage_nicknames=True)
    async def setnick(self, ctx, member : typing.Optional[discord.Member], *, new : typing.Optional[str] = 'None'):
        if member == None:
            if ctx.channel.permissions_for(ctx.author).manage_nicknames:
                await ctx.send("`!nick [member] (newNick)` - You must specify a member", delete_after=10)
                await asyncio.sleep(10)
                await ctx.message.delete()
            return
        if new == 'None':
            new = f'{member.name}'
        else:
            new = new
        old = f'{member.nick}'
        if old == 'None':
            old = f'{member.name}'
        else:
            old = old
        if member == ctx.author and ctx.channel.permissions_for(ctx.author).change_nickname:
            try:
                await member.edit(nick=new)
                await ctx.send(f"""✏ {ctx.author.mention} nick for {member}
**`{old}`** -> **`{new}`**""")
                try: await ctx.message.delete()
                except discord.Forbidden: return
            except discord.Forbidden:
                await self.error_message(ctx, 'Bot not high enough in role hierarchy')
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('#️⃣')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
                return
        elif ctx.channel.permissions_for(ctx.author).manage_nicknames:
            if member.top_role >= ctx.author.top_role:
                await self.error_message(ctx, "⚠ Cannot edit nick for members equal or above yourself!")
                return
            try:
                await member.edit(nick=new)
                await ctx.send(f"""✏ {ctx.author.mention} edited nick for **{member}**
**`{old}`** -> **`{new}`**""")
                try: await ctx.message.delete()
                except discord.Forbidden: return
            except discord.Forbidden:
                await self.error_message(ctx, 'Bot not high enough in role hierarchy')
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('#️⃣')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
        elif member == ctx.author and ctx.channel.permissions_for(ctx.author).change_nickname:
            await self.error_message(ctx, f"""You can only change your own nick!
> !nick {ctx.author.mention} `<new nick>`""")
            return
        else: await self.perms_error(ctx)

#-------------------------------------------------------------#
#------------------------ PURGE ------------------------------#
#-------------------------------------------------------------#

    @commands.command(help="Purges messages in a channel", aliases=['clean', 'clear', 'delete'], usage="<amount>")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    async def purge(self, ctx, argument: typing.Optional[int]):
        amount = argument
        if amount:
            if amount <= 1000:
                try: await ctx.message.delete()
                except: pass
                await ctx.channel.purge(limit=amount)
                await ctx.send("🗑 Purge completed!", delete_after = 5)
            else:
                try: await ctx.message.delete()
                except: pass
                await ctx.channel.purge(limit=1000)
                await ctx.send("🗑 Completed! Applied limited of 1000 messages")
        else:
            await self.error_message(ctx, "Please specify amount of messages to purge!")

#------------------------------------------------------------------------------#
#--------------------------------- UNBAN --------------------------------------#
#------------------------------------------------------------------------------#

    @commands.command(help="unbans a member # run without arguments to get a list of entries", usage="[entry]")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx, number: typing.Optional[int]):
        if not ctx.channel.permissions_for(ctx.me).ban_members:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not number:
            try:
                bans = await ctx.guild.bans()
            except:
                await ctx.send("i'm missing the ban_members permission :pensive:")
                return
            if not bans:
                await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
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
            description=f"__number__ must be greater than 1\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return

        try:
            ban_entry = bans[number]
        except:
            embed=discord.Embed(color=0xFF0000,
            description=f"That member was not found. \nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
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

    @commands.command(help="Gets a list of bans in the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def bans(self, ctx):
        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return
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

    @commands.command(help="brings info about a ban # run without arguments to get a list of entries", usage="[entry]")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def baninfo(self, ctx, number: typing.Optional[int]):
        if not ctx.channel.permissions_for(ctx.me).ban_members:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not number:
            try:
                bans = await ctx.guild.bans()
            except:
                await ctx.send("i'm missing the ban_members permission :pensive:")
                return
            if not bans:
                await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
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
            description=f"__number__ must be greater than 1\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return
        try:
            ban_entry = bans[number]
        except:
            embed=discord.Embed(color=0xFF0000,
            description=f"That member was not found. \nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
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
    bot.add_cog(moderation(bot))

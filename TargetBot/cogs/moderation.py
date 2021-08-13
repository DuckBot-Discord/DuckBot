from discord.ext import commands, tasks, menus
import typing, yaml

import re
import json
import discord
import enum
import datetime
import asyncio
import argparse, shlex

class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class banembed(menus.ListPageSource):
    def __init__(self, data, per_page=15):
        super().__init__(data, per_page=per_page)


    async def format_page(self, menu, entries):
        embed = discord.Embed(title=f"Server bans ({len(entries)})",
                              description="\n".join(entries))
        embed.set_footer(text=f"To unban do !unban [entry]\nMore user info do !baninfo [entry]")
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

def can_execute_action(ctx, user, target):
    return user.id == ctx.bot.owner_id or \
           user == ctx.guild.owner or \
           user.top_role > target.top_role

class MemberID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
            else:
                m = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
                if m is None:
                    # hackban case
                    return type('_Hackban', (), {'id': member_id, '__str__': lambda s: f'Member ID {s.id}'})()

        if not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')
        return m

class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity

class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f'{ctx.author} (ID: {ctx.author.id}): {argument}'

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret

def safe_reason_append(base, to_append):
    appended = base + f'({to_append})'
    if len(appended) > 512:
        return base
    return appended

class moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(717140270789033984).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml

    #--------------- FUNCTIONS ---------------#

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(self.yaml_data['ReactionTimeout'])
        try:
            await ctx.message.delete()
            return
        except: return

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=self.yaml_data['ErrorMessageTimeout'])
        await asyncio.sleep(self.yaml_data['ErrorMessageTimeout'])
        try:
            await ctx.message.delete()
            return
        except: return

    # all the emoji are from the bots.gg discord server.
    # If your bot is in there, it'll be able to use them
    def get_user_badges(self, user):
        author_flags = user.public_flags
        flags = dict(author_flags)
        emoji_flags = ""
        if flags['staff'] is True:
            emoji_flags = f"{emoji_flags} <:staff:860644241800429639>"
        if flags['partner'] is True:
            emoji_flags = f"{emoji_flags} <:partnernew:860644259107569685>"
        if flags['hypesquad'] is True:
            emoji_flags = f"{emoji_flags} <:hypesquad:860644277687943208>"
        if flags['bug_hunter'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter:585765206769139723>"
        if flags['hypesquad_bravery'] is True:
            emoji_flags = f"{emoji_flags} <:bravery:860644425319710760>"
        if flags['hypesquad_brilliance'] is True:
            emoji_flags = f"{emoji_flags} <:brilliance:860644445435199539>"
        if flags['hypesquad_balance'] is True:
            emoji_flags = f"{emoji_flags} <:balance:860644467933839410>"
        if flags['early_supporter'] is True:
            emoji_flags = f"{emoji_flags} <:supporter:860644501067268106>"
        if user.premium_since:
            emoji_flags = f"{emoji_flags} <:booster4:860644548887969832>"
        if flags['bug_hunter_level_2'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter_gold:850843414953984041>" #not from bots.gg
        if flags['verified_bot_developer'] is True:
            emoji_flags = f"{emoji_flags} <:earlybotdev:850843591756349450>" #not from bots.gg
        if emoji_flags == "": emoji_flags = None
        return emoji_flags


    @commands.command()
    async def invites(self, ctx, member:discord.Member=None):
        member = member or ctx.author
        invites = 0
        for invite in await ctx.guild.invites():
            if invite.inviter == member:
                invites += invite.uses
        embed = discord.Embed(description=f"{member} has invited **{invites}** member(s) to **{ctx.guild.name}**!", color=0x2F3136)
        await ctx.send(embed=embed)


    @commands.command(aliases = ['userinfo', 'ui'])
    async def uinfo(self, ctx, user: typing.Optional[discord.Member]):
        if not user: user = ctx.author
        # BADGES
        badges = self.get_user_badges(user)
        if badges: badges = f"\n<:store_tag:860644620857507901>**Badges:**{badges}"
        else: badges = ''
        # USERID
        userid = f"\n<:greyTick:860644729933791283>**ID:** `{user.id}`"
        # NICKNAME
        if user.nick: nick = f"\n<:nickname:850914031953903626>**Nickname:** `{user.nick}`"
        else: nick = ""
        # CREATION DATE
        date = user.created_at.strftime("%b %-d %Y at %-H:%M")
        created = f"\n<:invite:860644752281436171>**Created:** `{date} UTC`"
        # JOIN DATE
        if user.joined_at:
            date = user.joined_at.strftime("%b %-d %Y at %-H:%M")
            joined = f"\n<:joined:849392863557189633>**joined:** `{date} UTC`"
        else: joined = ""
        # GUILD OWNER
        if user is ctx.guild.owner:
            owner = f"\n<:owner:860644790005399573>**Owner:** <:check:314349398811475968>"
        else: owner = ""
        # BOT
        if user.bot:
            bot = f"\n<:botTag:860645571076030525>**Bot:** <:check:314349398811475968>"
        else: bot = ""
        # BOOSTER SINCE
        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:860644548887969832>**Boosting since:** `{date} UTC`"
        else: boost = ""

        # Join Order
        order = f"\n<:moved:848312880666640394>**Join position:** `{sorted(ctx.guild.members, key=lambda user: user.joined_at).index(user) + 1}`"

        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:860644548887969832>**Boosting since:** `{date} UTC`"
        else: boost = ""
        # ROLES
        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role: continue
            roles = f"{roles} {role.mention}"
        if roles != "":
            roles = f"\n<:role:860644904048132137>**roles:** {roles}"
        # EMBED
        embed = discord.Embed(color=ctx.me.color, description=f"""{badges}{owner}{bot}{userid}{created}{nick}{joined}{order}{boost}{roles}""")
        embed.set_author(name=user, icon_url=user.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        await ctx.send(embed=embed)


#------------------------------------------------------------#
#------------------------ KICK ------------------------------#
#------------------------------------------------------------#

    @commands.command()
    @commands.has_permissions(kick_members=True)
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
            if member.guild_permissions.ban_members == False or member.guild_permissions.kick_members == False:
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

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

#-----------------------------------------------------------#
#------------------------ BAN ------------------------------#
#-----------------------------------------------------------#

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to ban')
            return
        elif member == ctx.author:
            await self.error_message(ctx, 'You can\'t ban yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            await self.error_message(ctx, 'I\'m not high enough in role hierarchy to ban that member!')
            return
        if member.top_role <= ctx.author.top_role:
            if member.guild_permissions.ban_members == False or member.guild_permissions.kick_members == False:
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

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await self.perms_error(ctx)

#------------------------------------------------------------#
#------------------------ NICK ------------------------------#
#------------------------------------------------------------#

    @commands.command(aliases = ['sn', 'nick'])
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

    @commands.command(aliases=['clean', 'purge', 'delete'])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, argument: typing.Optional[int] = "noimput"):
        amount = argument
        if amount != "noimput":
            if amount <= 1000:
                await ctx.message.delete()
                await ctx.channel.purge(limit=amount)
                await ctx.send("🗑 Purge completed!", delete_after = 5)
            else:
                await ctx.message.delete()
                await ctx.channel.purge(limit=1000)
                await ctx.send("🗑 **[ERROR]** Applied limited of 1000 messages")
        else:
            await ctx.message.delete()
            await self.error_message(ctx, "Please specify amount of messages to purge!")

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

#------------------------------------------------------------#
#------------------------ MUTE ------------------------------#
#------------------------------------------------------------#

    @commands.command()
    async def mute(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to mute')
            return
        muterole = self.bot.get_guild(717140270789033984).get_role(self.yaml_data['MuteRole'])
        if muterole in member.roles:
            await self.error_message(ctx, f'{member} is already muted')
            return
        try:
            await member.add_roles(muterole)
            mem_embed=discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been muted by {ctx.author}", icon_url='https://i.imgur.com/hKNGsMb.png')
            mem_embed.set_image(url='https://i.imgur.com/hXbvCT4.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed=discord.Embed(description=f"""{ctx.author.mention} muted {member.mention} indefinitely...
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed=discord.Embed(description=f"""{ctx.author.mention} muted {member.mention} indefinitely...""", color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

#-------------------------------------------------------------#
#------------------------ UNMUTE -----------------------------#
#-------------------------------------------------------------#

    @commands.command()
    async def unmute(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to unmute')
            return
        muterole = ctx.guild.get_role(self.yaml_data['MuteRole'])
        if muterole not in member.roles:
            await self.error_message(ctx, f'{member} is not muted')
            return
        try:
            await member.remove_roles(muterole)
            mem_embed=discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been unmuted by {ctx.author}", icon_url='https://i.imgur.com/m1MtOVS.png')
            mem_embed.set_image(url='https://i.imgur.com/23XECtg.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed=discord.Embed(description=f"""{ctx.author.mention} unmuted {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed=discord.Embed(description=f"""{ctx.author.mention} unmuted {member.mention}""", color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')


#-----------------------------------------------------------------#
#------------------------ DENYMEDIA ------------------------------#
#-----------------------------------------------------------------#

    @commands.command(aliases=['nomedia', 'noimages', 'denyimages', 'noimg', 'md', 'mediaban', 'nm', 'mb', 'mban'])
    async def denymedia(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to deny media to')
            return
        muterole = self.bot.get_guild(717140270789033984).get_role(self.yaml_data['noMediaRole'])
        if muterole in member.roles:
            await self.error_message(ctx, f'{member} is already in deny media')
            return
        try:
            await member.add_roles(muterole)
            mem_embed=discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been denied permissions to send media by {ctx.author}", icon_url='https://i.imgur.com/hKNGsMb.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed=discord.Embed(description=f"""{ctx.author.mention} denied media pemrs to {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed=discord.Embed(description=f"""{ctx.author.mention} denied media pemrs to {member.mention}""", color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

#-----------------------------------------------------------------#
#------------------------ ALLOWMEDIA -----------------------------#
#-----------------------------------------------------------------#

    @commands.command(aliases=['yesmedia', 'yesimages', 'allowimages', 'yesimg', 'ma', 'mediaunban', 'ym', 'mub', 'munban'])
    async def allowmedia(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member deny media to')
            return
        muterole = ctx.guild.get_role(self.yaml_data['noMediaRole'])
        if muterole not in member.roles:
            await self.error_message(ctx, f'{member} is not in deny media')
            return
        try:
            await member.remove_roles(muterole)
            mem_embed=discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been allowed permissions to send media by {ctx.author}", icon_url='https://i.imgur.com/m1MtOVS.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed=discord.Embed(description=f"""{ctx.author.mention} returned media pemrs to {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed=discord.Embed(description=f"""{ctx.author.mention} returned media pemrs to {member.mention}""", color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

#---------------------------------------------------------------#
#------------------------ LOCKDOWN -----------------------------#
#---------------------------------------------------------------#

    @commands.command(aliases=['lock', 'ld'])
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx, textchannel: typing.Optional[discord.TextChannel], *, reason = None):

        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

        if not textchannel:
            await ctx.message.delete()
            textchannel = ctx.channel
        else:
            await ctx.message.add_reaction('🔓')

        perms = textchannel.overwrites_for(ctx.guild.default_role)
        perms.send_messages = False

        if reason:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f'locked by {ctx.author} - {reason}')
            embed=discord.Embed(description=f"{ctx.author.mention} has locked down {textchannel.mention} \n```reason: {reason}```", color=ctx.me.color)
        else:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f'locked by {ctx.author}')
            embed=discord.Embed(description=f"{ctx.author.mention} has locked down {textchannel.mention}", color=ctx.me.color)
        await textchannel.send(embed=embed)

#-------------------------------------------------------------#
#------------------------ UNLOCK -----------------------------#
#-------------------------------------------------------------#

    @lockdown.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

    @commands.command(aliases=['unlock', 'uld'])
    @commands.has_permissions(manage_channels=True)
    async def unlockdown(self, ctx, textchannel: typing.Optional[discord.TextChannel], *, reason = None):

        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

        if not textchannel:
            await ctx.message.delete()
            textchannel = ctx.channel
        else:
            await ctx.message.add_reaction('🔓')

        perms = textchannel.overwrites_for(ctx.guild.default_role)
        perms.send_messages = True

        if reason:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f'unlocked by {ctx.author} - {reason}')
            embed=discord.Embed(description=f"{ctx.author.mention} has unlocked {textchannel.mention} \n```reason: {reason}```", color=ctx.me.color)
        else:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f'unlocked by {ctx.author}')
            embed=discord.Embed(description=f"{ctx.author.mention} has unlocked {textchannel.mention}", color=ctx.me.color)
        await textchannel.send(embed=embed)

    @unlockdown.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

#--------------------------------------------------------------------#
#------------------------ MOVE MESSAGES -----------------------------#
#--------------------------------------------------------------------#

    @commands.command()
    async def move(self, ctx, amount: typing.Optional[int], channel: typing.Optional[discord.TextChannel]):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

        # Limitation checking

        if channel == None:
            await self.error_message(ctx, 'you must specify a channel: .move <amount> <#channel>')
            ctx.command.reset_cooldown(ctx)
            return
        elif channel == ctx.channel:
            await self.error_message(ctx, "channel can't be this channel: .move <amount> <#channel>")
            ctx.command.reset_cooldown(ctx)
            return
        if not channel.permissions_for(ctx.guild.me).manage_webhooks and not ctx.channel.permissions_for(ctx.me).manage_messages:
            await self.error_message(ctx, 'missing necessary permissions')
            ctx.command.reset_cooldown(ctx)
            return
        if amount == None:
             await self.error_message(ctx, 'you must specify an amount: .move <amount> <#channel>')
             ctx.command.reset_cooldown(ctx)
             return
        elif amount > 20:
            await self.error_message(ctx, 'you can only move 15 messages!')
            ctx.command.reset_cooldown(ctx)
        else:
            try:
                await ctx.message.delete()
            except:
                await ctx.send('missing manage_messages permission', delete_after=5)
                ctx.command.reset_cooldown(ctx)
                return


        # Actual copying and pasting


        history = []
        async for message in ctx.channel.history(limit = amount):
            history.append(message)
            await asyncio.sleep(0.001)
        history.reverse()

        try:
            webhook = await channel.create_webhook(name = "DB-Move", reason = "created webhook for move command")
        except:
            await ctx.send(f"i'm missing manage_webhooks permission in {channel.mention}",delete_after=5)
            ctx.command.reset_cooldown(ctx)
            return

        for message in history:
            if message.attachments:
                file = ctx.message.attachments[0]
                myfile = await file.to_file()
                if message.embeds:
                    embed = message.embeds[0]
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar_url, file = myfile, content = message.content, embed=embed)
                else:
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar_url, file = myfile, content = message.content)
            else:
                if message.embeds:
                    embed = message.embeds[0]
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar_url, content = message.content, embed=embed)
                else:
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar_url, content = message.content)
            try: await message.delete()
            except: pass
            await asyncio.sleep(0.5)

        await webhook.delete()
        await ctx.send(f'moved {amount} messages to {channel.mention}')


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



    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx, *, args):
        """Mass-bans members from the server.
        do ""%PRE%help massban help" for help"""
        # For some reason there are cases due to caching that ctx.author
        # can be a User even in a guild only context
        # Rather than trying to work out the kink with it
        # Just upgrade the member itself.
        if not isinstance(ctx.author, discord.Member):
            try:
                author = await ctx.guild.fetch_member(ctx.author.id)
            except discord.HTTPException:
                return await ctx.send('Somehow, Discord does not seem to think you are in this server.')
        else:
            author = ctx.author

        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument('--channel', '-c')
        parser.add_argument('--reason', '-r')
        parser.add_argument('--search', type=int, default=100)
        parser.add_argument('--regex')
        parser.add_argument('--no-avatar', action='store_true')
        parser.add_argument('--no-roles', action='store_true')
        parser.add_argument('--created', type=int)
        parser.add_argument('--joined', type=int)
        parser.add_argument('--joined-before', type=int)
        parser.add_argument('--joined-after', type=int)
        parser.add_argument('--contains')
        parser.add_argument('--starts')
        parser.add_argument('--ends')
        parser.add_argument('--match')
        parser.add_argument('--show', action='store_true')
        parser.add_argument('--embeds', action='store_const', const=lambda m: len(m.embeds))
        parser.add_argument('--files', action='store_const', const=lambda m: len(m.attachments))
        parser.add_argument('--after', type=int)
        parser.add_argument('--before', type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            return await ctx.send(str(e))

        members = []

        if args.channel:
            channel = await commands.TextChannelConverter().convert(ctx, args.channel)
            before = args.before and discord.Object(id=args.before)
            after = args.after and discord.Object(id=args.after)
            predicates = []
            if args.contains:
                predicates.append(lambda m: args.contains in m.content)
            if args.starts:
                predicates.append(lambda m: m.content.startswith(args.starts))
            if args.ends:
                predicates.append(lambda m: m.content.endswith(args.ends))
            if args.match:
                try:
                    _match = re.compile(args.match)
                except re.error as e:
                    return await ctx.send(f'Invalid regex passed to `--match`: {e}')
                else:
                    predicates.append(lambda m, x=_match: x.match(m.content))
            if args.embeds:
                predicates.append(args.embeds)
            if args.files:
                predicates.append(args.files)

            async for message in channel.history(limit=min(max(1, args.search), 2000), before=before, after=after):
                if all(p(message) for p in predicates):
                    members.append(message.author)
        else:
            if ctx.guild.chunked:
                members = ctx.guild.members
            else:
                async with ctx.typing():
                    await ctx.guild.chunk(cache=True)
                members = ctx.guild.members

        # member filters
        predicates = [
            lambda m: isinstance(m, discord.Member) and can_execute_action(ctx, author, m), # Only if applicable
            lambda m: not m.bot, # No bots
            lambda m: m.discriminator != '0000', # No deleted users
        ]

        converter = commands.MemberConverter()

        if args.regex:
            try:
                _regex = re.compile(args.regex)
            except re.error as e:
                return await ctx.send(f'Invalid regex passed to `--regex`: {e}')
            else:
                predicates.append(lambda m, x=_regex: x.match(m.name))

        if args.no_avatar:
            predicates.append(lambda m: m.avatar == m.default_avatar)
        if args.no_roles:
            predicates.append(lambda m: len(getattr(m, 'roles', [])) <= 1)

        now = discord.utils.utcnow()
        if args.created:
            def created(member, *, offset=now - datetime.timedelta(minutes=args.created)):
                return member.created_at > offset
            predicates.append(created)
        if args.joined:
            def joined(member, *, offset=now - datetime.timedelta(minutes=args.joined)):
                if isinstance(member, discord.User):
                    # If the member is a user then they left already
                    return True
                return member.joined_at and member.joined_at > offset
            predicates.append(joined)
        if args.joined_after:
            _joined_after_member = await converter.convert(ctx, str(args.joined_after))
            def joined_after(member, *, _other=_joined_after_member):
                return member.joined_at and _other.joined_at and member.joined_at > _other.joined_at
            predicates.append(joined_after)
        if args.joined_before:
            _joined_before_member = await converter.convert(ctx, str(args.joined_before))
            def joined_before(member, *, _other=_joined_before_member):
                return member.joined_at and _other.joined_at and member.joined_at < _other.joined_at
            predicates.append(joined_before)

        members = {m for m in members if all(p(m) for p in predicates)}
        if len(members) == 0:
            return await ctx.send('No members found matching criteria.')

        if args.show:
            members = sorted(members, key=lambda m: m.joined_at or now)
            fmt = "\n".join(f'{m.id}\tJoined: {m.joined_at}\tCreated: {m.created_at}\t{m}' for m in members)
            content = f'Current Time: {discord.utils.utcnow()}\nTotal members: {len(members)}\n{fmt}'
            file = discord.File(io.BytesIO(content.encode('utf-8')), filename='members.txt')
            return await ctx.send(file=file)

        if args.reason is None:
            return await ctx.send('--reason flag is required.')
        else:
            reason = await ActionReason().convert(ctx, args.reason)

        confirm = await ctx.prompt(f'This will ban **{plural(len(members)):member}**. Are you sure?')
        if not confirm:
            return await ctx.send('Aborting.')

        count = 0
        for member in members:
            try:
                await ctx.guild.ban(member, reason=reason)
            except discord.HTTPException:
                pass
            else:
                count += 1

        await ctx.send(f'Banned {count}/{len(members)}')

    @massban.command(name="help")
    async def _help(self, ctx):
        """Mass bans multiple members from the server.
        This command has a powerful "command line" syntax. To use this command
        you and the bot must both have Ban Members permission. **Every option is optional.**
        Users are only banned **if and only if** all conditions are met.
        The following options are valid.
        --channel / -c: Channel to search for message history.
        --reason / -r: The reason for the ban.
        --regex: Regex that usernames must match.
        --created: Matches users whose accounts were created less than specified minutes ago.
        --joined: Matches users that joined less than specified minutes ago.
        --joined-before: Matches users who joined before the member ID given.
        --joined-after: Matches users who joined after the member ID given.
        --no-avatar: Matches users who have no avatar. (no arguments)
        --no-roles: Matches users that have no role. (no arguments)
        --show: Show members instead of banning them (no arguments).
        Message history filters (Requires --channel):
        --contains: A substring to search for in the message.
        --starts: A substring to search if the message starts with.
        --ends: A substring to search if the message ends with.
        --match: A regex to match the message content to.
        --search: How many messages to search. Default 100. Max 2000.
        --after: Messages must come after this message ID.
        --before: Messages must come before this message ID.
        --files: Checks if the message has attachments (no arguments).
        --embeds: Checks if the message has embeds (no arguments).
        """
        return


    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def softban(self, ctx, member: discord.User, *, reason: ActionReason = None):
        """Soft bans a member from the server.
        A softban is basically banning the member from the server but
        then unbanning the member as well. This allows you to essentially
        kick the member while removing their messages.
        """

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        await ctx.guild.ban(member, reason=reason)
        await ctx.guild.unban(member, reason=reason)
        await ctx.send('\N{OK HAND SIGN}')

def setup(bot):
    bot.add_cog(moderation(bot))

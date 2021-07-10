import typing, discord, asyncio, yaml, aiohttp
from discord.ext import commands

class moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            guild = full_yaml['guildID']
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(guild).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml
        self.server = self.bot.get_guild(guild)
        self.console = self.bot.get_channel(full_yaml['ConsoleCommandsChannel'])

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

    async def namecheck(self, argument):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                if cs.status == 204: user = None
                elif cs.status == 400: user = None
                else:
                    res = await cs.json()
                    user = res["name"]
                return user

#------------------------------------------------------------#
#------------------------ KICK ------------------------------#
#------------------------------------------------------------#

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
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
        muterole = self.server.get_role(self.yaml_data['MuteRole'])
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

#---------------------------------------------------------------#
#------------------------ GameBan ------------------------------#
#---------------------------------------------------------------#

    @commands.command(aliases=['smpban', 'gban'])
    async def GameBan(self, ctx, argument: typing.Optional[str] = 'invalid name', *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        name = await self.namecheck(argument)
        if name:
            if reason:
                await self.console.send(f'ban {name} {reason}')
                embed=discord.Embed(description=f"""{ctx.author.mention} banned **{name}** from the server
```reason: {reason}```""", color=ctx.me.color)
            else:
                await self.console.send(f'ban {name}')
                embed=discord.Embed(description=f"""{ctx.author.mention} banned **{name}** from the server""", color=ctx.me.color)
            await ctx.send(embed=embed)
        else:
            await self.error_message(ctx, 'That username is invalid!')

#-----------------------------------------------------------------#
#------------------------ GameUnban ------------------------------#
#-----------------------------------------------------------------#

    @commands.command(aliases=['smpunban', 'gunban'])
    async def GameUnban(self, ctx, argument: typing.Optional[str] = 'invalid name', *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        name = await self.namecheck(argument)
        if name:
            if reason:
                await self.console.send(f'unban {name}')
                embed=discord.Embed(description=f"""{ctx.author.mention} unbanned **{name}** from the server
```reason: {reason}```""", color=ctx.me.color)
            else:
                await self.console.send(f'unban {name}')
                embed=discord.Embed(description=f"""{ctx.author.mention} unbanned **{name}** from the server""", color=ctx.me.color)
            await ctx.send(embed=embed)
        else:
            await self.error_message(ctx, 'That username is invalid!')

#-------------------------------------------------------------#
#------------------------ VCBAN ------------------------------#
#-------------------------------------------------------------#

    @commands.command()
    async def vcban(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to VC-Ban')
            return
        vcbanrole = self.server.get_role(self.yaml_data['VcBanRole'])
        if vcbanrole in member.roles:
            await self.error_message(ctx, f'{member} is already VC-Banned')
            return
        try:
            await member.add_roles(vcbanrole)
            await member.move_to(None)
            mem_embed=discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been VC-Banned by {ctx.author}", icon_url='https://i.imgur.com/hKNGsMb.png')
            mem_embed.set_image(url='https://i.imgur.com/hXbvCT4.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed=discord.Embed(description=f"""{ctx.author.mention} VC-Banned {member.mention} indefinitely...
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed=discord.Embed(description=f"""{ctx.author.mention} VC-Banned {member.mention} indefinitely...""", color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

#--------------------------------------------------------------#
#------------------------ UNVCBAN -----------------------------#
#--------------------------------------------------------------#

    @commands.command()
    async def vcunban(self, ctx, member: typing.Optional[discord.Member] = None, *, reason = None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to VC-Ban')
            return
        vcbanrole = ctx.guild.get_role(self.yaml_data['VcBanRole'])
        if vcbanrole not in member.roles:
            await self.error_message(ctx, f'{member} is not VC-Banned')
            return
        try:
            await member.remove_roles(vcbanrole)
            mem_embed=discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been VC-Unbanned by {ctx.author}", icon_url='https://i.imgur.com/m1MtOVS.png')
            mem_embed.set_image(url='https://i.imgur.com/23XECtg.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed=discord.Embed(description=f"""{ctx.author.mention} VC-Unbanned {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed=discord.Embed(description=f"""{ctx.author.mention} VC-Unbanned {member.mention}""", color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')



def setup(bot):
    bot.add_cog(moderation(bot))

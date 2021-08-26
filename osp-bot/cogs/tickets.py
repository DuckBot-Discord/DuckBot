import discord, asyncio, typing, aiohttp, random, json, yaml, re
from discord.ext import commands, menus
import helpers

class tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(full_yaml['guildID']).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml
        self.ticket_staff = self.bot.get_guild(full_yaml['guildID']).get_role(self.yaml_data['TicketStaffRole'])
        tstaff = self.bot.get_guild(full_yaml['guildID']).get_role(self.yaml_data['TicketStaffRole'])
        self.ticket_log = self.bot.get_channel(full_yaml['TicketLogChannel'])

    async def get_webhook(self, channel):
        hookslist = await channel.webhooks()
        if hookslist:
            for hook in hookslist:
                if hook.token:
                    return hook
                else: continue
        hook = await channel.create_webhook(name="OSP-Bot ticket logging")
        return hook

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await ctx.message.delete(delay=5)
        return

    @commands.command()
    @commands.guild_only()
    @helpers.is_osp_server()
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def ticket(self, ctx):
        embed=discord.Embed(color=0x47B781, description=f"<a:loading:864708067496296468> Checking, please wait...")
        message = await ctx.send(ctx.author.mention, embed=embed)

        category = self.bot.get_channel(self.yaml_data['TicketsCategory'])

        if category.text_channels:
            for channel in category.text_channels:
                if channel.permissions_for(ctx.author).send_messages and self.ticket_staff not in ctx.author.roles:
                    await asyncio.sleep(1)
                    err=discord.Embed(color=0xD7342A, description=f"**you already have an open ticket.** ({channel.mention})")
                    await message.edit(content=ctx.author.mention, embed=err)
                    return
                else: continue

        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        await asyncio.sleep(2)
        embed=discord.Embed(color=0x47B781,
                            description=f"""__Hello {ctx.author.mention}, welcome to the ticket creation tool.__

**Please describe your issue** _(custom emojis will display as `:emoji:` if they are not from this server!)_

Take your time, you have 10 minutes to do this before this process is cancelled.""")
        embed.set_author(name=f"{ctx.author.display_name}'s ticket", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Send \"cancel\" to cancel")
        await message.edit(content=ctx.author.mention, embed=embed)

        try:
            #                             event = on_message without on_
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)
            # msg = discord.Message
        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            err=discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time. Feel free to try again!**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if msg.content.lower() == "cancel":
                    try: await msg.delete()
                    except: pass
                    err=discord.Embed(color=0xD7342A, description=f"**Cancelled!**")
                    await message.edit(content=ctx.author.mention, embed=err)
                    return

            try: await msg.delete()
            except: pass
            embed=discord.Embed(color=0x47B781,
                                description=f"""{ctx.author.mention} | {ctx.author.id}

**Issue description:**
{msg.content}""")
            if msg.attachments:
                file = msg.attachments[0]
                spoiler = file.is_spoiler()
                if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                    embed.set_image(url=file.url)
                elif spoiler:
                    embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
                else:
                    embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)

            embed.set_author(name=f"{ctx.author.display_name}'s ticket", icon_url=ctx.author.display_avatar.url)
            embed.add_field(name="Do you want to open this ticket?", value="_ _")
            await message.edit(content=ctx.author.mention, embed=embed)

        def reactioncheck(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) in ['✅', '❌']

        await message.add_reaction("✅")
        await message.add_reaction("❌")
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reactioncheck)

        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            err=discord.Embed(color=0xD7342A, description=f"**Confirmation failed**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if str(reaction.emoji) == '✅':
                await message.clear_reactions()
                success=discord.Embed(color=0x47B781, description=f"**<a:loading:864708067496296468> Creating ticket, please wait**")
                await message.edit(content=ctx.author.mention, embed=success)
                await asyncio.sleep(1)
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True),
                    self.ticket_staff: discord.PermissionOverwrite(read_messages=True, manage_messages=True)
                }
                first = msg.content
                first = re.sub(r'[^a-zA-Z0-9_ ]+', '', first)
                first = first.split()[:10]
                first = "-".join(first)
                ticketname=f"{ctx.author.name}-{first}"
                ticketchannel = await category.create_text_channel(ticketname[0:100], overwrites=overwrites, topic = f"creating topic...")

                success=discord.Embed(color=0x47B781, description=f"**Ticket created at {ticketchannel.mention}!**")
                await message.edit(content=ctx.author.mention, embed=success)
                await asyncio.sleep(0.2)

                msgf = ""
                if msg.attachments:
                    file = msg.attachments[0]
                    spoiler = file.is_spoiler()
                    if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                        pass
                    elif spoiler:
                        msgf=f'\n\n**attachment:** ||[{file.filename}]({file.url})||'
                    else:
                        msgf=f'\n\n**attachment:** [{file.filename}]({file.url})'

                embed=discord.Embed(color=0x47B781,
                                    description=f"""{ctx.author.mention} | {ctx.author.id}

**Issue description:**
{msg.content}{msgf}
""")
                if msg.attachments:
                    file = msg.attachments[0]
                    spoiler = file.is_spoiler()
                    if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                        embed.set_image(url=file.url)

                embed.add_field(name="Actions:", value="🚪 Leave | 🔒 Close (staff-only)\n\".leave\" also works")
                embed.set_author(name=f"{ctx.author.display_name}'s ticket", icon_url=ctx.author.display_avatar.url)
                tickmsg = await ticketchannel.send(content=f"{ctx.author.mention} opened a ticket, {self.ticket_staff.mention}", embed=embed)
                await tickmsg.add_reaction('🔒')
                await tickmsg.add_reaction('🚪')
                print("attempting to edit")
                try:
                    print("before edit")
                    await ticketchannel.edit(topic = f"{ctx.author.display_name}'s ticket. \n\nDescription:\n{msg.content[0:850]} ​​​​​​​​​​​​​​​​​​​​{tickmsg.id}")
                    print("successful edit")
                except: print("unsuccessful edit.")
                print("after edit")
                TicketLog = await self.get_webhook(self.ticket_log)
                embed = discord.Embed(color=0x47B781, title="Ticket opened", description= f"""
{ctx.author.mention} opened a ticket: **{ticketchannel.name}** ({ticketchannel.mention})

**Issue description:**
{msg.content}
""")
                embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
                await TicketLog.send(embed=embed)
            else:
                await message.clear_reactions()
                err=discord.Embed(color=0xD7342A, description=f"**Cancelled!**")
                await message.edit(content=ctx.author.mention, embed=err)
                return


    @commands.command(help="Adds a member to a ticket", usage = "<member>", aliases=["addm", "am"])
    @commands.guild_only()
    @helpers.is_osp_server()
    @commands.has_role(864737541726142474)
    async def addmember(self, ctx, member: typing.Optional[discord.Member]):
        if self.ticket_staff not in ctx.author.roles:
            await self.perms_error(ctx)
            return
        category = self.bot.get_channel(self.yaml_data['TicketsCategory'])
        if ctx.channel.category != category:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="This channel is not a ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        if member == None:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="Please specify a member to add to this ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        if ctx.channel.permissions_for(member).read_messages:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description=f"{member.mention} can already see this ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        perms = ctx.channel.overwrites_for(member)
        perms.send_messages = True
        perms.read_messages = True
        await ctx.channel.set_permissions(member, overwrite=perms, reason=f"{member.name} was added to a ticket")
        embed=discord.Embed(color=0x47B781, title=f"+ {member} added", description=f"""
{ctx.author.mention} added {member.mention} to this ticket""")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await ctx.send(f"{member.mention} was added to this ticket", embed=embed)
        #LOG
        TicketLog = await self.get_webhook(self.ticket_log)
        logemb = discord.Embed(color=0x4286F4, title=f"{member} added to #{ctx.channel.name}", description= f"""
        {ctx.author.mention} added {member.mention} to {ctx.channel.mention}""")
        logemb.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await TicketLog.send(embed=logemb)
        return

    @commands.command(help="Removes a member from a ticket", usage = "<member>", aliases=["rmem"])
    @commands.guild_only()
    @helpers.is_osp_server()
    @commands.has_role(864737541726142474)
    async def removemember(self, ctx, member: typing.Optional[discord.Member]):
        category = self.bot.get_channel(self.yaml_data['TicketsCategory'])
        if ctx.channel.category != category:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="This channel is not a ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        if member == None:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="Please specify a member to add to this ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        if not ctx.channel.permissions_for(member).read_messages:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description=f"{member.mention} can't see this ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        perms = ctx.channel.overwrites_for(member)
        perms.send_messages = False
        perms.read_messages = False
        await ctx.channel.set_permissions(member, overwrite=perms, reason=f"{member.name} was removed from a ticket")
        embed=discord.Embed(color=0xD7342A, title=f"- {member} removed", description=f"""
{ctx.author.mention} removed {member.mention} from this ticket""")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await ctx.send(f"{member.mention} removed from this ticket", embed=embed)
        #LOG
        TicketLog = await self.get_webhook(self.ticket_log)
        logemb = discord.Embed(color=0x47B781, title=f"{member} removed from #{ctx.channel.name}", description= f"""
        {ctx.author.mention} removed {member.mention} from {ctx.channel.mention}""")
        logemb.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await TicketLog.send(embed=logemb)
        return

    @commands.command(help="Allows a member to leave a ticket", aliases=["leave"])
    @commands.guild_only()
    @helpers.is_osp_server()
    async def leaveticket(self, ctx):
        category = self.bot.get_channel(self.yaml_data['TicketsCategory'])
        if ctx.channel.category != category:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="This channel is not a ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return

        embed=discord.Embed(color=0x47B781,
                            description=f"""__Hey {ctx.author.mention}, we see you're leaving this ticket.__

**Want to tell us why?**

You have 5 minutes to do so.""")

        embed.set_author(name=f"{ctx.author} is leaving the ticket", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Send \"no\" if you don't want to\nSend \"cancel\" to cancel")
        lmsg = await ctx.channel.send(ctx.author.mention, embed=embed)

        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        try:
            #                             event = on_message without on_
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 300.0)
            # msg = discord.Message
        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            err=discord.Embed(color=0xD7342A, description=f"**{ctx.author} left the ticket.**")
            await lmsg.edit(content=ctx.author.mention, embed=err)
        else:
            if msg.content.lower() == "no":
                try: await msg.delete()
                except: pass
                err=discord.Embed(color=0xD7342A, description=f"**{ctx.author} left the ticket.**")
                await lmsg.edit(content=ctx.author.mention, embed=err)
            elif msg.content.lower() == "cancel":
                try: await msg.delete()
                except: pass
                err=discord.Embed(color=0xD7342A, description="**Cancelled!**")
                await lmsg.edit(content=ctx.author.mention, embed=err)
                return
            else:
                try: await msg.delete()
                except: pass
                embed=discord.Embed(color=0xD7342A,
                                    description=f"""**{ctx.author} left the ticket.**
**Reason:**
{msg.content}""")
                await lmsg.edit(content=ctx.author.mention, embed=embed)

        perms = ctx.channel.overwrites_for(ctx.author)
        perms.send_messages = False
        perms.read_messages = False
        await ctx.channel.set_permissions(ctx.author, overwrite=perms, reason=f"{ctx.author.name} left ticket")
        #LOG
        TicketLog = await self.get_webhook(self.ticket_log)
        logemb = discord.Embed(color=0xD7342A, title=f"Left ticket #{ctx.channel.name}", description= f"""
{ctx.author.mention} left ticket: {ctx.channel.mention}""")
        if msg:
            if msg.content and msg.content.lower() != "no":
                logemb.add_field(name="Reason:", value=msg.content)
        logemb.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await TicketLog.send(embed=logemb)

    @commands.command(help="Adds a member to a ticket",
                      usage="<member>",
                      aliases=["addm", "am"])
    @commands.guild_only()
    @helpers.is_osp_server()
    @commands.has_role(864737541726142474)
    async def addmember(self, ctx, member: typing.Optional[discord.Member]):
        category = self.bot.get_channel(self.yaml_data['TicketsCategory'])
        if ctx.channel.category != category:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="This channel is not a ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        if member == None:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="Please specify a member to add to this ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        if ctx.channel.permissions_for(member).read_messages:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description=f"{member.mention} can already see this ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        perms = ctx.channel.overwrites_for(member)
        perms.send_messages = True
        perms.read_messages = True
        await ctx.channel.set_permissions(member, overwrite=perms, reason=f"{member.name} was added to a ticket")
        embed=discord.Embed(color=0x47B781, title=f"+ {member} added", description=f"""
{ctx.author.mention} added {member.mention} to this ticket""")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await ctx.send(f"{member.mention} was added to this ticket", embed=embed)
        #LOG
        TicketLog = await self.get_webhook(self.ticket_log)
        logemb = discord.Embed(color=0x4286F4, title=f"{member} added to #{ctx.channel.name}", description= f"""
        {ctx.author.mention} added {member.mention} to {ctx.channel.mention}""")
        logemb.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await TicketLog.send(embed=logemb)
        return

    @commands.command(aliases=["closeticket"])
    @commands.guild_only()
    @helpers.is_osp_server()
    @commands.has_role(864737541726142474)
    async def close(self, ctx, *, reason: typing.Optional[str]):
        category = self.bot.get_channel(self.yaml_data['TicketsCategory'])
        if ctx.channel.category != category:
            await ctx.send(embed=discord.Embed(color=0xD7342A, description="This channel is not a ticket!"), delete_after=5)
            await ctx.message.delete(delay=5)
            return
        try: msgid = int(ctx.channel.topic.split(" ​​​​​​​​​​​​​​​​​​​​")[-1])
        except: return await ctx.send("something went wrong getting the message ID :( use the reaction menu instead.")
        await ctx.send(msgid)


        message = await ctx.channel.fetch_message(msgid)
        embed = message.embeds[0]
        embed.clear_fields()
        embed.add_field(name="Actions:", value="📁 Archive (staff-only) | 🗑 Delete (staff-only)")
        await message.edit(content=message.content, embed=embed)

        overwrites = {
            message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.ticket_staff: discord.PermissionOverwrite(read_messages=True, manage_messages=True)
        }
        await ctx.channel.edit(overwrites=overwrites)
        await message.clear_reactions()
        await ctx.channel.send("🔐 This ticket is now locked")
        await message.add_reaction("📁")
        await message.add_reaction("🗑")

        #LOG
        TicketLog = await self.get_webhook(self.ticket_log)
        if reason:
            logemb = discord.Embed(color=0x4286F4, title=f"Ticket #{ctx.channel.name} closed", description= f"""
            {ctx.author.mention} closed ticket: {ctx.channel.mention}

            **reason:**
            {reason}""")
        else:
            logemb = discord.Embed(color=0x4286F4, title=f"Ticket #{ctx.channel.name} closed", description= f"""
            {ctx.author.mention} closed ticket: {ctx.channel.mention}""")
        logemb.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await TicketLog.send(embed=logemb)
        return

def setup(bot):
    bot.add_cog(tickets(bot))

"""
str.split(" ​​​​​​​​​​​​​​​​​​​​")
"""

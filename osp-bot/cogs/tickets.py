import discord, asyncio, typing, aiohttp, random, json, yaml
from discord.ext import commands, menus

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

    @commands.command()
    @commands.guild_only()
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

**Please describe your issue** _(images will not be saved! neither will emojis from other servers). You can use them once the ticket is open._

Take your time, you have 10 minutes to do this before this process is cancelled.""")
        embed.set_author(name=f"{ctx.author.display_name}'s ticket", icon_url=ctx.author.avatar_url)
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

            embed.set_author(name=f"{ctx.author.display_name}'s ticket", icon_url=ctx.author.avatar_url)
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
                ticketchannel = await category.create_text_channel(f"{ctx.author.name}", overwrites=overwrites, topic = f"{ctx.author.display_name}'s ticket. \n\nDescription:\n{msg.content}")

                success=discord.Embed(color=0x47B781, description=f"**Ticket created at {ticketchannel.mention}!**")
                await message.edit(content=ctx.author.mention, embed=success)
                await asyncio.sleep(0.2)

                embed=discord.Embed(color=0x47B781,
                                    description=f"""{ctx.author.mention} | {ctx.author.id}

**Issue description:**
{msg.content}
""")
                embed.add_field(name="Actions:", value="Leave: 🚪 | Close (staff-only): 🔒")
                embed.set_author(name=f"{ctx.author.display_name}'s ticket", icon_url=ctx.author.avatar_url)
                tickmsg = await ticketchannel.send(content=f"{ctx.author.mention} opened a ticket, {self.ticket_staff.mention}", embed=embed)
                await tickmsg.add_reaction('🔒')
                await tickmsg.add_reaction('🚪')

                TicketLog = await self.get_webhook(self.ticket_log)
                embed = discord.Embed(color=0x47B781, title="Ticket opened", description= f"""
{ctx.author.mention} opened a ticket: **{ticketchannel.name}** ({ticketchannel.mention})

**Issue description:**
{msg.content}
""")
                embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
                await TicketLog.send(embed=embed)
            else:
                await message.clear_reactions()
                err=discord.Embed(color=0xD7342A, description=f"**Cancelled!**")
                await message.edit(content=ctx.author.mention, embed=err)
                return

def setup(bot):
    bot.add_cog(tickets(bot))

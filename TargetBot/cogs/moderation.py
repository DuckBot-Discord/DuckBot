import typing, discord, asyncio, yaml
from discord.ext import commands

class moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
        self.yaml_data = full_yaml

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member : discord.Member, *, reason: typing.Optional[str] = "No reason specified"):
        if member.top_role < ctx.author.top_role:
            if member.guild_permissions.kick_members == False:
                try:
                    await member.send(f"""**{ctx.message.author}** has kicked **you** from **{ctx.guild.name}**
**Reason:** `{reason}`""")
                    await member.kick(reason=reason)
                    await ctx.send(f"""**{ctx.message.author}** has kicked **{member}**!
    **Reason:** `{reason}` | DM sent: ✅""")
                except discord.HTTPException:
                    await member.kick(reason=reason)
                    await ctx.send(f"""**{ctx.message.author}** has kicked **{member}**!
    **Reason:** `{reason}` | DM sent: ❌""")

            else:
                await ctx.send(f"**{ctx.message.author}**, you can't kick another moderator!", delete_after=10)
                await ctx.message.delete()

        else:
            await ctx.send(f"**{member}** is higher than you in role hierarchy!", delete_after=10)
            await asyncio.sleep (2)
            await ctx.message.delete()

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep (2)
            await ctx.message.delete()

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member : discord.Member, *, reason: typing.Optional[str] = "No reason specified"):
        if member.top_role < ctx.author.top_role:
            if member.guild_permissions.ban_members == False or member.guild_permissions.kick_members == False:
                try:
                    await member.send(f"""**{ctx.message.author}** has banned **you** from **{ctx.guild.name}**
**Reason:** `{reason}`""")
                    await member.ban(reason=reason)
                    await ctx.send(f"""**{ctx.message.author}** has banned **{member}**!
    **Reason:** `{reason}` | DM sent: ✅""")
                except discord.HTTPException:
                    await member.ban(reason=reason)
                    await ctx.send(f"""**{ctx.message.author}** has banned **{member}**!
    **Reason:** `{reason}` | DM sent: ❌""")
            else:
                await ctx.send(f"**{ctx.message.author}**, you can't ban another moderator!", delete_after=10)
                await ctx.message.delete()

        else:
            await ctx.send(f"**{member}** is higher than you in role hierarchy!", delete_after=10)
            await asyncio.sleep (2)
            await ctx.message.delete()

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep (2)
            await ctx.message.delete()

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
                await ctx.send(f'🚫 Bot not high enough in role hierarchy 🚫', delete_after=15)
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('#️⃣')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
                return
        elif ctx.channel.permissions_for(ctx.author).manage_nicknames:
            if member.top_role >= ctx.author.top_role:
                await ctx.send("⚠ Cannot edit nick for members equal or above yourself!")
                return
            try:
                await member.edit(nick=new)
                await member.edit(nick=new)
                await ctx.send(f"""✏ {ctx.author.mention} edited nick for **{member}**
**`{old}`** -> **`{new}`**""")
                try: await ctx.message.delete()
                except discord.Forbidden: return
            except discord.Forbidden:
                await ctx.send(f'🚫 Bot not high enough in role hierarchy 🚫', delete_after=15)
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('#️⃣')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
        elif member == ctx.author and ctx.channel.permissions_for(ctx.author).change_nickname:
            await ctx.send(f"""🚫 You can only change your own nick!
> .nick {ctx.author.mention} `<new nick>`""", delete_after=15)
            return
        else:
            await ctx.message.add_reaction('🚫')

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
                await ctx.send("🗑 **[ERROR]** Applied limited of 1000 messages", delete_after=10)
        else:
            await ctx.message.delete()
            await ctx.send("**[PURGE]** The argument must be a number!", delete_after = 5)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep(3)
            await ctx.message.delete()

def setup(bot):
    bot.add_cog(moderation(bot))

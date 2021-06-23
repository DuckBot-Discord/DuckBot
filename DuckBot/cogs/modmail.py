import discord, asyncio, typing
from discord.ext import commands

class modmail(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild: return
        if message.author == self.bot.user: return
        if message.content.startswith('.'):
            await message.channel.send('⚠ messages starting with `.` will not be sent ⚠', delete_after=5)
            return
        pattern = '^([0-9]{4})'

        channel = self.bot.get_channel(830991980850446366)

        embed = discord.Embed(color=0xD7342A)
        if message.content:
            embed.add_field(name=f'<:incomingarrow:848312881070080001> **{message.author}**', value=f'{message.content}')
        else:
            embed.add_field(name=f'<:incomingarrow:848312881070080001> **{message.author}**', value=f'_ _')
        embed.set_footer(text=f'!dm {message.author.id}')
        if message.attachments:
            file = message.attachments[0]
            spoiler = file.is_spoiler()
            if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
            elif spoiler:
                embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
            else:
                embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
        await channel.send(embed=embed)
        await message.add_reaction('📬')
        await asyncio.sleep(2.5)
        await message.remove_reaction('📬', self.bot.user)

###############################################################################
###############################################################################

    @commands.command(aliases=['md', 'pm'])
    @commands.is_owner()
    async def dm(self, ctx, id: typing.Optional[int], *, message = ""):
        if id == None:
            await ctx.message.add_reaction('🔢')
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return
        if len(f'{id}') != 18:
            await ctx.message.add_reaction('#️⃣')
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return

        member = self.bot.get_user(id)

        if member == None:
            await ctx.message.add_reaction('⁉')
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return

        channel = self.bot.get_channel(830991980850446366)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        try:
            if ctx.message.attachments:
                file = ctx.message.attachments[0]
                myfile = await file.to_file()
                embed = discord.Embed(color=0x47B781)
                if message:
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                    await member.send(message, file=myfile)
                else:
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value='_ _')
                    await member.send(file=myfile)
                if ctx.message.attachments:
                    file = ctx.message.attachments[0]
                    spoiler = file.is_spoiler()
                    if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                        embed.set_image(url=file.url)
                    elif spoiler:
                        embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
                    else:
                        embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
                embed.set_footer(text=f'!dm {member.id}')
                await channel.send(embed=embed)
            else:
                await member.send(message)
                embed = discord.Embed(color=0x47B781)
                embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                embed.set_footer(text=f'!dm {member.id}')
                await channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"{member}'s DMs are closed.")

###############################################################################
###############################################################################

    @commands.command(aliases=['mentiondm', 'mdm', 'gdm', 'guilddm'])
    @commands.is_owner()
    async def msg(self, ctx, member: typing.Optional[discord.Member], *, message = ""):
        if ctx.message.author.id != 349373972103561218:
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep (5)
            await ctx.message.delete()
            return
        if member == None:
            await ctx.message.add_reaction('⁉')
            await asyncio.sleep(5)
            await ctx.message.delete()
            return
        channel = self.bot.get_channel(830991980850446366)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        try:
            if ctx.message.attachments:
                file = ctx.message.attachments[0]
                myfile = await file.to_file()
                embed = discord.Embed(color=0x47B781)
                if message:
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                    await member.send(message, file=myfile)
                else:
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value='_ _')
                    await member.send(file=myfile)
                if ctx.message.attachments:
                    file = ctx.message.attachments[0]
                    spoiler = file.is_spoiler()
                    if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                        embed.set_image(url=file.url)
                    elif spoiler:
                        embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
                    else:
                        embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
                embed.set_footer(text=f'!dm {member.id}')
                await channel.send(embed=embed)
            else:
                await member.send(message)
                embed = discord.Embed(color=0x47B781)
                embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                embed.set_footer(text=f'!dm {member.id}')
                await channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"{member}'s DMs are closed.")

def setup(bot):
    bot.add_cog(modmail(bot))

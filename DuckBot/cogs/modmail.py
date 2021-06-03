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
        else:
            channel = self.bot.get_channel(830991980850446366)
            if message.attachments:
                embed = discord.Embed(color= 0xFF0000)
                embed.add_field(title='⛔ ERROR ⛔', value="""Images are currently not supported in DMs.
You can use [imgur](https://imgur.com/upload) to send a images and
[pastebin](https://paste.gg/) to send long text files/messages!

⚠ `this message wasn't delivered!` ⚠
Remove the image/file and resend your message""")
                await message.channel.send(embed=embed)
                return
            else:
                embed = discord.Embed(color=0xD7342A)
                embed.add_field(name=f'<:incomingarrow:848312881070080001> **{message.author}**', value=f'{message.content}')
                embed.set_footer(text=f'.dm {message.author.id}')
                await channel.send(embed=embed)
            await message.add_reaction('📬')
            await asyncio.sleep(2.5)
            await message.remove_reaction('📬', self.bot.user)

###############################################################################
###############################################################################

    @commands.command(aliases=['md', 'pm'])
    async def dm(self, ctx, id: typing.Optional[int], *, message = ""):
        if ctx.message.author.id == 349373972103561218:
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
                    await member.send(message, file=myfile)
                    embed = discord.Embed(color=0x47B781)
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                    embed.set_footer(text=f'.dm {member.id}')
                    await channel.send(embed=embed, file=myfile)
                else:
                    await member.send(message)
                    embed = discord.Embed(color=0x47B781)
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                    embed.set_footer(text=f'.dm {member.id}')
                    await channel.send(embed=embed)
            except discord.Forbidden:
                await ctx.send(f"{member}'s DMs are closed.")
        else:
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep (5)
            await ctx.message.delete()

    @dm.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep (5)
            await ctx.message.delete()

###############################################################################
###############################################################################

    @commands.command()
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
                await member.send(message, file=myfile)
                embed = discord.Embed(color=0x47B781)
                embed.add_field(name=f'<:outgoingarrow:797567337976430632> **{member.name}#{member.discriminator}**', value=message)
                embed.set_footer(text=f'.dm {member.id}')
                await channel.send(embed=embed, file=myfile)
            else:
                await member.send(message)
                embed = discord.Embed(color=0x47B781)
                embed.add_field(name=f'<:outgoingarrow:797567337976430632> **{member.name}#{member.discriminator}**', value=message)
                embed.set_footer(text=f'.dm {member.id}')
                await channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"{member}'s DMs are closed.")

    @dm.error
    async def dm_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep (5)
            await ctx.message.delete()




def setup(bot):
    bot.add_cog(modmail(bot))

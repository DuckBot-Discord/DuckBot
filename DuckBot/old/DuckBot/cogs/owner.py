import typing, discord, asyncio, json
from discord.ext import commands

class owner_only_commands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.toggle = 0
        # Don't question the weird numbers. Just there because they're hard to guess.

    @commands.command(aliases = ['setstatus', 'ss', 'activity'])
    @commands.is_owner()
    async def status(self, ctx, thetype: typing.Optional[str] = None,* , argument: typing.Optional[str] = None):
        botprefix = 'db.'
        type = thetype.lower()

        if type == None:
            embed = discord.Embed(title= "`ERROR` NO STATUS GIVEN!", description="Here is a list of available types:", color = ctx.me.color)
            embed.add_field(name=(botprefix + 'status Playing <status>'), value='Sets the status to Playing.', inline=False)
            embed.add_field(name=(botprefix + 'status Listening <status>'), value='Sets the status to Listening.', inline=False)
            embed.add_field(name=(botprefix + 'status Watching <status>'), value='Sets the status to Watching.', inline=False)
            await ctx.send(embed=embed, delete_after=45)
            await asyncio.sleep(45)
            try: await ctx.message.delete()
            except discord.Forbidden: pass

        if type == "playing":
            if argument !=  None:
                # Setting `Playing ` status
                await self.bot.change_presence(activity=discord.Game(name=f'{argument}'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity changed to `Playing {argument}` ", delete_after=10)
                await asyncio.sleep(10)
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    pass

        if type == "listening":
            if argument !=  None:
                # Setting `Listening ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{argument}'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity changed to `Listening to {argument}` ", delete_after=10)
                await asyncio.sleep(10)
                try: await ctx.message.delete()
                except discord.Forbidden: pass

        if type == "watching":
            if argument !=  None:
                #Setting `Watching ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{argument}'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity changed to `Watching {argument}` ", delete_after=10)
                await asyncio.sleep(10)
                try: await ctx.message.delete()
                except discord.Forbidden: pass

        if type == "competing":
            if argument !=  None:
                #Setting `other ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=f'{argument}'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity changed to `Competing in {argument}` ", delete_after=10)
                await asyncio.sleep(10)
                try: await ctx.message.delete()
                except discord.Forbidden: pass

        if type == "clear":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name='cleared'))
            await ctx.message.add_reaction('✅')
            await ctx.send(f"Activity cleared ", delete_after=10)
            await asyncio.sleep(10)
            try: await ctx.message.delete()
            except discord.Forbidden: pass

        if type != "watching" and type != "listening" and type != "playing" and type != "competing" and type != "clear" and type != None:
            embed = discord.Embed(title= "`ERROR` INVALID TYPE!", description="Here is a list of available types:", color = ctx.me.color)
            embed.add_field(name=(botprefix + 'status Playing <status>'), value='Sets the status to Playing.', inline=False)
            embed.add_field(name=(botprefix + 'status Listening <status>'), value='Sets the status to `Listening to`.', inline=False)
            embed.add_field(name=(botprefix + 'status Watching <status>'), value='Sets the status to `Watching`.', inline=False)
            embed.add_field(name=(botprefix + 'status Competing <status>'), value='Sets the status to `Competing in`.', inline=False)
            await ctx.send(embed=embed, delete_after=45)
            await asyncio.sleep(45)
            try: await ctx.message.delete()
            except discord.Forbidden: pass



    @commands.command(aliases = ['stop','sd'])
    @commands.is_owner()
    async def shutdown(self, ctx):
        guild = self.bot.get_guild(787743716793516062)
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            a=1
        await ctx.send("🛑 **__Stopping the bot__**")
        await ctx.bot.logout()

    @commands.command()
    @commands.is_owner()
    async def todo(self, ctx, *, message = None):
        channel = self.bot.get_channel(830992446434312192)
        if message == None:
            await ctx.message.add_reaction('⚠')
            return
        if ctx.message.channel == channel:
            await ctx.message.delete()
        embed = discord.Embed(description=message, color=0x47B781)
        await channel.send(embed=embed)
        await ctx.message.add_reaction('✅')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            if after.channel.guild.id == 841298004929806336:
                textchannel = self.bot.get_channel(841298004929806340)
                await textchannel.send(f'<:joined:849392863557189633> {member.name} **joined** __{after.channel.name}__!')
        if before.channel is not None and after.channel is not None:
            if before.channel.guild.id == 841298004929806336 and before.channel.id != after.channel.id:
                textchannel = self.bot.get_channel(841298004929806340)
                await textchannel.send(f'<:moved:848312880666640394> {member.name} **has been moved to** __{after.channel.name}__!')
        if before.channel is not None and after.channel is None:
            if before.channel.guild.id == 841298004929806336:
                textchannel = self.bot.get_channel(841298004929806340)
                await textchannel.send(f'<:left:849392885785821224> {member.name} **left** __{before.channel.name}__!')

def setup(bot):
    bot.add_cog(owner_only_commands(bot))

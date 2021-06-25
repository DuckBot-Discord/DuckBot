import os, discord, asyncio, traceback, json, typing
from dotenv import load_dotenv
from discord.ext import commands
from helpers.helper import failed

class management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases = ['setstatus', 'ss', 'activity'])
    @commands.is_owner()
    async def status(self, ctx, type: typing.Optional[str] = None,* , argument: typing.Optional[str] = None):
        botprefix = 'db.'

        if type == None:
            embed = discord.Embed(title= "`ERROR` NO STATUS GIVEN!", description="Here is a list of available types:", color = ctx.me.color)
            embed.add_field(name=(botprefix + 'status Playing <status>'), value='Sets the status to Playing.', inline=False)
            embed.add_field(name=(botprefix + 'status Listening <status>'), value='Sets the status to Listening.', inline=False)
            embed.add_field(name=(botprefix + 'status Watching <status>'), value='Sets the status to Watching.', inline=False)
            await ctx.send(embed=embed, delete_after=45)
            await asyncio.sleep(45)
            try: await ctx.message.delete()
            except discord.Forbidden: pass
            return

        type = type.lower()

        if type == "playing":
            if argument !=  None:
                # Setting `Playing ` status
                await self.bot.change_presence(activity=discord.Game(name=f'{argument}'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity changed to `Playing {argument}` ")

        if type == "listening":
            if argument !=  None:
                # Setting `Listening ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{argument}'))
                await ctx.send(f"Activity changed to `Listening to {argument}` ")

        if type == "watching":
            if argument !=  None:
                #Setting `Watching ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{argument}'))
                await ctx.send(f"Activity changed to `Watching {argument}` ", delete_after=10)
                await asyncio.sleep(10)
                try: await ctx.message.delete()
                except discord.Forbidden: pass

        if type == "competing":
            if argument !=  None:
                #Setting `other ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=f'{argument}'))
                await ctx.send(f"Activity changed to `Competing in {argument}` ")

        if type == "clear":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name='cleared'))
            await ctx.send(f"Activity cleared")

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

    @commands.command(aliases = ['mm','maintenancemode'])
    @commands.is_owner()
    async def maintenance(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.bot.maintenance = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.bot.maintenance = False
        else:
            if self.bot.maintenance == False:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.bot.maintenance = True
            elif self.bot.maintenance == True:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.bot.maintenance = False

    @commands.command(aliases = ['np','invisprefix', 'sp'])
    @commands.is_owner()
    async def noprefix(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.bot.noprefix = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.bot.noprefix = False
        else:
            if self.bot.noprefix == False:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.bot.noprefix = True
            elif self.bot.noprefix == True:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.bot.noprefix = False

#----------------------------------------------------------------------------#
#------------------------ EXTENSION MANAGEMENT ------------------------------#
#----------------------------------------------------------------------------#

    @commands.command(aliases=['le', 'lc', 'loadcog'])
    @commands.is_owner()
    async def load(self, ctx, extension = ""):
        embed = discord.Embed(color=ctx.me.color, description = f"⬆ {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.load_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionAlreadyLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension already loaded")
            await message.edit(embed=embed)


        except discord.ext.commands.NoEntryPointError:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ No setup function")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error\n```{traceback_string}```")
            try: await message.edit(embed=embed)
            except:
                embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error ```\n error too long, check the console\n```")
                await message.edit()
            raise e

    @commands.command(aliases=['unl', 'ue', 'uc'])
    @commands.is_owner()
    async def unload(self, ctx, extension = ""):
        embed = discord.Embed(color=ctx.me.color, description = f"⬇ {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.unload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not loaded")
            await message.edit(embed=embed)

    @commands.command(aliases=['rel', 're', 'rc'])
    @commands.is_owner()
    async def reload(self, ctx, extension = ""):
        embed = discord.Embed(color=ctx.me.color, description = f"🔃 {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.reload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"✅ {extension}")
            await message.edit(embed=embed)
        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not loaded")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.NoEntryPointError:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ No setup function")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error\n```{traceback_string}```")
            try: await message.edit(embed=embed)
            except:
                embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error ```\n error too long, check the console\n```")
                await message.edit()
            raise e

    @commands.command(aliases=['reloadall', 'rall', 'rae', 'rac'])
    @commands.is_owner()
    async def relall(self, ctx, arg = None):
        list = ""
        desc = ""
        err = False
        rerel = []
        if arg == 'silent' or arg == 's': silent = True
        else: silent = False
        if arg == 'channel' or arg == 'channel': channel = True
        else: channel = False

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                list = f"{list} \n🔃 {filename[:-3]}"

        embed = discord.Embed(color=ctx.me.color, description = list)
        message = await ctx.send(embed=embed)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                    desc = f"{desc} \n✅ {filename[:-3]}"
                except:
                    rerel.append(filename)

        for filename in rerel:
            try:
                self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                desc = f"{desc} \n✅ {filename[:-3]}"

            except discord.ext.commands.ExtensionNotLoaded:
                desc = f"{desc} \n❌ {filename[:-3]} - Not loaded"
                err = True
            except discord.ext.commands.ExtensionNotFound:
                desc = f"{desc} \n❌ {filename[:-3]} - Not found"
                err = True
            except discord.ext.commands.NoEntryPointError:
                desc = f"{desc} \n❌ {filename[:-3]} - No setup func"
                err = True
            except discord.ext.commands.ExtensionFailed as e:
                traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
                desc = f"{desc} \n❌ {filename[:-3]} - Execution error"
                embederr = discord.Embed(color=ctx.me.color, description = f"\n❌ {filename[:-3]} Execution error - Traceback\n```\n{traceback_string}\n```")
                if silent == False:
                    if channel == False: await ctx.author.send(embed=embederr)
                    else: await ctx.send(embed=embederr)
                err = True

        await asyncio.sleep(1)
        if err == True:
            if silent == False:
                if channel == False: desc = f"{desc} \n\n📬 {ctx.author.mention}, I sent you all the tracebacks."
                else: desc = f"{desc} \n\n📬 Sent all tracebacks to {ctx.channel.mention}."
            if silent == True: desc = f"{desc} \n\n📭 silent, no tracebacks sent."
            embed = discord.Embed(color=ctx.me.color, description = desc, title = 'Reloaded some extensions')
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(title = 'Reloaded all extensions', color=ctx.me.color, description = desc)
            await message.edit(embed=embed)

    @commands.command(aliases = ['stop','sd'])
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.send("🛑 **__Stopping the bot__**")
        await ctx.bot.logout()

def setup(bot):
    bot.add_cog(management(bot))

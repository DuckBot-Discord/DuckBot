import os, discord, asyncio, traceback, json, typing
from dotenv import load_dotenv
from discord.ext import commands, menus
from jishaku.models import copy_context_with
import contextlib


class management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases = ['setstatus', 'ss', 'activity'])
    @commands.has_permissions(administrator=True)
    async def status(self, ctx, type: typing.Optional[str],* , argument: typing.Optional[str]):
        if ctx.author.guild_permissions.administrator == True:
            botprefix = ctx.prefix

            if type == None:
                embed = discord.Embed(title= "`ERROR` NO STATUS GIVEN!", description="Here is a list of available types:", color = ctx.me.color)
                embed.add_field(name=(botprefix + 'status Playing <status>'), value='Sets the status to Playing.', inline=False)
                embed.add_field(name=(botprefix + 'status Listening <status>'), value='Sets the status to `Listening to`.', inline=False)
                embed.add_field(name=(botprefix + 'status Watching <status>'), value='Sets the status to `Watching`.', inline=False)
                embed.add_field(name=(botprefix + 'status Competing <status>'), value='Sets the status to `Competing in`.', inline=False)
                await ctx.send(embed=embed, delete_after=45)
                await asyncio.sleep(45)
                await ctx.message.delete()
            else:
                type = type.lower()
            if type == "playing":
                if argument !=  None:
                    # Setting `Playing ` status
                    await self.bot.change_presence(activity=discord.Game(name=f'{argument}'))
                    await ctx.message.add_reaction('✅')
                    await ctx.send(f"Activity changed to `Playing {argument}` ", delete_after=10)
                    await asyncio.sleep(10)
                    await ctx.message.delete()

            if type == "listening":
                if argument != None:
                    # Setting `Listening ` status
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{argument}'))
                    await ctx.message.add_reaction('✅')
                    await ctx.send(f"Activity changed to `Listening to {argument}` ", delete_after=10)
                    await asyncio.sleep(10)
                    await ctx.message.delete()

            if type == "watching":
                if argument !=  None:
                    #Setting `Watching ` status
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{argument}'))
                    await ctx.message.add_reaction('✅')
                    await ctx.send(f"Activity changed to `Watching {argument}` ", delete_after=10)
                    await asyncio.sleep(10)
                    await ctx.message.delete()

            if type == "competing":
                if argument !=  None:
                    #Setting `other ` status
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=f'{argument}'))
                    await ctx.message.add_reaction('✅')
                    await ctx.send(f"Activity changed to `Competing in {argument}` ", delete_after=10)
                    await asyncio.sleep(10)
                    await ctx.message.delete()

            if type == "clear":
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name='cleared'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity cleared ", delete_after=10)
                await asyncio.sleep(10)
                await ctx.message.delete()

            if type != "watching" and type != "listening" and type != "playing" and type != "competing" and type != "clear" and type != "4afc07a4055edc68da62f18f7ecdd103":
                embed = discord.Embed(title= "`ERROR` INVALID TYPE!", description="Here is a list of available types:", color = ctx.me.color)
                embed.add_field(name=(botprefix + 'status Playing <status>'), value='Sets the status to Playing.', inline=False)
                embed.add_field(name=(botprefix + 'status Listening <status>'), value='Sets the status to `Listening to`.', inline=False)
                embed.add_field(name=(botprefix + 'status Watching <status>'), value='Sets the status to `Watching`.', inline=False)
                embed.add_field(name=(botprefix + 'status Competing <status>'), value='Sets the status to `Competing in`.', inline=False)
                await ctx.send(embed=embed, delete_after=45)
                await asyncio.sleep(45)
                await ctx.message.delete()
        else:
            await ctx.message.add_reaction('🚫')
            await asyncio.sleep(5)
            await ctx.message.delete()


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


    @commands.command()
    @commands.is_owner()
    async def sudo(self, ctx: commands.Context, target: discord.User, *, command_string: str):
        """
        Run a command as someone else.

        This will try to resolve to a Member, but will use a User if it can't find one.

        """

        if ctx.guild:
            # Try to upgrade to a Member instance
            # This used to be done by a Union converter, but doing it like this makes
            #  the command more compatible with chaining, e.g. `jsk in .. jsk su ..`
            target_member = None

            with contextlib.suppress(discord.HTTPException):
                target_member = ctx.guild.get_member(target.id) or await ctx.guild.fetch_member(target.id)

            target = target_member or target

        alt_ctx = await copy_context_with(ctx, author=target, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            if alt_ctx.invoked_with is None:
                return await ctx.send('This bot has been hard-configured to ignore this user.')
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.invoke(alt_ctx)

def setup(bot):
    bot.add_cog(management(bot))

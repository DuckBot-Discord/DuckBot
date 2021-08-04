import os, discord, asyncio, traceback, json, typing
from dotenv import load_dotenv
from discord.ext import commands, menus
from jishaku.models import copy_context_with
import contextlib

class management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

#----------------------------------------------------------------------------#
#------------------------ EXTENSION MANAGEMENT ------------------------------#
#----------------------------------------------------------------------------#

    @commands.command(aliases=['le', 'lc', 'loadcog'])
    @commands.is_owner()
    async def load(self, ctx, extension):
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
    async def unload(self, ctx, extension):
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
    async def reload(self, ctx, extension):
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
        if arg == 'channel' or arg == 'c': channel = True
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

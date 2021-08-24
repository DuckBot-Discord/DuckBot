import asyncio
import contextlib
import datetime
import io
import os
import textwrap
import traceback
import typing

import discord
from discord.ext import commands, menus

from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.shell import ShellReader
from jishaku.models import copy_context_with


def setup(bot):
    bot.add_cog(Management(bot))


class Confirm(menus.Menu):

    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


class Management(commands.Cog, name='Bot Management'):
    """🤖Management stuff. Ignore this"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    # Git but to the correct directory
    @Feature.Command(parent="jsk", name="git")
    async def jsk_git(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh git'. Invokes the system shell.
        """
        return await ctx.invoke("jsk shell",
                                argument=Codeblock(argument.language, "cd ~/.git/DiscordBots\ngit " + argument.content))

    @commands.command()
    @commands.is_owner()
    async def update(self, ctx):
        await ctx.invoke("jsk git", argument="pull")
        await asyncio.sleep(1)
        await ctx.invoke("rall")

    @commands.group(aliases=['setstatus', 'ss', 'activity'], invoke_without_subcommand=True)
    @commands.is_owner()
    async def status(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @status.command(name='playing')
    async def status_playing(self, ctx: commands.Context, text):
        await self.bot.change_presence(activity=discord.Game(name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Playing {text}` ")

    @status.command(name='listening')
    async def status_listening(self, ctx: commands.Context, text):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Listening to {text}` ")

    @status.command(name='watching')
    async def status_watching(self, ctx: commands.Context, text):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Watching {text}` ")

    @status.command(name='competing')
    async def status_competing(self, ctx: commands.Context, text):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Watching {text}` ")

    @commands.command(help="Adds something to de to-do list", usage="<text>")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def todo(self, ctx, *, message=None):
        channel = self.bot.get_channel(830992446434312192)
        if ctx.message.reference:
            message = ctx.message.reference.resolved.content
        if ctx.message.channel == channel:
            await ctx.message.delete()
        embed = discord.Embed(description=message, color=0x47B781)
        await channel.send(embed=embed)
        await ctx.message.add_reaction('✅')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            if after.channel.guild.id == 841298004929806336:
                text_channel = self.bot.get_channel(841298004929806340)
                await text_channel.send(
                    f'<:joined:849392863557189633> {member.name} **joined** __{after.channel.name}__!')
        if before.channel is not None and after.channel is not None:
            if before.channel.guild.id == 841298004929806336 and before.channel.id != after.channel.id:
                text_channel = self.bot.get_channel(841298004929806340)
                await text_channel.send(
                    f'<:moved:848312880666640394> {member.name} **has been moved to** __{after.channel.name}__!')
        if before.channel is not None and after.channel is None:
            if before.channel.guild.id == 841298004929806336:
                text_channel = self.bot.get_channel(841298004929806340)
                await text_channel.send(f'<:left:849392885785821224> {member.name} **left** __{before.channel.name}__!')

    @commands.command(aliases=['mm'], help="puts the bot under maintenance", usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def maintenance(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.bot.maintenance = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.bot.maintenance = False
        else:
            if not self.bot.maintenance:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.bot.maintenance = True
            elif self.bot.maintenance:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.bot.maintenance = False

    @commands.command(aliases=['sp'], help="toggles no-prefix mode on or off",
                      usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def silentprefix(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.bot.noprefix = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.bot.noprefix = False
        else:
            if not self.bot.noprefix:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.bot.noprefix = True
            elif self.bot.noprefix:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.bot.noprefix = False

    # ----------------------------------------------------------------------------#
    # ------------------------ EXTENSION MANAGEMENT ------------------------------#
    # ----------------------------------------------------------------------------#

    @commands.command(help="Loads an extension", aliases=['le', 'lc', 'loadcog'], usage="<extension>")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def load(self, ctx, extension=""):
        embed = discord.Embed(color=ctx.me.color, description=f"⬆ {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.load_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionAlreadyLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension already loaded")
            await message.edit(embed=embed)

        except discord.ext.commands.NoEntryPointError:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ No setup function")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Execution error\n```{traceback_string}```")
            try:
                await message.edit(embed=embed)
            except:
                embed = discord.Embed(color=ctx.me.color,
                                      description=f"❌ Execution error ```\n error too long, check the console\n```")
                await message.edit(embed=embed)
            raise e

    @commands.command(help="Unloads an extension", aliases=['unl', 'ue', 'uc'], usage="<extension>")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def unload(self, ctx, extension=""):
        embed = discord.Embed(color=ctx.me.color, description=f"⬇ {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.unload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not loaded")
            await message.edit(embed=embed)

    @commands.command(help="Reloads an extension", aliases=['rel', 're', 'rc'])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reload(self, ctx, extension=""):
        embed = discord.Embed(color=ctx.me.color, description=f"🔃 {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.reload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"✅ {extension}")
            await message.edit(embed=embed)
        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not loaded")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.NoEntryPointError:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ No setup function")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Execution error\n```{traceback_string}```")
            try:
                await message.edit(embed=embed)
            except:
                embed = discord.Embed(color=ctx.me.color,
                                      description=f"❌ Execution error ```\n error too long, check the console\n```")
                await message.edit(embed=embed)
            raise e

    @commands.command(help="Reloads all extensions", aliases=['relall', 'rall'], usage="[silent|channel]")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reloadall(self, ctx, argument: typing.Optional[str]):
        self.bot.last_rall = datetime.datetime.utcnow()
        cogs_list = ""
        to_send = ""
        err = False
        first_reload_failed_extensions = []
        if argument == 'silent' or argument == 's':
            silent = True
        else:
            silent = False
        if argument == 'channel' or argument == 'c':
            channel = True
        else:
            channel = False

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cogs_list = f"{cogs_list} \n🔃 {filename[:-3]}"

        embed = discord.Embed(color=ctx.me.color, description=cogs_list)
        message = await ctx.send(embed=embed)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                    to_send = f"{to_send} \n✅ {filename[:-3]}"
                except:
                    first_reload_failed_extensions.append(filename)

        for filename in first_reload_failed_extensions:
            try:
                self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                to_send = f"{to_send} \n✅ {filename[:-3]}"

            except discord.ext.commands.ExtensionNotLoaded:
                to_send = f"{to_send} \n❌ {filename[:-3]} - Not loaded"
            except discord.ext.commands.ExtensionNotFound:
                to_send = f"{to_send} \n❌ {filename[:-3]} - Not found"
            except discord.ext.commands.NoEntryPointError:
                to_send = f"{to_send} \n❌ {filename[:-3]} - No setup func"
            except discord.ext.commands.ExtensionFailed as e:
                traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
                to_send = f"{to_send} \n❌ {filename[:-3]} - Execution error"
                embed_error = discord.Embed(color=ctx.me.color,
                                            description=f"\n❌ {filename[:-3]} Execution error - Traceback\n```\n{traceback_string}\n```")
                if not silent:
                    if not channel:
                        await ctx.author.send(embed=embed_error)
                    else:
                        await ctx.send(embed=embed_error)
                err = True

        await asyncio.sleep(0.4)
        if err:
            if not silent:
                if not channel:
                    to_send = f"{to_send} \n\n📬 {ctx.author.mention}, I sent you all the tracebacks."
                else:
                    to_send = f"{to_send} \n\n📬 Sent all tracebacks here."
            if silent:
                to_send = f"{to_send} \n\n📭 silent, no tracebacks sent."
            embed = discord.Embed(color=ctx.me.color, description=to_send, title='Reloaded some extensions')
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(title='Reloaded all extensions', color=ctx.me.color, description=to_send)
            await message.edit(embed=embed)

    ###############################################################################
    ###############################################################################

    @commands.command(help="Dms a user from any guild", aliases=['md', 'pm', 'id-dm'], usage="[ID]")
    @commands.is_owner()
    async def dm(self, ctx, member: discord.User, *, message=""):

        if member.bot:
            await ctx.message.add_reaction('🤖')
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
                    embed.add_field(
                        name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**',
                        value=message)
                    await member.send(message, file=myfile)
                else:
                    embed.add_field(
                        name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**',
                        value='_ _')
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
                embed.set_footer(text=f'.dm {member.id}')
                await channel.send(embed=embed)
            else:
                await member.send(message)
                embed = discord.Embed(color=0x47B781)
                embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**',
                                value=message)
                embed.set_footer(text=f'.dm {member.id}')
                await channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"{member}'s DMs are closed.")

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

            with contextlib.suppress(discord.HTTPException):
                target_member = ctx.guild.get_member(target.id) or await ctx.guild.fetch_member(target.id)

            target = target_member or target

        alt_ctx = await copy_context_with(ctx, author=target, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            if alt_ctx.invoked_with is None:
                return await ctx.send('This bot has been hard-configured to ignore this user.')
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.invoke(alt_ctx)

    @commands.command(pass_context=True, hidden=True, name='eval')
    @commands.is_owner()
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

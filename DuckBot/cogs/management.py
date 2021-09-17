import asyncio
import contextlib
import datetime
import io
import os
import textwrap
import traceback
import typing
from DuckBot.main import DuckBot

import discord
from discord.ext import commands

from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.features.baseclass import Feature
from jishaku.models import copy_context_with


def setup(bot):
    bot.add_cog(Management(bot))


async def get_webhook(channel):
    webhook_list = await channel.webhooks()
    if webhook_list:
        for hook in webhook_list:
            if hook.token:
                return hook
            else:
                continue
    hook = await channel.create_webhook(name="DuckBot ModMail")
    return hook


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


class Management(commands.Cog, name='Bot Management'):
    """
    🤖 Commands meant for the bot developers to manage the bots functionalities. Not meant for general use.
    """

    def __init__(self, bot):
        self.research_channels = (881215900315951184, 881246869873917962, 881246946776449045, 881247025688084521)
        self.bot: DuckBot = bot
        self._last_result = None

    # Git but to the correct directory
    @Feature.Command(parent="jsk", name="git")
    async def jsk_git(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh git'. Invokes the system shell.
        """
        return await ctx.invoke("jsk shell",
                                argument=Codeblock(argument.language, "cd ~/.git/DiscordBots\ngit " + argument.content))

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
            activity=discord.Activity(type=discord.ActivityType.competing, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Competing in {text}`")

    @commands.command(help="Adds something to de to-do list")
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

    @commands.command(aliases=['mm'], help="puts the bot under maintenance", usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def maintenance(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction(ctx.toggle(True))
            self.bot.maintenance = True
        elif state == 'off':
            await ctx.message.add_reaction(ctx.toggle(False))
            self.bot.maintenance = False
        else:
            if not self.bot.maintenance:
                await ctx.message.add_reaction(ctx.toggle(True))
                self.bot.maintenance = True
            elif self.bot.maintenance:
                await ctx.message.add_reaction(ctx.toggle(False))
                self.bot.maintenance = False

    @commands.command(aliases=['sp'], help="toggles no-prefix mode on or off",
                      usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def silentprefix(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction(ctx.toggle(True))
            self.bot.noprefix = True
        elif state == 'off':
            await ctx.message.add_reaction(ctx.toggle(False))
            self.bot.noprefix = False
        else:
            if not self.bot.noprefix:
                await ctx.message.add_reaction(ctx.toggle(True))
                self.bot.noprefix = True
            elif self.bot.noprefix:
                await ctx.message.add_reaction(ctx.toggle(False))
                self.bot.noprefix = False

    # ----------------------------------------------------------------------------#
    # ------------------------ EXTENSION MANAGEMENT ------------------------------#
    # ----------------------------------------------------------------------------#

    @commands.command(help="Loads an extension", aliases=['le', 'lc', 'loadcog'])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def load(self, ctx, extension):
        embed = discord.Embed(color=ctx.me.color, description=f"⬆ {extension}")
        message = await ctx.send(embed=embed, footer=False)
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
            except (discord.HTTPException, discord.Forbidden):
                embed = discord.Embed(color=ctx.me.color,
                                      description=f"❌ Execution error ```\n error too long\n```")
                await message.edit(embed=embed,
                                   file=io.StringIO(traceback_string))
            raise e

    @commands.command(help="Unloads an extension", aliases=['unl', 'ue', 'uc'])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def unload(self, ctx, extension):
        embed = discord.Embed(color=ctx.me.color, description=f"⬇ {extension}")
        message = await ctx.send(embed=embed, footer=False)
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
        message = await ctx.send(embed=embed, footer=False)
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
            except (discord.Forbidden, discord.HTTPException):
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

        embed = discord.Embed(description=cogs_list)
        message = await ctx.send(embed=embed, footer=False)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                    to_send = f"{to_send} \n✅ {filename[:-3]}"
                except Exception:
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
                embed_error = f"\n❌ {filename[:-3]} Execution error - Traceback" \
                              f"\n```py\n{traceback_string}\n```"
                if not silent:
                    target = ctx if channel else ctx.author
                    if len(embed_error) > 2000:
                        await target.send(file=io.StringIO(embed_error))
                    else:
                        await target.send(embed_error)

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

    @commands.command(aliases=['pm', 'message', 'direct'])
    @commands.is_owner()
    @commands.guild_only()
    async def dm(self, ctx: commands.Context, member: discord.User, *, message=None):
        if ctx.channel.category_id == 878123261525901342:
            return
        category = self.bot.get_guild(774561547930304536).get_channel(878123261525901342)
        channel = discord.utils.get(category.channels, topic=str(member.id))
        if not channel:
            channel = await category.create_text_channel(
                name=f"{member}",
                topic=str(member.id),
                position=0,
                reason="DuckBot ModMail"
            )

        wh = await get_webhook(channel)

        files = []
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.size > 8388600:
                    await ctx.send('Sent message without attachment! File size greater than 8 MB.')
                    continue
                files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await member.send(content=message, files=files)
        except:
            return await ctx.message.add_reaction('⚠')

        try:
            await wh.send(content=message, username=ctx.author.name, avatar_url=ctx.author.display_avatar.url,
                          files=files)
        except:
            await ctx.message.add_reaction('🤖')
            await ctx.message.add_reaction('‼')
        await ctx.message.add_reaction('💌')

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
        try:
            await ctx.message.add_reaction('▶')
        except (discord.Forbidden, discord.HTTPException):
            pass
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
            try:
                await ctx.message.add_reaction('⚠')
            except (discord.Forbidden, discord.HTTPException):
                pass
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('⚠')
            except (discord.Forbidden, discord.HTTPException):
                pass
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except (discord.Forbidden, discord.HTTPException):
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.group(invoke_without_command=True, aliases=['bl'])
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context) -> discord.Message:
        """ Blacklist management commands """
        if ctx.invoked_subcommand is None:
            return

    @blacklist.command(name="add", aliases=['a'])
    @commands.is_owner()
    async def blacklist_add(self, ctx: commands.Context,
                            user: discord.User) -> discord.Message:
        """ adds a user to the bot blacklist """

        await self.bot.db.execute(
            "INSERT INTO blacklist(user_id, is_blacklisted) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET is_blacklisted = $2",
            user.id, True)

        self.bot.blacklist[user.id] = True

        return await ctx.send(f"Added **{user}** to the blacklist")

    @blacklist.command(name="remove", aliases=['r', 'rm'])
    @commands.is_owner()
    async def blacklist_remove(self, ctx: commands.Context,
                               user: discord.User) -> discord.Message:
        """
        removes a user from the bot blacklist
        """

        await self.bot.db.execute(
            "DELETE FROM blacklist where user_id = $1",
            user.id)

        self.bot.blacklist[user.id] = False

        return await ctx.send(f"Removed **{user}** from the blacklist")

    @blacklist.command(name='check', aliases=['c'])
    @commands.is_owner()
    async def blacklist_check(self, ctx: commands.Context, user: discord.User):
        """
        Checks a user's blacklist status
        """
        try:
            status = self.bot.blacklist[user.id]
        except KeyError:
            status = False
        return await ctx.send(f"**{user}** {'is' if status is True else 'is not'} blacklisted")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if channel.category.id in self.research_channels:
            send_to = self.bot.get_channel(804035776722894890)
            invite = await channel.create_invite(max_age=3600 * 24)
            message = await send_to.send(invite.url)
            await self.bot.db.execute('INSERT INTO voice_channels(channel_id, message_id) '
                                      'VALUES ($1, $2)', channel.id, message.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if channel.category.id in self.research_channels:
            delete_from = self.bot.get_channel(804035776722894890)
            msg_id = await self.bot.db.fetchval('SELECT message_id FROM voice_channels WHERE '
                                                'channel_id = $1', channel.id)
            message = delete_from.get_partial_message(msg_id)
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

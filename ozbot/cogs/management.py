import datetime
import io
import itertools

import asyncio
import discord
import jishaku.modules
import traceback
import typing
from discord.ext import commands
from jishaku.paginators import WrappedPaginator


class Management(commands.Cog):
    """👩‍⚖️ Commands to manage the bot itself."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=['setstatus', 'ss', 'activity'], usage='<type> <status>')
    async def status(self, ctx):
        """ Base command for setting the bot's status """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @status.command(name='playing')
    async def status_playing(self, ctx, text):
        """ Sets the bot's status to playing """
        await self.bot.change_presence(activity=discord.Game(name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Playing {text}` ")

    @status.command(name='listening')
    async def status_listening(self, ctx, text):
        """ Sets the bot's status to listening """
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Listening to {text}` ")

    @status.command(name='watching')
    async def status_watching(self, ctx, text):
        """ Sets the bot's status to watching """
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Watching {text}` ")

    @status.command(name='competing')
    async def status_competing(self, ctx, text):
        """ Sets the bot's status to competing """
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.competing, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Competing in {text}`")

    @commands.command(help="Reloads all extensions", aliases=['relall', 'rall', 'reloadall', 'load'])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reload(self, ctx, *extensions: jishaku.modules.ExtensionConverter):
        self.bot.last_rall = datetime.datetime.utcnow()
        pages = WrappedPaginator(prefix='', suffix='')
        first_reload_failed_extensions = []

        extensions = extensions or [await jishaku.modules.ExtensionConverter.convert(self, ctx, '~')]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )
            # noinspection PyBroadException
            try:
                method(extension)
                pages.add_line(f"{icon} `{extension}`")
            except Exception:
                first_reload_failed_extensions.append(extension)

        error_keys = {
            discord.ext.commands.ExtensionNotFound: 'Not found',
            discord.ext.commands.NoEntryPointError: 'No setup function',
            discord.ext.commands.ExtensionNotLoaded: 'Not loaded',
            discord.ext.commands.ExtensionAlreadyLoaded: 'Already loaded',
        }

        for extension in first_reload_failed_extensions:
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )
            try:
                method(extension)
                pages.add_line(f"{icon} `{extension}`")

            except tuple(error_keys.keys()) as exc:
                pages.add_line(f"{icon}❌ `{extension}` - {error_keys[type(exc)]}")

            except discord.ext.commands.ExtensionFailed as e:
                traceback_string = f"```py" \
                                   f"\n{''.join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))}" \
                                   f"\n```"
                pages.add_line(f"{icon}❌ `{extension}` - Execution error")
                to_dm = f"❌ {extension} - Execution error - Traceback:"

                if (len(to_dm) + len(traceback_string) + 5) > 2000:
                    await ctx.author.send(file=io.StringIO(traceback_string))
                else:
                    await ctx.author.send(f"{to_dm}\n{traceback_string}")

        for page in pages.pages:
            await ctx.send(page)


def setup(bot):
    bot.add_cog(management(bot))

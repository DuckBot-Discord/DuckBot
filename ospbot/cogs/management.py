import asyncio
import contextlib
import discord
import os
import traceback
import typing

from discord.ext import commands
from jishaku.models import copy_context_with

from files import constants


class management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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

    @commands.command(aliases=['mm'], help="puts the bot under maintenance", usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def maintenance(self, ctx, *, reason: str = None):
        if reason:
            await ctx.message.add_reaction(ctx.toggle(True))
            self.bot.maintenance = reason
        else:
            await ctx.message.add_reaction(ctx.toggle(False))
            self.bot.maintenance = None

    @commands.command(aliases = ['mm','maintenancemode'])
    @commands.is_owner()
    async def maintenance(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction(constants.TOGGLES[True])
            self.bot.maintenance = True
        elif state == 'off':
            await ctx.message.add_reaction(constants.TOGGLES[False])
            self.bot.maintenance = False
        else:
            if not self.bot.maintenance:
                await ctx.message.add_reaction(constants.TOGGLES[True])
                self.bot.maintenance = True
            elif self.bot.maintenance == True:
                await ctx.message.add_reaction(constants.TOGGLES[False])
                self.bot.maintenance = False

    @commands.command(aliases = ['np','invisprefix', 'sp'])
    @commands.is_owner()
    async def noprefix(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction(constants.TOGGLES[True])
            self.bot.noprefix = True
        elif state == 'off':
            await ctx.message.add_reaction(constants.TOGGLES[False])
            self.bot.noprefix = False
        else:
            if self.bot.noprefix == False:
                await ctx.message.add_reaction(constants.TOGGLES[True])
                self.bot.noprefix = True
            elif self.bot.noprefix == True:
                await ctx.message.add_reaction(constants.TOGGLES[False])
                self.bot.noprefix = False

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

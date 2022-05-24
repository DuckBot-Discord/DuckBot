import contextlib

import asyncpg
import discord
from discord.ext import commands

from ._base import ConfigBase
from ..logs import LoggingBackend
from ...helpers.context import CustomContext


class ModLogs(ConfigBase):
    @commands.group(name='modlogs', aliases=['modlog'], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def modlogs(self, ctx: CustomContext, channel: discord.TextChannel = None):
        """Enables mod-logs"""
        if channel:
            await self.bot.db.execute(
                "INSERT INTO prefixes (guild_id, modlog) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET modlog = $2",
                ctx.guild.id,
                channel.id,
            )
            await ctx.send(f'✅ | **ModLogs** will now be delivered in #{channel.mention}')
        else:
            modlog = await self.bot.db.fetchval("SELECT modlog FROM prefixes WHERE guild_id = $1", ctx.guild.id)
            if modlog:
                await ctx.send(f"ℹ | **ModLogs** are currently enabled in #{self.bot.get_channel(modlog) or modlog}")
            else:
                await ctx.send("ℹ | **ModLogs** are disabled")

    @modlogs.command(name='disable')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def modlogs_disable(self, ctx: CustomContext):
        modlog = await self.bot.db.fetchval("SELECT modlog FROM prefixes WHERE guild_id = $1", ctx.guild.id)
        if not modlog:
            await ctx.send('ℹ | **ModLogs** are already disabled')
        else:
            await self.bot.db.execute("UPDATE prefixes SET modlog = null WHERE guild_id = $1", ctx.guild.id)
            await self.bot.db.execute("DROP TABLE IF EXISTS modlogs.modlogs_{}".format(ctx.guild.id))
            await ctx.send('✅ | **ModLogs** have been disabled')

    @commands.has_permissions(administrator=True)
    @modlogs.command(name='reason')
    async def reason(self, ctx: CustomContext, case_id: int, *, reason: str):
        """Sets the reason for a mod-log entry"""
        cog: LoggingBackend = self.bot.get_cog('LoggingBackend')  # type: ignore
        if not cog:
            raise commands.BadArgument('Sorry, this service is temporarily unavailable!')
        if not (mod_log := await cog.get_modlog(ctx.guild)):
            raise commands.BadArgument('This guild does not have a mod-log enabled!')
        if ctx.channel == mod_log:
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.delete()
        else:
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.add_reaction('🔃')
        try:
            case = await self.bot.db.fetchval(
                "SELECT case_id FROM modlogs.modlogs_{} WHERE case_id = $1".format(ctx.guild.id), case_id
            )
            if not case:
                raise commands.BadArgument(f'I could not find the case number {case_id}!')
        except asyncpg.UndefinedTableError:
            raise commands.BadArgument(f'I could not find the case number {case_id}!')
        await self.bot.db.execute(
            "UPDATE modlogs.modlogs_{} SET reason = $2 WHERE case_id = $1".format(ctx.guild.id), case_id, reason
        )
        await cog.update_message(ctx.guild, case_id)
        if mod_log != ctx.channel:
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.remove_reaction('🔃', ctx.guild.me)
                await ctx.message.add_reaction('✅')

from __future__ import annotations

from typing import (
    Optional,
    Union,
)

import discord
from discord.ext import commands

from utils import DuckCog
from .modutils import can_execute_action, safe_reason
from utils.context import DuckContext
from utils.errorhandler import HandleHTTPException


class StandardModeration(DuckCog):
    """A cog dedicated to holding standard
    moderation commands. Such as ban or kick.
    
    Attributes
    ----------
    bot: :class:`DuckBot`
        The main bot instance.
    """

    @commands.command(name='kick', aliases=['boot'])
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_guild_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: DuckContext, member: discord.Member, *, reason: Optional[str] = '...') -> Optional[discord.Message]:
        """|coro|
        
        Kick a member from the server.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to kick.
        reason: Optional[:class:`str`]
            The reason for kicking the member. Defaults to 'being a jerk!'.
        """
        guild = ctx.guild
        if guild is None:
            return

        await can_execute_action(ctx, member)

        async with HandleHTTPException(ctx):
            await member.kick(reason=safe_reason(ctx, reason))

        return await ctx.send(f'Kicked **{member}** for: {reason}')

    @commands.command(name='ban')
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: DuckContext, user: discord.User, *, reason: Optional[str] = '...') -> Optional[discord.Message]:
        """|coro|

        Ban a member from the server.

        Parameters
        ----------
        user: :class:`discord.Member`
            The member to ban.
        reason: Optional[:class:`str`]
            The reason for banning the member. Defaults to 'being a jerk!'.
        """
        guild = ctx.guild
        if guild is None:
            return

        await can_execute_action(ctx, user)

        async with HandleHTTPException(ctx):
            await guild.ban(user, reason=safe_reason(ctx, reason))

        return await ctx.send(f'Banned **{user}** for: {reason}')

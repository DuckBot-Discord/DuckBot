from __future__ import annotations

from typing import (
    Optional,
)

import discord
from discord.ext import commands

from utils import (
    DuckCog, 
    safe_reason, 
)
from utils.context import DuckContext
from utils.errorhandler import HandleHTTPException
from utils.converters import TargetVerifier, BanEntryConverter


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
    async def kick(self, ctx: DuckContext, member: TargetVerifier[discord.Member], *, reason: str = '...') -> Optional[discord.Message]: # type: ignore
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

        async with HandleHTTPException(ctx, title=f'Failed to kick {member}'):
            await member.kick(reason=safe_reason(ctx.author, reason))

        return await ctx.send(f'Kicked **{member}** for: {reason}')

    @commands.command(name='ban')
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: DuckContext, user: TargetVerifier[discord.User], *, reason: str = '...') -> Optional[discord.Message]: # type: ignore
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

        async with HandleHTTPException(ctx, title=f'Failed to ban {user}'):
            await guild.ban(user, reason=safe_reason(ctx.author, reason))

        return await ctx.send(f'Banned **{user}** for: {reason}')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx: DuckContext, *, user: BanEntryConverter):
        """unbans a user from this server.
        Can search by:
        - `user ID` (literal - number)
        - `name#0000` (literal - case insensitive)
        - `name` (literal - case insensitive)
        - `name` (close matches - will prompt to confirm)
        """
        guild = ctx.guild
        if guild is None:
            return
        
        async with HandleHTTPException(ctx, title=f'Failed to unban {user}'):
            await guild.unban(user.user, reason=f"Unban by {ctx.author} ({ctx.author.id})")

        extra = f"Previously banned for: {user.reason}" if user.reason else ''
        return await ctx.send(f"Unbanned **{user}**\n{extra}")


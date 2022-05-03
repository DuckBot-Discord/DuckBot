from __future__ import annotations

from typing import (
    Optional,
)

import discord
from discord.ext import commands

from utils import (
    DuckContext,
    HandleHTTPException,
    TargetVerifier,
    BanEntryConverter,
    DuckCog,
    safe_reason,
    mdr,
    command
)
from utils.helpers import can_execute_action


class StandardModeration(DuckCog):
    """A cog dedicated to holding standard
    moderation commands. Such as ban or kick.
    """

    @command(name='kick', aliases=['boot'], hybrid=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_guild_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(
        self, 
        ctx: DuckContext, 
        member: TargetVerifier(discord.Member),  # type: ignore
        *,   
        reason: str = '...'
        ) -> Optional[discord.Message]:
        """        
        Kick a member from the server.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to kick. (can be an ID)
        reason: Optional[:class:`str`]
            The reason for the kick.'.
        """
        guild = ctx.guild
        if guild is None:
            return
        
        await ctx.defer()

        async with HandleHTTPException(ctx, title=f'Failed to kick {member}'):
            await member.kick(reason=safe_reason(ctx.author, reason))

        return await ctx.send(f'Kicked **{member}** for: {reason}')

    @command(name='ban')
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: DuckContext, user: discord.User, *, delete_days: Optional[int], reason: str = '...') -> Optional[discord.Message]:
        """|coro|

        Ban a member from the server.

        Parameters
        ----------
        user: :class:`discord.Member`
            The member to ban.
        delete_days: Optional[:class:`int`]
            The number of days worth of messages to delete.
        reason: Optional[:class:`str`]
            The reason for banning the member. Defaults to 'being a jerk!'.
        """
        await can_execute_action(ctx, user, fail_if_not_upgrade=False)

        async with HandleHTTPException(ctx, title=f'Failed to ban {user}'):
            await ctx.guild.ban(user, reason=safe_reason(ctx.author, reason))

        return await ctx.send(f'Banned **{user}** for: {reason}')

    @command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx: DuckContext, *, user: BanEntryConverter):
        """|coro|
        
        Unbans a user from this server. You can search for this by:
 
        +------------------+--------------------------+----------------------------+
        |     User ID      |        Name#0000         |            Name            |
        +------------------+--------------------------+----------------------------+
        | Literal - Number | Literal - case sensitive | Literal - case insensitive |
        +------------------+--------------------------+----------------------------+

        Parameters
        ----------
        user: :class:`discord.User`
            The user to unban.
        """
        guild = ctx.guild
        if guild is None:
            return
        
        async with HandleHTTPException(ctx, title=f'Failed to unban {user}'):
            await guild.unban(user.user, reason=f"Unban by {ctx.author} ({ctx.author.id})")

        extra = f"Previously banned for: {user.reason}" if user.reason else ''
        return await ctx.send(f"Unbanned **{user}**\n{extra}")

    @command(name='nick', hybrid=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    @commands.has_guild_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def nick(self, ctx: DuckContext, member: discord.Member, *, nickname: Optional[str] = None):
        """Change a member's nickname.

        Parameters
        ----------
        member: :class:`discord.Member`
            The member to change the nickname of.
        nickname: Optional[:class:`str`]
            The nickname to set. If no nickname is provided, the nickname will be removed.
        """
        await can_execute_action(ctx, member) 

        if nickname is None and not member.nick:
            return await ctx.send(f'**{mdr(member)}** has no nickname to remove.')

        if nickname is not None and len(nickname) > 32:
            return await ctx.send(f'Nickname is too long! ({len(nickname)}/32)')

        async with HandleHTTPException(ctx, title=f'Failed to set nickname for {member}.'):
            await member.edit(nick=nickname)

        message = 'Changed nickname of **{user}** to **{nick}**.' \
            if nickname else 'Removed nickname of **{user}**.'
        return await ctx.send(message.format(user=mdr(member), nick=mdr(nickname)))

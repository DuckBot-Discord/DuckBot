from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import (
    DuckContext,
    HandleHTTPException,
    VerifiedMember,
    VerifiedUser,
    BanEntryConverter,
    DuckCog,
    safe_reason,
    mdr,
    command,
    UserFriendlyTime,
    human_timedelta,
    Timer,
    format_date,
)
from utils.checks import hybrid_permissions_check
from utils.helpers import can_execute_action


class StandardModeration(DuckCog):
    """A cog dedicated to holding standard
    moderation commands. Such as ban or kick.
    """

    @command(name='kick', aliases=['boot'], hybrid=True)
    @hybrid_permissions_check(kick_members=True, bot_kick_members=True)
    async def kick(self, ctx: DuckContext, member: VerifiedMember, *, reason: str = '...') -> Optional[discord.Message]:
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

    @command(name='ban', hybrid=True)
    @hybrid_permissions_check(ban_members=True, bot_ban_members=True)
    @app_commands.rename(delete_days='delete-days')
    async def ban(
        self,
        ctx: DuckContext,
        user: VerifiedUser,
        *,
        delete_days: Optional[commands.Range[int, 0, 7]] = 1,
        reason: str = '...',
    ) -> Optional[discord.Message]:
        """
        Bans a member from the server.

        Parameters
        ----------
        user: :class:`discord.Member`
            The member to ban.
        delete_days: Optional[:class:`int`]
            The number of days worth of messages to delete.
        reason: Optional[:class:`str`]
            The reason for banning the member. Defaults to '...'.
        """

        async with HandleHTTPException(ctx, title=f'Failed to ban {user}'):
            seconds = (delete_days or 0) * 86400
            await ctx.guild.ban(user, delete_message_seconds=seconds, reason=safe_reason(ctx.author, reason))

        return await ctx.send(f'Banned **{user}** for: {reason}')

    @command(name='softban')
    @hybrid_permissions_check(ban_members=True, bot_ban_members=True)
    @app_commands.rename(delete_days='delete-days')
    async def softban(
        self,
        ctx: DuckContext,
        user: VerifiedUser,
        *,
        delete_days: Optional[commands.Range[int, 0, 7]] = 1,
        reason: str = '...',
    ) -> Optional[discord.Message]:
        """Ban a member from the server, then immediately unbans them, deleting all their messages in the process.

        Parameters
        ----------
        user: :class:`discord.Member`
            The member to softban.
        delete_days: Optional[:class:`int`]
            The number of days worth of messages to delete.
        reason: Optional[:class:`str`]
            The reason for softbanning the member. Defaults to '...'.
        """

        async with HandleHTTPException(ctx, title=f'Failed to ban {user}'):
            seconds = (delete_days or 0) * 86400

            await ctx.guild.ban(user, delete_message_seconds=seconds, reason=safe_reason(ctx.author, reason))
            await ctx.guild.unban(user, reason=safe_reason(ctx.author, reason))

        return await ctx.send(f'Banned **{user}** for: {reason}')

    @command(hybrid=True)
    @hybrid_permissions_check(ban_members=True, bot_ban_members=True)
    async def unban(self, ctx: DuckContext, *, user: BanEntryConverter):
        """Unbans a user from this server. You can search for this by:

        The lookup strategy for the ``user`` parameter is as follows (in order):

        - User ID: The ID of a user that.
        - User Mention: The mention of a user.
        - Name and discriminator: The Name#0000 format of a user (case sensitive, will look at the ban list to find the user).
        - Name: The name of a user (case insensitive, will look at the ban list to find the user).

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
    @hybrid_permissions_check(manage_nicknames=True, bot_manage_nicknames=True)
    async def nick(self, ctx: DuckContext, member: VerifiedMember, *, nickname: Optional[str] = None):
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

        message = 'Changed nickname of **{user}** to **{nick}**.' if nickname else 'Removed nickname of **{user}**.'
        return await ctx.send(message.format(user=mdr(member), nick=mdr(nickname)))

    @command(name='tempban', aliases=['tban'])
    @hybrid_permissions_check(ban_members=True, bot_ban_members=True)
    async def tempban(
        self,
        ctx: DuckContext,
        member: VerifiedUser,
        *,
        when: UserFriendlyTime(commands.clean_content, default='...'),  # type: ignore
    ) -> None:
        """

        Temporarily ban a user from the server.

        This command temporarily bans a user from the server. The user will be able to rejoin the server, but will be
        unable to send messages.

        The user will be banned for 24 hours by default. If you wish to ban for a longer period of time, use the
        `ban` command instead.

        Examples
        --------
        `db.tempban @DuckBot 3 hours being too good.`

        Parameters
        ----------
        member : discord.Member
            The member to ban.
        when : UserFriendlyTime
            The reason and time of the ban, for example, "hours for being a bad"
        """

        async with HandleHTTPException(ctx):
            await ctx.guild.ban(member, reason=safe_reason(ctx.author, when.arg))

        await self.bot.pool.execute(
            """
            DELETE FROM timers
            WHERE event = 'ban'
            AND (extra->'args'->0) = $1
            AND (extra->'args'->1) = $2
        """,
            member.id,
            ctx.guild.id,
        )

        await self.bot.create_timer(when.dt, 'ban', member.id, ctx.guild.id, ctx.author.id, precise=False)

        await ctx.send(f"Banned **{mdr(member)}** for {human_timedelta(when.dt)}.")

    @commands.Cog.listener('on_ban_timer_complete')
    async def on_ban_timer_complete(self, timer: Timer):
        """Automatic unban handling."""
        member_id, guild_id, moderator_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            self.logger.info('Guild %s not found, discarding...', guild_id)
            return  # F

        moderator = await self.bot.get_or_fetch_user(moderator_id)
        if moderator is None:
            mod = f"@Unknown User ({moderator_id})"
        else:
            mod = f"@{moderator} ({moderator_id})"

        try:
            await guild.unban(
                discord.Object(id=member_id),
                reason=f"Automatic unban for temp-ban by {mod} " f"on {format_date(timer.created_at)}.",
            )
        except discord.HTTPException as e:
            self.logger.debug(f"Failed to unban {member_id} in {guild_id}.", exc_info=e)

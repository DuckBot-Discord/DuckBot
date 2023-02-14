from __future__ import annotations

import logging

import discord
from discord.ext import commands

from utils import (
    DuckContext,
    DuckCog,
    HandleHTTPException,
    VerifiedUser,
    UserFriendlyTime,
    safe_reason,
    mdr,
    human_timedelta,
    Timer,
    format_date,
    command,
)

log = logging.getLogger('DuckBot.moderation.temporary')


class TemporaryCommands(DuckCog):
    @command(name='tempban', aliases=['tban'])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: DuckContext,
        member: discord.Member | discord.User = VerifiedUser,
        *,
        when: UserFriendlyTime(commands.clean_content, default='...'),  # type: ignore
    ) -> None:
        """|coro|

        Temporarily ban a user from the server.

        This command temporarily bans a user from the server. The user will be able to rejoin the server, but will be
        unable to send messages.

        The user will be banned for 24 hours by default. If you wish to ban for a longer period of time, use the
        `ban` command instead.

        Parameters
        ----------
        member : discord.Member
            The member to ban.
        when : UserFriendlyTime
            The reason and time of the ban, for example, "?ban @LeoCx1000 for 5 hours for being a bad"
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
            log.info('Guild %s not found, discarding...', guild_id)
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
            log.debug(f"Failed to unban {member_id} in {guild_id}.", exc_info=e)

from __future__ import annotations

import logging
import pytz
from typing import (
    Optional, 
)

import discord
from discord.ext import commands

from utils import DuckCog
from utils.context import DuckContext
from utils.time import UserFriendlyTime
from utils.timer import Timer, TimerNotFound

log = logging.getLogger('DuckBot.cogs.meta.reminders')


class JumpView(discord.ui.View):
    def __init__(self, jump_url: str, *, label: Optional[str] = None):
        super().__init__(timeout=1)
        self.add_item(discord.ui.Button(label=label or 'Go to message', url=jump_url))


class Reminders(DuckCog):
    """Used to create and manage reminders."""

    @commands.group(name='remind', aliases=['remindme', 'reminder'], invoke_without_command=True)
    async def remindme(
        self,
        ctx: DuckContext,
        *,
        when: UserFriendlyTime(commands.clean_content, default='...')  # type: ignore
    ) -> None:
        """|coro|
        
        Reminds you of something in the future.

        Parameters
        ----------
        when : `UserFriendlyTime`
            When and for what to remind you for. Which can either be a date (YYYY-MM-DD) or a human-readable time, like:

            - "next thursday at 3pm do something funny"
            - "do the dishes tomorrow"
            - "in 3 days do the thing"
            - "2d unmute someone"

            Times are in UTC.
        """
        timer = await self.bot.create_timer(
            when.dt,
            'reminder',

            ctx.author.id,
            ctx.channel.id,
            when.arg,

            message_id=ctx.message.id,
            precise=False
        )
        await ctx.send(f"Alright {ctx.author.mention}, {discord.utils.format_dt(when.dt, 'R')}: {when.arg}")

    # noinspection PyShadowingBuiltins
    @remindme.command(name='delete')
    async def remindme_delete(self, ctx: DuckContext, id: int) -> None:
        """|coro|

        Deletes a reminder.

        Parameters
        ----------
        id : `int`
            The ID of the reminder to delete.
        """
        try:
            timer = await self.bot.get_timer(id)
            if timer.event != 'reminder':
                raise TimerNotFound(timer.id)
            if timer.args[0] != ctx.author.id:
                raise TimerNotFound(timer.id)
            await timer.delete(self.bot)
            await ctx.send(f'{self.bot.done_emoji} Okay, I deleted that reminder.')
        except TimerNotFound as error:
            await ctx.send(f"I couldn't find a reminder with ID {error.id}.")

    @remindme.command(name='list')
    async def remindme_list(self, ctx: DuckContext) -> None:
        """|coro|

        Lists all your upcoming reminders.
        """

        timers = await self.bot.pool.fetch("""
            SELECT id, expires, (extra->'args'->2) AS reason FROM timers
            WHERE event = 'reminder' AND (extra->'args'->0)::bigint = $1
            ORDER BY expires
        """, ctx.author.id)

        if not timers:
            await ctx.send("You have no upcoming reminders.")
            return

        embed = discord.Embed(title="Upcoming reminders", color=discord.Color.blurple())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        for index, (r_id, expires, reason) in enumerate(timers):
            if index > 9:
                embed.set_footer(text=f"(And {len(timers) - index} more)")
                break

            name = f"{r_id} - {discord.utils.format_dt(expires, 'R')}"
            value = reason if len(reason) < 1024 else reason[:1021] + '...'

            if (len(embed) + len(name) + len(value)) > 5900:
                embed.set_footer(text=f"(And {len(timers) - index} more)")
                break

            embed.add_field(name=name, value=value, inline=False)

        await ctx.send(embed=embed)

    @commands.Cog.listener('on_reminder_timer_complete')
    async def reminder_dispatch(self, timer: Timer) -> None:
        await self.bot.wait_until_ready()
        
        user_id, channel_id, user_input = timer.args
        
        channel: Union[discord.TextChannel, discord.Thread] = self.bot.get_channel(channel_id) # type: ignore # Type checker hates me
        if channel is None:
            return log.warning('Discarding channel %s as it\'s not found in cache.', channel_id)

        guild_id = channel.guild.id if isinstance(channel, (discord.TextChannel, discord.Thread)) else '@me'
        
        # We need to format_dt in utc so the user
        # can see the time in their local timezone. If not
        # the user will see the timestamp as 5 hours ahead.
        aware = timer.created_at.replace(tzinfo=pytz.UTC)
        msg = f'<@{user_id}>, {discord.utils.format_dt(aware, "R")}: {user_input}'
        
        view = discord.utils.MISSING
        if message_id := timer.kwargs.get('message_id'):
            jump_url = f'https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}'
            view = JumpView(jump_url)
        
        mentions = discord.AllowedMentions(users=True, everyone=False, roles=False)
        await channel.send(msg, view=view, allowed_mentions=mentions)
     



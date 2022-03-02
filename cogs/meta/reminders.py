from __future__ import annotations

import logging
from typing import (
    Optional, 
    Tuple
)

import discord
from discord.ext import commands

from utils import DuckCog
from utils.context import DuckContext
from utils.time import UserFriendlyTime
from utils.timer import Timer


log = logging.getLogger('DuckBot.cogs.meta.reminders')


class ToLower(commands.Converter):
    __slots__: Tuple[str, ...] = ()

    # noinspection PyProtocol
    async def convert(self, ctx: DuckContext, argument: str) -> str:
        return argument.lower()


class JumpView(discord.ui.View):
    def __init__(self, jump_url: str, *, label: Optional[str] = None):
        super().__init__(timeout=1)
        self.add_item(discord.ui.Button(label=label or 'Go to message', url=jump_url))


class Reminders(DuckCog):

    @commands.command(name='remindme', aliases=['remind'])
    async def remindme(
        self,
        ctx: DuckContext,
        when: UserFriendlyTime(ToLower, default='...') # type: ignore
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
        async with ctx.bot.safe_connection() as conn:
            timer = await ctx.bot.create_timer(
                when.dt,
                'reminder',

                ctx.author.id,
                ctx.channel.id,
                when.arg,

                connection=conn,
                precise=False
            )
            await ctx.send(f"Alright {ctx.author.mention}, {discord.utils.format_dt(when.dt, 'R')}: {when.arg}")

    @commands.Cog.listener('on_reminder_timer_complete')
    async def reminder_dispatch(self, timer: Timer) -> None:
        await self.bot.wait_until_ready()
        
        user_id, channel_id, user_input = timer.args

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return log.warning('Discarding channel %s as it\'s not found in cache.', channel_id)

        guild_id = channel.guild.id if isinstance(channel, (discord.TextChannel, discord.Thread)) else '@me'
        msg = f'<@{user_id}>, {discord.utils.format_dt(timer.created_at, "R")}: {user_input}'
        message_id = timer.kwargs.get('message_id')

        view = discord.utils.MISSING
        if message_id:
            jump_url = f'https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}'
            view = JumpView(jump_url)
        
        await channel.send(f'<@{user_id}>, {msg}', view=view)
    



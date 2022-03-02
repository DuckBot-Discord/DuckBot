import asyncio
import contextlib
import logging

import discord
from discord.ext import commands

from utils.context import DuckContext
from utils.errors import TimerNotFound
from utils.time import FutureTime
from utils.timer import Timer
from .modutils import can_execute_action
from utils.errorhandler import HandleHTTPException
from utils import DuckCog


log = logging.getLogger('DuckBot.moderation.block')


class Block(DuckCog):
    async def toggle_block(self, channel: discord.TextChannel, member: discord.Member,
                           blocked: bool = True, update_db: bool = True, reason: str = None):
        await channel.set_permissions(
            member, reason=reason,
            overwrite=discord.PermissionOverwrite(
                send_messages=False if blocked else None,
                add_reactions=False if blocked else None,
                create_public_threads=False if blocked else None,
                create_private_threads=False if blocked else None,
                send_messages_in_threads=False if blocked else None
            )
        )
        if update_db is True:
            if blocked is True:
                query = 'INSERT INTO blocks (guild_id, channel_id, user_id) VALUES ($1, $2, $3) ' \
                        'ON CONFLICT (guild_id, channel_id, user_id) DO NOTHING'
            else:
                query = "DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3"
            await self.bot.pool.execute(query, channel.guild.id, channel.id, member.id)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_permissions=True)
    @can_execute_action()
    async def block(self, ctx: DuckContext, *, member: discord.Member):
        """|coro|

        Blocks a user from your channel.

        Parameters
        ----------
        member: :class:`discord.Member`
            The member to block.
        """
        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=True, reason=reason)

        await ctx.send(f'✅ **|** Blocked **{discord.utils.remove_markdown(str(member))}** from **{ctx.channel}**')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_permissions=True)
    @can_execute_action()
    async def tempblock(self, ctx: DuckContext, time: FutureTime, *, member: discord.Member):
        """|coro|

        Temporarily blocks a user from your channel.

        Parameters
        ----------
        time: :class:`utils.time.FutureTime`
            The time to unblock the user.
        member: :class:`discord.Member`
            The member to block.
        """
        reason = f'Tempblock by {ctx.author} (ID: {ctx.author.id}) until {time.dt}'

        await self.bot.create_timer(time.dt, 'tempblock', ctx.guild.id, ctx.channel.id,
                                    member.id, ctx.author.id, precise=False)

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=True, reason=reason)

        await ctx.send(f'✅ **|** Blocked **{discord.utils.remove_markdown(str(member))}** '
                       f'until {discord.utils.format_dt(time.dt, "R")}')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    @can_execute_action()
    async def unblock(self, ctx: DuckContext, *, member: discord.Member):
        """Unblocks a user from your channel."""
        # Firstly, we get any running temp-block timers.
        # If there are any, we cancel them.

        db_timers = await self.bot.pool.fetch("""
            SELECT id FROM timers WHERE event = 'tempblock'
            AND (extra->'args'->0)::bigint = $1
                -- First arg is the guild ID
            AND (extra->'args'->1)::bigint = $2
                -- Second arg is the channel ID
            AND (extra->'args'->2)::bigint = $3
                -- Third arg is the user ID
            ORDER BY expires
        """, ctx.guild.id, ctx.channel.id, member.id)
        for timer in db_timers:
            with contextlib.suppress(TimerNotFound):
                await self.bot.delete_timer(timer['id'])

        # then the actual unblock

        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=False, reason=reason)

        await ctx.send(f'✅ **|** Unblocked **{discord.utils.remove_markdown(str(member))}**')

    @commands.Cog.listener('on_member_join')
    async def on_member_join(self, member: discord.Member):
        """Blocks a user from your channel."""
        guild = member.guild
        if guild is None:
            return
        channel_ids = await self.bot.pool.fetch('SELECT channel_id FROM blocks WHERE guild_id = $1 AND user_id = $2',
                                                guild.id, member.id)
        for record in channel_ids:
            channel_id = record['channel_id']
            try:
                channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
            except discord.HTTPException:
                log.debug(f"Discarding blocked users for channel id {channel_id} as it can't be found.")
                await self.bot.pool.execute('DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2',
                                            guild.id, channel_id)
                continue
            else:
                try:
                    await self.toggle_block(channel, member, blocked=True, update_db=False,
                                            reason='[MEMBER-JOIN] Automatic re-block for previously blocked user.')
                    await asyncio.sleep(1)
                except discord.Forbidden:
                    log.debug(f"Did not unblock user {member} in channel {channel} due to missing permissions.", exc_info=False)
                    continue
                except discord.HTTPException:
                    log.debug(f"Unexpected error while re-blocking user {member} in channel {channel}.", exc_info=False)

    @commands.Cog.listener('on_tempblock_timer_complete')
    async def on_tempblock_timer_complete(self, timer: Timer):
        """Automatic temp block expire handler"""
        guild_id, channel_id, user_id, author_id = timer.args

        try:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return

            channel = guild.get_channel(channel_id)
            if channel is None:
                return

            try:
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                # Can't really 100% rely on member cache, so we'll just try to fetch.
            except discord.HTTPException:
                return log.debug(f"Discarding blocked users for channel id {channel_id} as it can't be found.")

            try:
                mod = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
                f"{mod} (ID: {author_id})"
            except discord.HTTPException:
                mod = f"unknown moderator (ID: {author_id})"

            await self.toggle_block(channel, member, blocked=False, update_db=False,
                                    reason=f'Expiring temp-block made on {timer.created_at} by {mod}')

        finally:
            # Finally, we remove the user from the list of blocked users, regardless of any errors.
            await self.bot.pool.execute('DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3',
                                        guild_id, channel_id, user_id)

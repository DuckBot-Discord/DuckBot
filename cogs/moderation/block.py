import asyncio
import contextlib
import logging
import math
import typing
from typing import Optional, List

import discord
from discord.ext import commands

from utils.timer import Timer
from utils.errors import TimerNotFound
from utils import (
    DuckContext,
    DuckCog,
    HandleHTTPException,
    TargetVerifier,
    mdr,
    FutureTime
)

log = logging.getLogger('DuckBot.moderation.block')


class Block(DuckCog):

    async def toggle_block(
            self,
            channel: discord.abc.Messageable,
            member: discord.Member,
            blocked: bool = True,
            update_db: bool = True,
            reason: Optional[str] = None
    ) -> None:
        """|coro|
        
        Toggle the block status of a member in a channel.
        
        Parameters
        ----------
        channel : `discord.abc.Messageable`
            The channel to block/unblock the member in.
        member : `discord.Member`
            The member to block/unblock.
        blocked : `bool`, optional
            Whether to block or unblock the member. Defaults to ``True``, which means block.
        update_db : `bool`, optional
            Whether to update the database with the new block status.
        """

        # The prereq here is that channel is not a DM channel
        # and the channel has a guild attr.
        if isinstance(channel, discord.Thread):
            channel = channel.parent  # type: ignore
            if not channel:
                return None

        val = False if blocked else None
        await channel.set_permissions(  # type: ignore
            member, reason=reason,
            overwrite=discord.PermissionOverwrite(
                send_messages=val,
                add_reactions=val,
                create_public_threads=val,
                create_private_threads=val,
                send_messages_in_threads=val
            )
        )

        if update_db:
            if blocked:
                query = 'INSERT INTO blocks (guild_id, channel_id, user_id) VALUES ($1, $2, $3) ' \
                        'ON CONFLICT (guild_id, channel_id, user_id) DO NOTHING'
            else:
                query = "DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3"

            async with self.bot.safe_connection() as conn:
                await conn.execute(query, channel.guild.id, channel.id, member.id)  # type: ignore

    async def format_block(self, guild: discord.Guild, user_id: int, channel_id: int = None):
        """|coro|

        Format a block entry from the database into a human-readable string.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild the block is in.
        channel_id: :class:`int`
            The channel ID of the block.
        user_id: :class:`int`
            The user ID of the block.

        Returns
        -------
        :class:`str`
            The formatted block entry.
        """
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel is None:
                channel = '#deleted-channel - '
            else:
                channel = f"#{channel} ({channel_id}) - "
        else:
            channel = ''
        user = await self.bot.get_or_fetch_member(guild, user_id) or f"Unknown User"

        return f"{channel}@{user} ({user_id})"

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_permissions=True)
    async def block(self, ctx: DuckContext, *, member: TargetVerifier[discord.Member]):  # type: ignore
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

        await ctx.send(f'✅ **|** Blocked **{mdr(member)}** from **{ctx.channel}**')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_permissions=True)
    async def tempblock(self, ctx: DuckContext, time: FutureTime, *,
                        member: TargetVerifier[discord.Member]):  # type: ignore
        """|coro|

        Temporarily blocks a user from your channel.

        Parameters
        ----------
        time: :class:`utils.time.FutureTime`
            The time to unblock the user.
        member: :class:`discord.Member`
            The member to block.
        """
        guild = ctx.guild
        if guild is None:  # Type checker happy
            return

        reason = f'Tempblock by {ctx.author} (ID: {ctx.author.id}) until {time.dt}'

        await self.bot.create_timer(time.dt, 'tempblock', guild.id, ctx.channel.id, member.id, ctx.author.id,
                                    precise=False)

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=True, reason=reason)

        await ctx.send(f'✅ **|** Blocked **{mdr(member)}** '
                       f'until {discord.utils.format_dt(time.dt, "R")}')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unblock(self, ctx: DuckContext, *, member: TargetVerifier[discord.Member]):  # type: ignore
        """|coro|

        Unblocks a user from your channel.

        Parameters
        ----------
        member: :class:`discord.Member`
            The member to unblock.
        """

        # Firstly, we get any running temp-block timers.
        # If there are any, we cancel them.
        guild = ctx.guild
        if guild is None:
            return

        db_timers = await self.bot.pool.fetch("""
            SELECT id FROM timers WHERE event = 'tempblock'
            AND (extra->'args'->0)::bigint = $1
                -- First arg is the guild ID
            AND (extra->'args'->1)::bigint = $2
                -- Second arg is the channel ID
            AND (extra->'args'->2)::bigint = $3
                -- Third arg is the user ID
            ORDER BY expires
        """, guild.id, ctx.channel.id, member.id)

        with contextlib.suppress(TimerNotFound):
            for timer in db_timers:
                await self.bot.delete_timer(timer['id'])

        # then the actual unblock
        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=False, reason=reason)

        await ctx.send(f'✅ **|** Unblocked **{mdr(member)}**')

    @commands.command(aliases=['blocks'])
    @commands.has_permissions(manage_messages=True)
    async def blocked(self, ctx: DuckContext, page: typing.Optional[int] = 1, *, channel: discord.TextChannel = None):
        """|coro|
        Gets a list of all blocked users in a channel.
        If no channel is specified, it will show the
        blocked users for all the chnannels in the server.

        Parameters
        ----------
        page: :class:`int`
            The page number to show.
        channel: :class:`discord.TextChannel`
            The channel to get the blocked users from.
        """
        guild = ctx.guild
        if guild is None:
            return  # i hate your type checker chai.

        # Firstly we generate the queries and arguments
        args = [guild.id]

        if channel is not None:
            query = "SELECT user_id FROM blocks WHERE guild_id = $1 AND channel_id = $2"
            count_query = "SELECT COUNT(*) FROM blocks WHERE guild_id = $1 AND channel_id = $2"
            args.append(channel.id)
        else:
            query = "SELECT channel_id, user_id FROM blocks WHERE guild_id = $1"
            count_query = "SELECT COUNT(*) FROM blocks WHERE guild_id = $1"
        query += f"ORDER BY channel_id OFFSET {(page - 1) * 10}"

        # Then we get the results and check if there are any
        fetched_blocks = await self.bot.pool.fetch(query, *args)

        if not fetched_blocks:
            return await ctx.send('❌ **|** No blocked users found.')

        # then we format the results and send them
        count = await self.bot.pool.fetchval(count_query, *args)
        max_pages = math.ceil(count / 10)

        blocks: str = '\n'.join([await self.format_block(guild=guild, **block) for block in fetched_blocks])  # type: ignore

        if max_pages > 1:
            ch_m = f' {channel.mention}' if channel else ''
            extra = f"\nNext page: `{ctx.clean_prefix}{ctx.invoked_with} {page + 1}{ch_m}`"
        else:
            extra = ''

        channel = f"{channel.mention}\n" if channel else 'all channels - '
        await ctx.send(f'📋 **|** Blocked users in {channel}'
                       f'Showing: `{len(fetched_blocks)}/{count}` - '
                       f'Showing Page: `{page}/{max_pages}`\n'
                       f'```\n{blocks}\n```' + extra)

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
                await self.bot.pool.execute('DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2', guild.id,
                                            channel_id)
                continue
            else:
                try:
                    if channel.permissions_for(guild.me).manage_permissions:
                        await self.toggle_block(
                            channel,  # type: ignore
                            member,
                            blocked=True,
                            update_db=False,
                            reason='[MEMBER-JOIN] Automatic re-block for previously blocked user. See "db.blocked" for a list of blocked users.'
                        )
                        await asyncio.sleep(1)
                except discord.Forbidden:
                    log.debug(f"Did not unblock user {member} in channel {channel} due to missing permissions.",
                              exc_info=False)
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

            # Can't really 100% rely on member cache, so we'll just try to fetch.
            member = await self.bot.get_or_fetch_member(guild, user_id)
            if not member:
                return log.debug("Discarding blocked users for channel id {channel_id} as it can't be found.")

            try:
                mod = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
                f"{mod} (ID: {author_id})"
            except discord.HTTPException:
                mod = f"unknown moderator (ID: {author_id})"

            await self.toggle_block(
                channel,  # type: ignore
                member,
                blocked=False, update_db=False,
                reason=f'Expiring temp-block made on {timer.created_at} by {mod}'
            )

        finally:
            # Finally, we remove the user from the list of blocked users, regardless of any errors.
            await self.bot.pool.execute('DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3',
                                        guild_id, channel_id, user_id)

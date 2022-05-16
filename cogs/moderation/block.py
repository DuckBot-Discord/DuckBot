from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from typing import (
    Optional,
)

import discord
from discord import app_commands
from discord.ext import commands

from utils import DuckContext, DuckCog, ActionNotExecutable, HandleHTTPException, mdr, FutureTime, TargetVerifier, command

from utils.interactions import (
    HandleHTTPException as InterHandleHTTPException,
    can_execute_action,
    has_permissions,
    bot_has_permissions,
)

from utils import TimerNotFound, Timer

log = logging.getLogger('DuckBot.moderation.block')


class Block(DuckCog):
    async def toggle_block(
        self,
        channel: discord.TextChannel,
        member: discord.Member,
        blocked: bool = True,
        update_db: bool = True,
        reason: Optional[str] = None,
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
        reason : `str`, optional
            The reason for the block/unblock.
        """
        if isinstance(channel, discord.abc.PrivateChannel):
            raise commands.NoPrivateMessage()

        if isinstance(channel, discord.Thread):
            channel = channel.parent  # type: ignore
            if not channel:
                raise ActionNotExecutable("Couldn't block! This thread has no parent channel... somehow.")

        val = False if blocked else None
        overwrites = channel.overwrites_for(member)

        overwrites.update(
            send_messages=val,
            add_reactions=val,
            create_public_threads=val,
            create_private_threads=val,
            send_messages_in_threads=val,
        )
        try:
            await channel.set_permissions(member, reason=reason, overwrite=overwrites)
        finally:
            if update_db:
                if blocked:
                    query = (
                        'INSERT INTO blocks (guild_id, channel_id, user_id) VALUES ($1, $2, $3) '
                        'ON CONFLICT (guild_id, channel_id, user_id) DO NOTHING'
                    )
                else:
                    query = "DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3"

                async with self.bot.safe_connection() as conn:
                    await conn.execute(query, channel.guild.id, channel.id, member.id)

    async def format_block(self, guild: discord.Guild, user_id: int, channel_id: Optional[int] = None):
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

    @command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_permissions=True)
    async def block(self, ctx: DuckContext, *, member: TargetVerifier(discord.Member)):  # type: ignore
        """|coro|

        Blocks a user from your channel.

        Parameters
        ----------
        member: :class:`discord.Member`
            The member to block.
        """
        if not isinstance(ctx.channel, discord.TextChannel):
            raise ActionNotExecutable(
                'This action is not supported in this channel type. Only text channels are currently supported.'
            )

        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=True, reason=reason)

        await ctx.send(f'✅ **|** Blocked **{mdr(member)}** from **{ctx.channel}**')

    @command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_permissions=True)
    async def tempblock(self, ctx: DuckContext[discord.TextChannel], time: FutureTime, *, member: TargetVerifier(discord.Member)):  # type: ignore
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

        await self.bot.create_timer(
            time.dt, 'tempblock', ctx.guild.id, ctx.channel.id, member.id, ctx.author.id, precise=False
        )

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=True, reason=reason)

        await ctx.send(f'✅ **|** Blocked **{mdr(member)}** until {discord.utils.format_dt(time.dt, "R")}')

    @command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unblock(self, ctx: DuckContext, *, member: TargetVerifier(discord.Member)):  # type: ignore
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

        db_timers = await self.bot.pool.fetch(
            """
            SELECT id FROM timers WHERE event = 'tempblock'
            AND (extra->'args'->0)::bigint = $1
                -- First arg is the guild ID
            AND (extra->'args'->1)::bigint = $2
                -- Second arg is the channel ID
            AND (extra->'args'->2)::bigint = $3
                -- Third arg is the user ID
            ORDER BY expires
        """,
            guild.id,
            ctx.channel.id,
            member.id,
        )

        with contextlib.suppress(TimerNotFound):
            for timer in db_timers:
                await self.bot.delete_timer(timer['id'])

        # then the actual unblock
        reason = f'Unblock by {ctx.author} (ID: {ctx.author.id})'

        async with HandleHTTPException(ctx):
            await self.toggle_block(ctx.channel, member, blocked=False, reason=reason)

        await ctx.send(f'✅ **|** Unblocked **{mdr(member)}**')

    @command(aliases=['blocks'])
    @commands.has_permissions(manage_guild=True)
    async def blocked(self, ctx: DuckContext, page: int = 1, *, channel: Optional[discord.TextChannel] = None):
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

        channel_fmt = f"{channel.mention}\n" if channel else 'all channels - '
        await ctx.send(
            f'📋 **|** Blocked users in {channel_fmt}'
            f'Showing: `{len(fetched_blocks)}/{count}` - '
            f'Showing Page: `{page}/{max_pages}`\n'
            f'```\n{blocks}\n```' + extra
        )

    @commands.Cog.listener('on_member_join')
    async def on_member_join(self, member: discord.Member):
        """Blocks a user from your channel."""
        guild = member.guild
        if guild is None:
            return

        channel_ids = await self.bot.pool.fetch(
            'SELECT channel_id FROM blocks WHERE guild_id = $1 AND user_id = $2', guild.id, member.id
        )

        for record in channel_ids:
            channel_id = record['channel_id']
            try:
                channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
            except discord.HTTPException:
                log.debug(f"Discarding blocked users for channel id {channel_id} as it can't be found.")
                await self.bot.pool.execute(
                    'DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2', guild.id, channel_id
                )
                continue
            else:
                try:
                    if channel.permissions_for(guild.me).manage_permissions:
                        await self.toggle_block(
                            channel,  # type: ignore
                            member,
                            blocked=True,
                            update_db=False,
                            reason='[MEMBER-JOIN] Automatic re-block for previously blocked user. See "db.blocked" for a list of blocked users.',
                        )
                        await asyncio.sleep(1)
                except discord.Forbidden:
                    log.debug(
                        f"Did not unblock user {member} in channel {channel} due to missing permissions.", exc_info=False
                    )
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
                blocked=False,
                update_db=False,
                reason=f'Expiring temp-block made on {timer.created_at} by {mod}',
            )

        finally:
            # Finally, we remove the user from the list of blocked users, regardless of any errors.
            await self.bot.pool.execute(
                'DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3', guild_id, channel_id, user_id
            )

    slash_block = app_commands.Group(name='block', description='Blocks users from channels')

    @slash_block.command(name='user')
    @app_commands.describe(user='The user you wish to block.')
    async def app_block_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        """Blocks a user from your channel."""
        await has_permissions(interaction, manage_messages=True)
        await bot_has_permissions(interaction, ban_members=True)
        await can_execute_action(interaction, user)

        if not isinstance(interaction.channel, discord.TextChannel):
            raise ActionNotExecutable(
                'This action is not supported in this channel type. Only text channels are currently supported.'
            )

        await interaction.response.defer()
        reason = f'Block by {interaction.user} (ID: {interaction.user.id})'

        async with InterHandleHTTPException(interaction.followup):
            await self.toggle_block(interaction.channel, user, blocked=True, reason=reason)

        await interaction.followup.send(f'✅ **|** Blocked **{mdr(user)}**')

    @slash_block.command(name='revoke')
    @app_commands.describe(user='The user you wish to block.')
    async def app_unblock_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        """Unblocks a user from your channel."""
        await has_permissions(interaction, manage_messages=True)
        await bot_has_permissions(interaction, ban_members=True)
        await can_execute_action(interaction, user)
        assert interaction.guild is not None
        assert interaction.channel is not None

        await interaction.response.defer()
        bot: DuckBot = interaction.client  # type: ignore
        await bot.pool.execute(
            """
            DELETE FROM timers WHERE event = 'tempblock'
            AND (extra->'args'->0)::bigint = $1
                -- First arg is the guild ID
            AND (extra->'args'->1)::bigint = $2
                -- Second arg is the channel ID
            AND (extra->'args'->2)::bigint = $3
                -- Third arg is the user ID
        """,
            interaction.guild.id,
            interaction.channel.id,
            user.id,
        )

        # then the actual unblock
        reason = f'Unblock by {interaction.user} (ID: {interaction.user.id})'

        async with InterHandleHTTPException(interaction.followup):
            await self.toggle_block(interaction.channel, user, blocked=False, reason=reason)  # type: ignore

        await interaction.followup.send(f'✅ **|** Unblocked **{mdr(user)}**')

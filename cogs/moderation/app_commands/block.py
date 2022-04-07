from __future__ import annotations

import discord
from discord import app_commands

from bot import DuckBot
from utils import (
    mdr
)
from utils.interactions import (
    HandleHTTPException,
    can_execute_action,
    has_permissions,
    bot_has_permissions,
)
from .._block_cog import BlockCog


class ApplicationBlock(BlockCog, name='block'):

    slash_block = app_commands.Group(name='block', description='Blocks users from channels')

    @slash_block.command(name='user')
    @app_commands.describe(
        user='The user you wish to block.'
    )
    async def app_block_user(
            self,
            interaction: discord.Interaction,
            user: discord.Member,
    ):
        """ Blocks a user from your channel. """
        await has_permissions(interaction, manage_messages=True)
        await bot_has_permissions(interaction, ban_members=True)
        await can_execute_action(interaction, user)

        await interaction.response.defer()
        followup: discord.Webhook = interaction.followup  # type: ignore
        reason = f'Block by {interaction.user} (ID: {interaction.user.id})'

        async with HandleHTTPException(followup):
            await self.toggle_block(interaction.channel, user, blocked=True, reason=reason)  # type: ignore

        await followup.send(f'✅ **|** Blocked **{mdr(user)}**')

    @slash_block.command(name='revoke')
    @app_commands.describe(
        user='The user you wish to block.'
    )
    async def app_unblock_user(
            self,
            interaction: discord.Interaction,
            user: discord.Member,
    ):
        """ Unblocks a user from your channel. """
        await has_permissions(interaction, manage_messages=True)
        await bot_has_permissions(interaction, ban_members=True)
        await can_execute_action(interaction, user)

        await interaction.response.defer()
        followup: discord.Webhook = interaction.followup  # type: ignore
        bot: DuckBot = interaction.client  # type: ignore

        await bot.pool.execute("""
            DELETE FROM timers WHERE event = 'tempblock'
            AND (extra->'args'->0)::bigint = $1
                -- First arg is the guild ID
            AND (extra->'args'->1)::bigint = $2
                -- Second arg is the channel ID
            AND (extra->'args'->2)::bigint = $3
                -- Third arg is the user ID
        """, interaction.guild.id, interaction.channel.id, user.id)

        # then the actual unblock
        reason = f'Unblock by {interaction.user} (ID: {interaction.user.id})'

        async with HandleHTTPException(followup):
            await self.toggle_block(interaction.channel, user, blocked=False, reason=reason)  # type: ignore

        await followup.send(f'✅ **|** Unblocked **{mdr(user)}**')

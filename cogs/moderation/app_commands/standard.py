import typing
from typing import (
    Optional,
    Tuple,
)

import discord
from discord import app_commands

from utils import (
    DuckCog,
    ShortTime,
    safe_reason,
    format_date,
    mdr
)

from utils.interactions import (
    HandleHTTPException,
    can_execute_action,
    has_permissions,
    bot_has_permissions,
    ActionNotExecutable,
)

__all__: Tuple[str, ...] = (
    'ApplicationStandard',
)


class ApplicationStandard(DuckCog):

    @app_commands.command(name='ban')
    @app_commands.describe(
        user='The user to ban. (can be a user ID)',
        duration='Duration of the ban (Must be a short time, like: "1y 2mo 3w 4d 5h 6m 7s" or a combination of them.)',
        reason='The reason for the ban.',
        delete_days='The number of days to delete messages from the user. (0 to 7 inclusive)',
    )
    async def app_ban(
            self,
            interaction: discord.Interaction,
            user: typing.Union[discord.Member, discord.User],
            duration: Optional[str] = None,
            delete_days: Optional[int] = 1,
            reason: Optional[str] = '...',
    ) -> None:
        """ Bans a user temporarily or permanently from this server. """
        await has_permissions(interaction, ban_members=True)
        await bot_has_permissions(interaction, ban_members=True)
        await can_execute_action(interaction, user)

        await interaction.response.defer()

        if delete_days and 0 >= delete_days >= 7:
            raise ActionNotExecutable('`delete_days` must be between 0 and 7 days.')

        dt = None
        if duration:
            time = ShortTime(duration.replace(' ', ''))
            dt = time.dt

            await self.bot.pool.execute("""
                DELETE FROM timers
                WHERE event = 'ban'
                AND (extra->'args'->0) = $1
                AND (extra->'args'->1) = $2
            """, user.id, interaction.guild.id)

            await self.bot.create_timer(
                dt,
                'ban',
                user.id,
                interaction.guild.id,
                interaction.user.id,
                precise=False
            )

        followup: discord.Webhook = interaction.followup  # noqa

        try:
            await interaction.guild.ban(user, reason=safe_reason(interaction.user, f"[Temp Ban Until: {format_date(dt)}] Reason: {reason}"))
        except discord.HTTPException:
            return await followup.send(f'Failed to ban {user}... Was it already banned? Am I missing permissions?')

        if dt:
            text = f"Banned **{mdr(user)}** until **{format_date(dt)}** for: {reason}"
        else:
            text = f"Banned **{mdr(user)}** permanently for: {reason}"
        await followup.send(text, wait=True)

    # @app_commands.command(name='kick')
    # @app_commands.describe(
    #     member='The member to kick. (can be an ID)',
    #     reason='The reason for the ban.',
    # )
    # async def app_kick(
    #         self,
    #         interaction: discord.Interaction,
    #         member: discord.Member,
    #         reason: Optional[str] = '...',
    # ) -> None:
    #     """ Kicks a member from this server """
    #     await has_permissions(interaction, kick_members=True)
    #     await bot_has_permissions(interaction, kick_members=True)
    #     await can_execute_action(interaction, member)

    #     await interaction.response.defer()
    #     followup: discord.Webhook = interaction.followup  # type: ignore

    #     with HandleHTTPException(followup):
    #         await member.kick(reason=safe_reason(interaction.user, reason))

    #     await followup.send(f"Successfully kicked **{mdr(member)}** for: {reason[0:1000]}")

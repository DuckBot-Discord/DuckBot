import logging

import discord
from discord import app_commands

from bot import DuckBot
from utils import DuckCog, UserFriendlyTime, TimerNotFound


class ApplicationReminders(DuckCog):
    """Reminds the user of something"""

    slash_reminder = app_commands.Group(name='reminder', description='Reminds the user of something')

    @slash_reminder.command(name='add')
    @app_commands.describe(when='When and what to remind you of. Example: "in 10 days do this", "next monday do that."')
    async def slash_remind_add(
        self,
        interaction: discord.Interaction[DuckBot],
        when: UserFriendlyTime,
    ) -> None:
        """Reminds you of something in the future."""
        bot: DuckBot = interaction.client

        await interaction.response.defer()
        original = await interaction.original_response()

        await bot.create_timer(
            when.dt,
            'reminder',
            interaction.user.id,
            interaction.channel_id,
            str(when.arg),
            message_id=original.id,
            precise=False,
        )
        await interaction.followup.send(f"Alright, {discord.utils.format_dt(when.dt, 'R')}: {when.arg}")

    @slash_reminder.command(name='delete')
    @app_commands.describe(id='The ID of the reminder you want to delete.')
    async def slash_remind_delete(self, interaction: discord.Interaction[DuckBot], id: int) -> None:
        """Deletes one fo your reminders."""
        await interaction.response.defer(ephemeral=True)
        bot: DuckBot = interaction.client
        try:
            timer = await bot.get_timer(id)
            if timer.event != 'reminder':
                raise TimerNotFound(timer.id)
            if timer.args[0] != interaction.user.id:
                raise TimerNotFound(timer.id)
            await timer.delete(bot)
            await interaction.followup.send(f'{bot.done_emoji} Okay, I deleted that reminder.')
        except TimerNotFound as error:
            await interaction.followup.send(f"I couldn't find a reminder with ID {error.id}.")

    @slash_reminder.command(name='list')
    async def slash_remind_list(self, interaction: discord.Interaction[DuckBot]) -> None:
        """Lists all of your reminders."""
        bot: DuckBot = interaction.client

        await interaction.response.defer(ephemeral=True)

        timers = await bot.pool.fetch(
            """
            SELECT id, expires, (extra->'args'->2) AS reason FROM timers
            WHERE event = 'reminder' AND (extra->'args'->0)::bigint = $1
            ORDER BY expires
        """,
            interaction.user.id,
        )

        if not timers:
            await interaction.followup.send("You have no upcoming reminders.")
            return

        embed = discord.Embed(title="Upcoming reminders", color=discord.Color.blurple())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

        for index, (r_id, expires, reason) in enumerate(timers):
            if index > 9:
                embed.set_footer(text=f"(... and {len(timers) - index} more)")
                break

            try:
                relative = discord.utils.format_dt(expires, 'R')
            except Exception as e:
                relative = 'in a long time...'
                logging.debug(f'Failed to format relative time: {expires} {repr(expires)}', exc_info=e)

            name = f"{r_id}: {relative}"
            value = reason if len(reason) < 1024 else reason[:1021] + '...'

            if (len(embed) + len(name) + len(value)) > 5900:
                embed.set_footer(text=f"(... and {len(timers) - index} more)")
                break

            embed.add_field(name=name, value=value, inline=False)
        else:
            embed.set_footer(text=f"(Showing all {len(timers)} reminders)")

        await interaction.followup.send(embed=embed)

import logging

import discord
from discord import app_commands

from bot import DuckBot
from utils import DuckCog, UserFriendlyTime, TimerNotFound, shorten, human_timedelta


class ApplicationReminders(DuckCog):
    """Reminds the user of something"""

    slash_reminder = app_commands.Group(name='reminder', description='Reminds the user of something')

    @slash_reminder.command(name='add')
    async def slash_remind_add(
        self,
        interaction: discord.Interaction[DuckBot],
        when: UserFriendlyTime(default=False),  # type: ignore
        what: str,
    ) -> None:
        """Reminds you of something in the future.

        Parameters
        ----------
        when: UserFriendlyTime
            When should I remind you? E.g. "Tomorrow", "1 day", "next Monday"
        what: str
            A description or note about this reminder.
        """
        bot: DuckBot = interaction.client

        if when.arg:
            await interaction.response.send_message("Could not parse time", ephemeral=True)
            return

        await interaction.response.defer()
        original = await interaction.original_response()

        await bot.create_timer(
            when.dt,
            'reminder',
            interaction.user.id,
            interaction.channel_id,
            what,
            message_id=original.id,
            precise=False,
        )
        await interaction.followup.send(f"Alright, {discord.utils.format_dt(when.dt, 'R')}: {what}")

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
            await interaction.followup.send(
                shorten(f'{bot.done_emoji} Okay, I deleted reminder with ID {timer.id}: {timer.args[2]}')
            )
        except TimerNotFound as error:
            await interaction.followup.send(f"I couldn't find a reminder with ID {error.id}.")

    @slash_remind_delete.autocomplete('id')
    async def autocomplete_slash_remind_delete_id(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        if current.isdigit():
            timers = await self.bot.pool.fetch(
                """
                SELECT id, expires, (extra->'args'->2) AS reason FROM timers
                WHERE event = 'reminder' AND (extra->'args'->0)::bigint = $1
                ORDER BY similarity(id::TEXT, $2) DESC, expires LIMIT 25
            """,
                interaction.user.id,
                current,
            )
        elif current:
            timers = await self.bot.pool.fetch(
                """
                SELECT id, expires, (extra->'args'->2) AS reason FROM timers
                WHERE event = 'reminder' AND (extra->'args'->0)::bigint = $1
                ORDER BY similarity(reason, $2) DESC, expires LIMIT 25
            """,
                interaction.user.id,
                current,
            )
        else:

            timers = await self.bot.pool.fetch(
                """
                SELECT id, expires, (extra->'args'->2) AS reason FROM timers
                WHERE event = 'reminder' AND (extra->'args'->0)::bigint = $1
                ORDER BY expires LIMIT 25
            """,
                interaction.user.id,
            )

        return [
            app_commands.Choice(
                name=shorten(f"id: {t['id']} — in {human_timedelta(t['expires'], brief=True)} — {t['reason']}", length=100),
                value=t['id'],
            )
            for t in timers
        ]

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

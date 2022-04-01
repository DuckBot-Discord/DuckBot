import datetime
import logging
import re

import discord
from discord.ext.commands import clean_content

from utils import DuckCog, UserFriendlyTime, TimerNotFound
from bot import DuckBot
from discord import app_commands


class clean_c(clean_content):
    async def convert(self, interaction: discord.Interaction, argument: str) -> str:
        msg = interaction.message

        if interaction.guild:

            def resolve_member(id: int) -> str:
                m = discord.utils.get(msg.mentions, id=id) or interaction.guild.get_member(id)
                return f'@{m.display_name if self.use_nicknames else m.name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                r = discord.utils.get(msg.role_mentions, id=id) or interaction.guild.get_role(id)
                return f'@{r.name}' if r else '@deleted-role'

        else:

            def resolve_member(id: int) -> str:
                m = discord.utils.get(msg.mentions, id=id) or interaction.client.get_user(id)
                return f'@{m.name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                return '@deleted-role'

        if self.fix_channel_mentions and interaction.guild:

            def resolve_channel(id: int) -> str:
                c = interaction.guild.get_channel(id)  # type: ignore
                return f'#{c.name}' if c else '#deleted-channel'

        else:

            def resolve_channel(id: int) -> str:
                return f'<#{id}>'

        transforms = {
            '@': resolve_member,
            '@!': resolve_member,
            '#': resolve_channel,
            '@&': resolve_role,
        }

        def repl(match: re.Match) -> str:
            type = match[1]
            id = int(match[2])
            transformed = transforms[type](id)
            return transformed

        result = re.sub(r'<(@[!&]?|#)([0-9]{15,20})>', repl, argument)
        if self.escape_markdown:
            result = discord.utils.escape_markdown(result)
        elif self.remove_markdown:
            result = discord.utils.remove_markdown(result)

        # Completely ensure no mentions escape:
        return discord.utils.escape_mentions(result)


class AppRemind(app_commands.Group, name='reminder'):
    """ Reminds the user of something """

    @app_commands.command(name='add')
    @app_commands.describe(
        when='When and what to remind you of. Example: "in 10 days do this", "next monday do that."'
    )
    async def remind_add(
            self,
            interaction: discord.Interaction,
            when: str,
    ) -> None:
        """Reminds you of something in the future."""
        bot: DuckBot = interaction.client  # type: ignore
        converter = UserFriendlyTime(converter=clean_c(), default='...')
        when = await converter.convert(interaction, when)

        await interaction.response.defer()
        original = await interaction.original_message()

        timer = await bot.create_timer(
            when.dt,
            'reminder',

            interaction.user.id,
            interaction.channel.id,
            when.arg,

            message_id=original.id,
            precise=False
        )
        await interaction.followup.send(f"Alright, {discord.utils.format_dt(when.dt, 'R')}: {when.arg}")

    @app_commands.command(name='delete')
    @app_commands.describe(id='The ID of the reminder you want to delete.')
    async def remind_delete(self, interaction: discord.Interaction, id: int) -> None:
        """Deletes one fo your reminders."""
        await interaction.response.defer(ephemeral=True)
        bot: DuckBot = interaction.client  # type: ignore
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

    @app_commands.command(name='list')
    async def list(self, interaction: discord.Interaction) -> None:
        """Lists all of your reminders."""
        bot: DuckBot = interaction.client  # type: ignore

        await interaction.response.defer(ephemeral=True)

        timers = await bot.pool.fetch("""
            SELECT id, expires, (extra->'args'->2) AS reason FROM timers
            WHERE event = 'reminder' AND (extra->'args'->0)::bigint = $1
            ORDER BY expires
        """, interaction.user.id)

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


class ApplicationReminders(DuckCog):
    def __init__(self, bot: DuckBot):
        super().__init__(bot)
        self.bot.tree.add_command(AppRemind())

    def cog_unload(self) -> None:
        self.bot.tree.remove_command('reminder')

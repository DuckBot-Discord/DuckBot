from __future__ import annotations

from typing import Union, TYPE_CHECKING
from logging import getLogger

import discord
from discord import app_commands
from discord.ext import commands

import errors
from helpers.time_formats import human_join

from ._base import ConfigBase
from .views.events import CreateEvent


if TYPE_CHECKING:
    from bot import DuckBot


default_message = "***{user}** just joined **{server}**! Welcome."


log = getLogger(__name__)


def make_ordinal(n):
    """
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    """
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return str(n) + suffix


class SilentError(errors.NoHideout):
    pass


Q_T = Union[str, discord.Embed]


class ValidPlaceholdersConverter(commands.Converter):

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if len(argument) > 1000:
            raise commands.BadArgument(f"That welcome message is too long! ({len(argument)}/1000)")

        to_format = {
            'server': '...',
            'user': '...',
            'full-user': '...',
            'user-mention': '...',
            'count': '...',
            'ordinal': '...',
            'code': '...',
            'full-code': '...',
            'full-url': '...',
            'inviter': '...',
            'full-inviter': '...',
            'inviter-mention': '...',
        }

        try:
            argument.format(**to_format)
        except KeyError as e:
            ph = human_join(to_format.keys(), final='and')
            raise commands.BadArgument(f'Unrecognised placeholder: `{e}`.\nAvailable placeholders: {ph}')
        else:
            return argument


class Welcome(ConfigBase):
    @commands.command()
    async def welcome(self, ctx):
        await ctx.send("Welcome messages are now managed via `/events`")

    event = app_commands.Group(name='event')

    @event.command(name='create')
    @app_commands.choices(
        when=[
            # Different events that may happen in a server
            app_commands.Choice(name="user joins server", value=0),
            app_commands.Choice(name="user leaves server", value=1),
            app_commands.Choice(name="user obtains role or roles", value=2),
            app_commands.Choice(name="user loses role or roles", value=3),
            app_commands.Choice(name="other event", value=-1),
        ]
    )
    async def event_create(self, interaction: discord.Interaction[DuckBot], when: app_commands.Choice[int]):
        if when.value == -1:
            await interaction.response.send_message(
                "Didn't find an event you like? Join our support server, which you can "
                "find in the help command, and create a post in the suggestions channel."
                "\n-# If you can't find the channel, [click here](https://discord.com/"
                "channels/774561547930304536/1077034825229291590) after joining the server.",
                ephemeral=True,
            )

    @event.command(name='create')
    async def event_edit(self, interaction: discord.Interaction[DuckBot]): ...

    @commands.Cog.listener()
    async def on_invite_update(self, member: discord.Member, invite: discord.Invite | None):
        try:
            channel = await self.bot.get_welcome_channel(member)
        except errors.NoWelcomeChannel:
            return
        message: str = await self.bot.db.fetchval("SELECT welcome_message FROM guilds WHERE guild_id = $1", member.guild.id)
        message = message or default_message

        to_format = {
            'server': str(member.guild),
            'user': str(member.display_name),
            'full-user': str(member),
            'user-mention': str(member.mention),
            'count': str(member.guild.member_count),
            'ordinal': str(make_ordinal(member.guild.member_count)),
            'code': (str(invite.code) if invite else 'N/A'),
            'full-code': (f"discord.gg/{invite.code}" if invite else 'N/A'),
            'full-url': (str(invite) if invite else 'N/A'),
            'inviter': str(((invite.inviter.display_name) or invite.inviter.name) if invite and invite.inviter else 'N/A'),
            'full-inviter': str(invite.inviter if invite and invite.inviter else 'N/A'),
            'inviter-mention': str(invite.inviter.mention if invite and invite.inviter else 'N/A'),
        }

        try:
            await channel.send(
                message.format(**to_format), allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False)
            )
        except discord.HTTPException:
            log.info('Could not send welcome message to guild %s: %s', member.guild.id, to_format, exc_info=False)

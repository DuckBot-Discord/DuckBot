from __future__ import annotations

import typing
from typing import Union

import discord
from discord import Permissions, PermissionOverwrite, Member, Role

from utils import DuckContext, DuckCog, DeleteButton, group, View
from utils.types import constants
from bot import DuckBot

# These are just for making it look nicer,
# I know it looks ugly, but I prefer it.

message_perms_text = """```
{send_messages} Send Messages
{manage_messages} Manage Messages
{read_message_history} Read Message History
{attach_files} Attach Files
{embed_links} Embed Links
{add_reactions} Add Reactions
{external_emojis} Use External Emoji
{external_stickers} Use External Stickers
{send_messages_in_threads} Send Messages in Threads
{send_tts_messages} Use `/tts`
```"""

mod_perms_text = """```
{administrator} Administrator
{kick_members} Kick Members
{ban_members} Ban Members
{manage_roles} Manage Roles
{manage_guild} Manage Server
{manage_expressions} Manage Expressions
{manage_events} Manage Events
{manage_threads} Manage Threads
{manage_channels} Manage Channels
{manage_webhooks} Manage Webhooks
{manage_nicknames} Manage Nicknames
{moderate_members} Timeout Members
{view_guild_insights} Server Insights
{view_audit_log} View Audit Log
```"""

normal_perms_text = """```
{read_messages} View Channels
{change_nickname} Change Own Nickname
{create_public_threads} Create Public Threads
{create_private_threads} Create Private Threads
{mention_everyone} Mention Everyone and Roles
```"""

voice_perms_text = """```
{connect} Connect
{speak} Speak
{stream} Stream
{priority_speaker} Priority Speaker
{mute_members} Mute Members
{deafen_members} Deafen Members
{move_members} Move Members
{request_to_speak} Request to Speak
{use_voice_activation} Use Voice Activation
{use_embedded_activities} Use VC Games
```"""


def get_type(entity: typing.Any) -> type:
    if isinstance(entity, SimpleOverwrite):
        return type(entity.entity)
    return type(entity)


class PermsEmbed(discord.Embed):
    def __init__(
        self,
        entity: Union[Member, Role, SimpleOverwrite],
        permissions: Union[Permissions, PermissionOverwrite],
        channel: discord.abc.GuildChannel | None = None,
    ):
        descriptor = 'Permissions' if isinstance(permissions, discord.Permissions) else 'Overwrites'

        extra = ""
        if channel:
            extra = f" in {channel.mention}"

        super().__init__(
            description=f"{descriptor} for {entity.mention} {extra}",
            color=entity.color,
        )
        formatted = {p: constants.SQUARE_TICKS.get(v) for p, v in permissions}
        self.add_field(name='Message Permissions', value=message_perms_text.format(**formatted), inline=False)
        self.add_field(name='Moderator Permissions', value=mod_perms_text.format(**formatted), inline=False)
        self.add_field(name='Normal Permissions', value=normal_perms_text.format(**formatted), inline=False)
        self.add_field(name='Voice Permissions', value=voice_perms_text.format(**formatted), inline=False)


class SimpleOverwrite:
    def __init__(
        self, entity: typing.Union[discord.Member, discord.Role, discord.Object], overwrite: discord.PermissionOverwrite, pos
    ):
        self.entity = entity
        self.overwrite = overwrite
        self.position = pos

    @property
    def mention(self):
        entity = self.entity
        if isinstance(entity, discord.Object):
            return f"unknown {entity.id}"
        return entity.mention

    @property
    def permissions(self):
        return self.overwrite

    @property
    def id(self):
        return self.entity.id

    @property
    def name(self):
        return str(self.entity)

    @property
    def emoji(self):
        if isinstance(self.entity, discord.Role):
            return constants.ROLES_ICON
        else:
            return '\N{BUST IN SILHOUETTE}'

    @property
    def color(self):
        return getattr(self.entity, 'color', discord.Color.default())

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<SimpleOverwrite id={self.id}>"


class GuildPermsViewer(View):
    """
    A view that shows the permissions for an object.
    """

    def __init__(
        self,
        ctx: DuckContext,
    ):
        super().__init__(bot=ctx.bot, author=ctx.author, disable_on_timeout=True)
        self.ctx = ctx

    @discord.ui.select(cls=discord.ui.RoleSelect)
    async def select_role(self, interaction: discord.Interaction[DuckBot], select: discord.ui.RoleSelect):
        role = select.values[0]
        embed = PermsEmbed(role, role.permissions)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Exit', style=discord.ButtonStyle.red)
    async def exit(self, interaction: discord.Interaction[DuckBot], button: discord.ui.Button):
        self.stop()
        await interaction.response.defer()
        await interaction.delete_original_response()
        try:
            await self.ctx.message.add_reaction(self.ctx.bot.done_emoji)
        except:
            pass

    @classmethod
    async def start(cls, ctx: DuckContext):
        """
        Starts the viewer using the `ctx.guild`'s permissions.

        Parameters
        ----------
        ctx: DuckContext
            The context to use.
        """
        new = cls(ctx)
        message = await ctx.send(view=new)
        new.message = message
        new.ctx.bot.views.add(new)


class OverwritesViewer(View):
    def __init__(self, ctx: DuckContext, overwrites: list[SimpleOverwrite]):
        super().__init__(bot=ctx.bot, author=ctx.author, disable_on_timeout=True)
        self.ctx = ctx
        self.overwrites = overwrites
        self.current_page: int = 0
        self.per_page = 10

    def update_select_options(self):
        range = self.overwrites[self.current_page * self.per_page : (self.current_page + 1) * self.per_page]
        self.select_overwrite.options = [
            discord.SelectOption(label=over.name, emoji=over.emoji, value=over.position) for over in range
        ]

    @discord.ui.select(cls=discord.ui.Select)
    async def select_overwrite(self, interaction: discord.Interaction, select: discord.ui.Select):
        overwrite = self.overwrites[int(select.values[0])]
        embed = PermsEmbed(overwrite, overwrite.permissions)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label='<')
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.overwrites), max(0, self.current_page - 1))
        self.update_select_options()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='>')
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.overwrites), max(0, self.current_page + 1))
        self.update_select_options()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Exit', style=discord.ButtonStyle.red)
    async def exit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.defer()
        await interaction.delete_original_response()
        try:
            await self.ctx.message.add_reaction(self.ctx.bot.done_emoji)
        except:
            pass

    @classmethod
    async def start(cls, ctx: DuckContext, channel: discord.abc.GuildChannel):
        overwrites = [
            SimpleOverwrite(entry, overwrite, pos)
            for pos, (entry, overwrite) in enumerate(filter(lambda x: not x[1].is_empty(), channel.overwrites.items()))
        ]
        if not overwrites:
            await ctx.send(f"No permission overwrites found in this channel.")
            return

        new = cls(ctx, overwrites)
        new.update_select_options()
        message = await ctx.send(view=new)
        new.message = message


class PermsViewer(DuckCog):
    @group(hybrid=True, fallback='for', invoke_without_command=True)
    async def permissions(self, ctx: DuckContext, *, entity: discord.Role | discord.Member) -> None:
        """Shows the global permissions of a user or role.

        Parameters
        ----------
        entity: Role | Member
            The user or role that will be checked.
        """

        if isinstance(entity, discord.Role):
            perms = entity.permissions
        else:
            perms = entity.guild_permissions

        embed = PermsEmbed(entity=entity, permissions=perms)
        await DeleteButton.send_to(ctx, embed=embed, author=ctx.author)

    @permissions.command(name='in')
    async def permissions_in(
        self, ctx: DuckContext, channel: discord.abc.GuildChannel, entity: discord.Role | discord.Member
    ):
        """Shows a role or user's permissions for a channel.

        This shows the effective permissions of a user in a channel, which take into consideration both channel-specific (user/role) and global (role) permissions for all roles the user has.

        Parameters
        ----------
        channel: GuildChannel
            The channel to get permission information from.
        entity:
            The user or role that will be checked.
        """
        perms = channel.permissions_for(entity)
        embed = PermsEmbed(entity=entity, permissions=perms, channel=channel)
        await DeleteButton.send_to(ctx, embed=embed, author=ctx.author)

    @permissions.command(name='all')
    async def permissions_all(self, ctx: DuckContext, *, entity: discord.abc.GuildChannel | None):
        """Shows all the server or a channel's permissions and overwrites.

        Parameters
        ----------
        channel: GuildChannel
            The channel to get permission information from.
        """
        if entity:
            return await OverwritesViewer.start(ctx, entity)

        await GuildPermsViewer.start(ctx)

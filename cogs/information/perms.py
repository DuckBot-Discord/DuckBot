import contextlib
import typing
from typing import Union

import discord
from discord import Permissions, PermissionOverwrite, Member, Role
from discord.ext import commands

from utils import DuckContext, DuckCog, constants, DeleteButton, command
from discord.utils import as_chunks

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
{manage_emojis} Manage Emojis
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
            entity: Union[Member, Role],
            permissions: Union[Permissions, PermissionOverwrite],
    ):
        sym = '@' if isinstance(entity, (discord.Role, discord.abc.User)) else '#'
        word = 'Permissions' if isinstance(permissions, discord.Permissions) else 'Overwrites'
        super().__init__(
            title=f"{word} for {sym}{entity}",
            color=entity.color,
        )
        formatted = {p: constants.SQUARE_TICKS.get(v) for p, v in permissions}
        self.add_field(name='Message Permissions', value=message_perms_text.format(**formatted), inline=False)
        self.add_field(name='Moderator Permissions', value=mod_perms_text.format(**formatted), inline=False)
        self.add_field(name='Normal Permissions', value=normal_perms_text.format(**formatted), inline=False)
        self.add_field(name='Voice Permissions', value=voice_perms_text.format(**formatted), inline=False)


class SimpleOverwrite:
    def __init__(
            self,
            entity: typing.Union[discord.Member, discord.Role],
            overwrite: discord.PermissionOverwrite,
            pos
    ):
        self.entity = entity
        self.overwrite = overwrite
        self.position = pos

    @property
    def permissions(self):
        return self.overwrite

    @property
    def id(self):
        return self.entity.id

    @property
    def color(self):
        return self.entity.color

    def __str__(self):
        return f"{self.entity}"

    def __repr__(self):
        return f"<SimpleOverwrite id={self.id}>"

class GuildPermsViewer(discord.ui.View):
    """
    A view that shows the permissions for an object.
    """
    def __init__(self, ctx: DuckContext, message: discord.Message,
                 chunks: typing.List[typing.List[typing.Union[discord.Role, SimpleOverwrite]]]):
        super().__init__()
        self.ctx = ctx
        self.guild = ctx.guild
        self.message = message
        self.current_page = 0
        self.chunks = chunks
        self.max_pages = len(chunks) - 1
        self.current_role: typing.Optional[discord.Role, SimpleOverwrite] = None

    def get_options_from_chunk(self, index: int):
        roles = self.chunks[index]
        return [
            discord.SelectOption(
                label=f"{r.position + 1}) {get_type(r).__name__} @{r}",
                value=str(r.id)
            )
            for r in roles
        ]

    @discord.ui.select()
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.Select):
        role_id: int = int(select.values[0])
        role = discord.utils.get(self.chunks[self.current_page], id=role_id)
        if not role:
            return await interaction.response.send_message('Entity not found...', ephemeral=True)
        embed = PermsEmbed(role, role.permissions)
        select.placeholder = f"Viewing @{role} (page {self.current_page + 1}/{self.max_pages + 1})"
        self.current_role = role
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='<')
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_components()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='>')
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.max_pages, self.current_page + 1)
        self.update_components()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Exit', style=discord.ButtonStyle.red)
    async def exit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.message.delete()
        with contextlib.suppress(discord.HTTPException):
            await self.ctx.message.add_reaction(self.ctx.bot.done_emoji)

    def update_components(self):
        self.next_page.disabled = self.current_page >= self.max_pages
        self.previous_page.disabled = self.current_page <= 0
        self.select_role.options = self.get_options_from_chunk(self.current_page)
        self.select_role.placeholder = f"Viewing @{self.current_role or 'no role'} " \
                                       f"(page {self.current_page + 1}/{self.max_pages + 1})"

    @classmethod
    async def start(cls, ctx: DuckContext):
        """
        Starts the viewer using the `ctx.guild`'s permissions.

        Parameters
        ----------
        ctx: DuckContext
            The context to use.
        """
        message = await ctx.send('Loading...')
        chunks = [chunk for chunk in as_chunks(ctx.guild.roles, 10)]
        new = cls(ctx, message, chunks)
        new.update_components()
        await message.edit(content=None, view=new)
        new.ctx.bot.views.add(new)

    @classmethod
    async def from_overwrites(
            cls,
            ctx: DuckContext,
            overwrites: typing.Dict[typing.Union[discord.Member, discord.Role], discord.PermissionOverwrite]
    ) -> None:
        """|coro|

        Starts a Permissions Viewer from a channel's overwrites.

        Parameters
        ----------
        ctx: DuckContext
            The context of the command.
        overwrites: Dict[Union[discord.Member, discord.Role], discord.PermissionOverwrite]
            The overwrites to view.
        """
        message = await ctx.send('Loading...')
        chunks = [[SimpleOverwrite(k, v, i) for i, (k, v) in enumerate(chunk)] for chunk in as_chunks(overwrites.items(), 10)]
        new = cls(ctx, message, chunks)
        new.update_components()
        await message.edit(content=None, view=new)
        new.ctx.bot.views.add(new)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self) -> None:
        self.ctx.bot.views.discard(self)
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    def stop(self) -> None:
        self.ctx.bot.views.discard(self)
        super().stop()

class PermsViewer(DuckCog):

    @command()
    async def perms(
            self,
            ctx: DuckContext,
            *,
            entity: typing.Union[discord.abc.GuildChannel, discord.Role, discord.Member] = None
    ) -> None:
        """|coro|

        Shows the permissions of a channel or user.
        """
        if entity is None:
            await GuildPermsViewer.start(ctx)
        else:
            if isinstance(entity, discord.abc.GuildChannel):
                await GuildPermsViewer.from_overwrites(ctx, entity.overwrites)
                return

            elif isinstance(entity, discord.Role):
                perms = entity.permissions
            else:
                perms = entity.guild_permissions

            embed = PermsEmbed(entity=entity, permissions=perms)
            await DeleteButton.to_destination(ctx, embed=embed, author=ctx.author)


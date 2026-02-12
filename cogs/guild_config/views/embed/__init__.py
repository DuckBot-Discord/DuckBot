from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Optional, TypeAlias, Self

import discord
from discord import ButtonStyle

from helpers.constants import EDIT_NICKNAME

from .modals import (
    AddFieldModal,
    EditAuthorModal,
    EditEmbedModal,
    EditFieldModal,
    EditFooterModal,
    EditWithModalButton,
)

if TYPE_CHECKING:
    from bot import DuckBot

    BotInteraction: TypeAlias = discord.Interaction[DuckBot]


class Embed(discord.Embed):
    def __bool__(self) -> bool:
        return any(
            (
                self.title,
                self.url,
                self.description,
                self.fields,
                self.timestamp,
                self.author,
                self.thumbnail,
                self.footer,
                self.image,
            )
        )


class UndoView(discord.ui.View):
    def __init__(self, parent: 'EmbedEditor'):
        self.parent = parent
        self.interaction_check = self.parent.interaction_check  # type: ignore
        super().__init__(timeout=10)

    @discord.ui.button(label='Undo deletion.')
    async def undo(self, interaction: BotInteraction, button: discord.ui.Button[UndoView]):
        self.stop()
        await interaction.channel.send(view=self.parent, embed=self.parent.current_embed)  # type: ignore
        await interaction.response.edit_message(view=None)
        await interaction.delete_original_response()

    async def on_timeout(self) -> None:
        self.parent.stop()


class DeleteButton(discord.ui.Button['EmbedEditor']):
    async def callback(self, interaction: BotInteraction):
        if interaction.message:
            await interaction.message.delete()
        await interaction.response.send_message(
            'Done!\n*This message goes away in 10 seconds*\n*You can use this to recover your progress.*',
            view=UndoView(self.view),  # type: ignore
            delete_after=10,
            ephemeral=True,
        )


class FieldSelectorView(discord.ui.View):
    def __init_subclass__(cls, label: str, **kwargs):
        cls.label = label
        super().__init_subclass__(**kwargs)

    def __init__(self, parent: EmbedEditor):
        self.parent = parent
        self.interaction_check = self.parent.interaction_check  # type: ignore
        super().__init__(timeout=300)
        self.pick_field.placeholder = self.label
        self.update_options()

    def update_options(self):
        self.pick_field.options = []
        for i, field in enumerate(self.parent.embed.fields):
            self.pick_field.add_option(label=f"{i + 1}) {(field.name or '')[0:95]}", value=str(i))

    @discord.ui.select()
    async def pick_field(self, interaction: BotInteraction, select: discord.ui.Select):
        await self.actual_logic(interaction, select)

    @discord.ui.button(label='Go back')
    async def cancel(self, interaction: BotInteraction, button: discord.ui.Button[Self]):
        await interaction.response.edit_message(view=self.parent)
        self.stop()

    async def actual_logic(self, interaction: BotInteraction, select: discord.ui.Select[Self]) -> None:
        raise NotImplementedError('Child classes must overwrite this method.')


class DeleteFieldWithSelect(FieldSelectorView, label='Select a field to delete.'):
    async def actual_logic(self, interaction: BotInteraction, select: discord.ui.Select[Self]):
        index = int(select.values[0])
        self.parent.embed.remove_field(index)
        await self.parent.update_buttons()
        await interaction.response.edit_message(embed=self.parent.current_embed, view=self.parent)
        self.stop()


class EditFieldSelect(FieldSelectorView, label='Select a field to edit.'):
    async def actual_logic(self, interaction: BotInteraction, select: discord.ui.Select[Self]):
        index = int(select.values[0])
        self.parent.timeout = 600
        await interaction.response.send_modal(EditFieldModal(self.parent, index))


class SendToView(discord.ui.View):
    def __init__(self, *, parent: EmbedEditor):
        self.parent = parent
        self.interaction_check = self.parent.interaction_check  # type: ignore
        super().__init__(timeout=300)

    async def send_to(self, interaction: BotInteraction, channel_id: int):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return await interaction.followup.send(
                'for some reason, discord thinks you are not a member of this server...', ephemeral=True
            )

        channel = interaction.guild.get_channel_or_thread(channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return await interaction.followup.send('That channel does not exist... somehow.', ephemeral=True)
        if not channel.permissions_for(interaction.user).send_messages:
            return await interaction.followup.send(f'You cannot send messages in {channel.mention}.', ephemeral=True)
        if not channel.permissions_for(interaction.guild.me).send_messages:
            return await interaction.followup.send(f'I cannot send messages in {channel.mention}.', ephemeral=True)

        await channel.send(embed=self.parent.embed)
        await interaction.delete_original_response()
        await interaction.followup.send('Sent!', ephemeral=True)
        self.stop()

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[
            discord.ChannelType.text,
            discord.ChannelType.news,
            discord.ChannelType.voice,
            discord.ChannelType.private_thread,
            discord.ChannelType.public_thread,
        ],
        placeholder="Pick a channel to send this embed to.",
    )
    async def pick_a_channel(self, interaction: BotInteraction, select: discord.ui.ChannelSelect[SendToView]):
        await self.send_to(interaction, select.values[0].id)

    @discord.ui.button(label="Send to current channel")
    async def to_current_channel(self, interaction: BotInteraction, button: discord.ui.Button):
        await self.send_to(interaction, interaction.channel.id if interaction.channel else 0)

    @discord.ui.button(label='Go Back')
    async def stop_pages(self, interaction: BotInteraction, button: discord.ui.Button[SendToView]):
        """stops the pagination session."""
        await interaction.response.edit_message(embed=self.parent.current_embed, view=self.parent)
        self.stop()

    async def on_timeout(self) -> None:
        if self.parent.message:
            try:
                await self.parent.message.edit(view=self.parent)
            except discord.NotFound:
                pass


class EmbedEditor(discord.ui.View):
    def __init__(self, owner: discord.Member, *, timeout: Optional[float] = 600):
        self.owner: discord.Member = owner
        self.embed = Embed()
        self.showing_help = False
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=timeout)
        self.clear_items()
        self.add_items()

    @staticmethod
    def shorten(_embed: discord.Embed):
        embed = Embed.from_dict(deepcopy(_embed.to_dict()))
        while len(embed) > 6000 and embed.fields:
            embed.remove_field(-1)
        if len(embed) > 6000 and embed.description:
            embed.description = embed.description[: (len(embed.description) - (len(embed) - 6000))]
        return embed

    @property
    def current_embed(self) -> discord.Embed:
        if self.showing_help:
            return self.help_embed()
        if self.embed:
            if len(self.embed) < 6000:
                return self.embed
            else:
                return self.shorten(self.embed)
        return self.help_embed()

    async def interaction_check(self, interaction: BotInteraction, /):
        if interaction.user == self.owner:
            return True
        await interaction.response.send_message('This is not your menu.', ephemeral=True)

    def add_items(self):
        """This is done this way because if not, it would get too cluttered."""
        # Row 1
        self.add_item(discord.ui.Button(label='Edit:', style=ButtonStyle.blurple, disabled=True))
        self.add_item(EditWithModalButton(EditEmbedModal, label='Embed', style=ButtonStyle.blurple))
        self.add_item(EditWithModalButton(EditAuthorModal, row=0, label='Author', style=ButtonStyle.blurple))
        self.add_item(EditWithModalButton(EditFooterModal, row=0, label='Footer', style=ButtonStyle.blurple))
        # Row 2
        self.add_item(discord.ui.Button(row=1, label='Fields:', disabled=True, style=ButtonStyle.blurple))
        self.add_fields = EditWithModalButton(AddFieldModal, row=1, emoji='\N{HEAVY PLUS SIGN}', style=ButtonStyle.green)
        self.add_item(self.add_fields)
        self.add_item(self.remove_fields)
        self.add_item(self.edit_fields)
        # Row 3
        self.add_item(self.done)
        self.add_item(DeleteButton(emoji='\N{WASTEBASKET}', style=ButtonStyle.red))
        self.add_item(self.help_page)
        # Row 4
        self.character_count: discord.ui.Button[Self] = discord.ui.Button(row=3, label='0/6,000 Characters', disabled=True)
        self.add_item(self.character_count)
        self.fields_count: discord.ui.Button[Self] = discord.ui.Button(row=3, label='0/25 Total Fields', disabled=True)
        self.add_item(self.fields_count)

    async def update_buttons(self):
        fields = len(self.embed.fields)
        self.add_fields.disabled = fields > 25
        self.remove_fields.disabled = not fields
        self.edit_fields.disabled = not fields
        self.help_page.disabled = not self.embed
        if len(self.embed) <= 6000:
            self.done.style = ButtonStyle.green
        else:
            self.done.style = ButtonStyle.red

        self.character_count.label = f"{len(self.embed)}/6,000 Characters"
        self.fields_count.label = f"{len(self.embed.fields)}/25 Total Fields"

        if self.showing_help:
            self.help_page.label = 'Show My Embed'
        else:
            self.help_page.label = 'Show Help Page'

    def help_embed(self) -> Embed:
        embed = Embed(
            title='How do I use this? [title]',
            color=discord.Colour.blurple(),
            description=(
                "Use the below buttons to add things to the embed. "
                "Once you are done, you will be able to send this to any channel "
                "or begin configuring an event, which will enable this embed to "
                "be sent to a selected channel when a condition is met."
                "\n-# Note that some ***__discord formatting__*** features do NOT "
                "in every field. Thanks discord!"
                "\n-# Btw this \"main\" field is called the [description]. We use "
                "[square brackets] in in this help page, so you can know the name of "
                "each field."
            ),
        )
        embed.add_field(
            name='This is a [field]. Specifically its [name].',
            value=(
                'and this is the [value]. This field is [in-line]. You can have '
                'up to **three** different fields in one line.'
            ),
        )
        embed.add_field(
            name='Here is another [field]', value='As you can see, there are side by side as they both are [in-line].'
        )
        embed.add_field(
            name='Here is another field, but not in-line.',
            value='Note that fields can have up to 256 characters in the name, and up to 1,024 characters in the value!',
            inline=False,
        )
        embed.add_field(
            name='Placeholders for adding things to an event.',
            value=(
                'If you plan to add this embed to an event, then there are some placeholders that are available. '
                'They will be listed here once they are all completed.'  # TODO
            ),
        )
        embed.set_author(
            name='DuckBot Embed Creator! [author]',
            icon_url='https://cdn.duck-bot.com/file/AVATAR',
        )
        embed.set_image(url='https://cdn.duck-bot.com/file/IMAGE')
        embed.set_thumbnail(url='https://cdn.duck-bot.com/file/THUMBNAIL')
        footer_text = "This is the footer, which like the author, does not support markdown."
        if not self.embed and not self.showing_help:
            footer_text += '\n💢This embed will be replaced by yours once it has characters💢'
        embed.set_footer(icon_url='https://cdn.duck-bot.com/file/ICON', text=footer_text)
        return embed

    @discord.ui.button(row=1, emoji='\N{HEAVY MINUS SIGN}', style=ButtonStyle.red, disabled=True)
    async def remove_fields(self, interaction: BotInteraction, button: discord.ui.Button[Self]):
        await interaction.response.edit_message(view=DeleteFieldWithSelect(self))

    @discord.ui.button(row=1, emoji=EDIT_NICKNAME, disabled=True, style=ButtonStyle.blurple)
    async def edit_fields(self, interaction: BotInteraction, button: discord.ui.Button[Self]):
        await interaction.response.edit_message(view=EditFieldSelect(self))

    @discord.ui.button(label='Send To', row=2, style=ButtonStyle.red)
    async def done(self, interaction: BotInteraction, button: discord.ui.Button[Self]):
        if not self.embed:
            return await interaction.response.send_message('Your embed is empty!', ephemeral=True)
        elif len(self.embed) > 6000:
            return await interaction.response.send_message(
                'You have exceeded the embed character limit (6000)', ephemeral=True
            )
        await interaction.response.edit_message(view=SendToView(parent=self))

    @discord.ui.button(label='Show Help Page', row=2, disabled=True)
    async def help_page(self, interaction: BotInteraction, button: discord.ui.Button[Self]):
        self.showing_help = not self.showing_help
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.current_embed, view=self)

    async def on_timeout(self) -> None:
        if self.message:
            if self.embed:
                await self.message.edit(view=None)
            else:
                await self.message.delete()

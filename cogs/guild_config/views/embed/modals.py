from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional, Type, Union, Self

import discord
from discord import ButtonStyle, Emoji, PartialEmoji

if TYPE_CHECKING:
    from . import EmbedEditor


URL_REGEX = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')


def to_boolean(argument: str) -> bool:
    lowered = argument.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'off'):
        return False
    else:
        raise InvalidModalField(f'{argument} is not a valid boolean value.')


class InvalidModalField(Exception): ...


class BaseModal(discord.ui.Modal):
    def __init__(self, parent_view: EmbedEditor) -> None:
        self.parent_view = parent_view
        self.update_defaults(parent_view.embed)
        super().__init__()

    def update_embed(self) -> None:
        raise NotImplementedError

    def update_defaults(self, embed: discord.Embed):
        return

    async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None:
        if isinstance(error, InvalidModalField):
            await self.parent_view.update_buttons()
            await interaction.response.edit_message(embed=self.parent_view.current_embed, view=self.parent_view)
            await interaction.followup.send(str(error), ephemeral=True)
            return
        await super().on_error(interaction, error)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        self.update_embed()
        await self.parent_view.update_buttons()
        await interaction.response.edit_message(embed=self.parent_view.current_embed, view=self.parent_view)


class EditWithModalButton(discord.ui.Button['EmbedEditor']):
    def __init__(
        self,
        modal: Type[BaseModal],
        /,
        *,
        style: ButtonStyle = ButtonStyle.secondary,
        label: Optional[str] = None,
        disabled: bool = False,
        emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
        row: Optional[int] = None,
    ):
        self.modal = modal
        super().__init__(style=style, label=label, disabled=disabled, emoji=emoji, row=row)

    async def callback(self, interaction: discord.Interaction):
        if not self.view:
            raise discord.DiscordException('No view was found attached to this modal.')
        await interaction.response.send_modal(self.modal(self.view))


class EditEmbedModal(BaseModal, title='Editing the embed:'):
    _title = discord.ui.TextInput[Self](
        label='Embed Title', placeholder='Leave any field empty to remove it', max_length=256, required=False
    )
    description = discord.ui.TextInput[Self](
        label='Embed Description',
        placeholder='Any text, up to 4,000 characters.\n\nEmbeds can have a shared total of 6,000 characters!',
        style=discord.TextStyle.long,
        required=False,
    )
    image = discord.ui.TextInput[Self](label='Embed Image URL', placeholder='Must be HTTP(S) format.', required=False)
    thumbnail = discord.ui.TextInput[Self](
        label='Thumbnail Image URL', placeholder='Must be HTTP(S) format.', required=False
    )
    color = discord.ui.TextInput[Self](
        label='Embed Color', placeholder='Hex [#FFFFFF] or RGB [rgb(num, num, num)] only', required=False
    )

    def update_defaults(self, embed: discord.Embed):
        self._title.default = embed.title
        self.description.default = embed.description
        self.image.default = embed.image.url
        self.thumbnail.default = embed.thumbnail.url
        if embed.color:
            self.color.default = str(embed.color)

    def update_embed(self):
        self.parent_view.embed.title = self._title.value.strip() or None
        self.parent_view.embed.description = self.description.value.strip() or None
        failed: list[str] = []
        if self.color.value:
            try:
                color = discord.Color.from_str(self.color.value)
                self.parent_view.embed.color = color
            except (ValueError, IndexError):
                failed.append('Invalid Color given!')
        else:
            self.parent_view.embed.color = None

        sti = self.image.value.strip()
        if URL_REGEX.fullmatch(sti):
            self.parent_view.embed.set_image(url=sti)
        elif sti:
            failed.append('Image URL did not match the http/https format')
        else:
            self.parent_view.embed.set_image(url=None)

        sti = self.thumbnail.value.strip()
        if URL_REGEX.fullmatch(sti):
            self.parent_view.embed.set_thumbnail(url=sti)
        elif sti:
            failed.append('Thumbnail URL did not match the http/https format')
        else:
            self.parent_view.embed.set_thumbnail(url=None)
        if failed:
            raise InvalidModalField('\n'.join(failed))


class EditAuthorModal(BaseModal, title='Editing the embed author:'):
    name = discord.ui.TextInput[Self](
        label='Author name', max_length=256, placeholder='Leave any field empty to remove it', required=False
    )
    url = discord.ui.TextInput[Self](label="Author URL", placeholder='Must be HTTP(S) format.', required=False)
    image = discord.ui.TextInput[Self](label='Author Icon URL', placeholder='Must be HTTP(S) format.', required=False)

    def update_defaults(self, embed: discord.Embed):
        self.name.default = embed.author.name
        self.url.default = embed.author.url
        self.image.default = embed.author.icon_url

    def update_embed(self):
        author = self.name.value.strip()
        if not author:
            self.parent_view.embed.remove_author()

        failed: list[str] = []

        image_url = None
        sti = self.image.value.strip()
        if URL_REGEX.fullmatch(sti):
            if not author:
                failed.append(
                    'Cannot add image. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            image_url = sti
        elif sti:
            if not author:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            failed.append('Image URL did not match the http/https format.')

        url = None
        sti = self.url.value.strip()
        if URL_REGEX.fullmatch(sti):
            if not author:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            url = sti
        elif sti:
            if not author:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            failed.append('URL did not match the http/https format.')

        if author:
            self.parent_view.embed.set_author(name=author, url=url, icon_url=image_url)

        if failed:
            raise InvalidModalField('\n'.join(failed))


class EditFooterModal(BaseModal, title='Editing the embed author:'):
    text = discord.ui.TextInput[Self](
        label='Footer text', max_length=256, placeholder='Leave any field empty to remove it', required=False
    )
    image = discord.ui.TextInput[Self](label='Footer icon URL', placeholder='Must be HTTP(S) format.', required=False)

    def update_defaults(self, embed: discord.Embed):
        self.text.default = embed.footer.text
        self.image.default = embed.footer.icon_url

    def update_embed(self):
        text = self.text.value.strip()
        if not text:
            self.parent_view.embed.remove_author()

        failed: list[str] = []

        image_url = None
        sti = self.image.value.strip()
        if URL_REGEX.fullmatch(sti):
            if not text:
                failed.append(
                    'Cannot add image. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            image_url = sti
        elif sti:
            if not text:
                failed.append(
                    'Cannot add url. NAME is required to add an author.\n(Leave all fields empty to remove author.)'
                )
            failed.append('Image URL did not match the http/https format.')

        if text:
            self.parent_view.embed.set_footer(text=text, icon_url=image_url)

        if failed:
            raise InvalidModalField('\n'.join(failed))


class AddFieldModal(BaseModal, title='Add a field'):
    name = discord.ui.TextInput[Self](label='Field Name', max_length=256)
    value = discord.ui.TextInput[Self](label='Field Value', max_length=1024, style=discord.TextStyle.paragraph)
    inline = discord.ui.TextInput[Self](
        label='Is inline?', placeholder='[ "Yes" | "No" ] (Default: Yes)', max_length=4, required=False
    )
    index = discord.ui.TextInput[Self](
        label='Index (where to place this field)',
        placeholder='Number between 1 and 25. Default: 25 (last)',
        max_length=2,
        required=False,
    )

    def update_embed(self):
        failed: list[str] = []

        name = self.name.value.strip()
        if not name:
            raise InvalidModalField('Name and Value are required.')
        value = self.value.value.strip()
        if not value:
            raise InvalidModalField('Name and Value are required.')
        _inline = self.inline.value.strip()
        _idx = self.index.value.strip()

        inline = True
        if _inline:
            try:
                inline = to_boolean(_inline)
            except Exception as e:
                failed.append(str(e))

        if _idx:
            try:
                index = int(_idx) - 1
                self.parent_view.embed.insert_field_at(index=index, name=name, value=value, inline=inline)
            except:
                failed.append('Invalid index! (not a number)')
                self.parent_view.embed.add_field(name=name, value=value, inline=inline)
        else:
            self.parent_view.embed.add_field(name=name, value=value, inline=inline)

        if failed:
            raise InvalidModalField('\n'.join(failed))


class EditFieldModal(BaseModal):
    name = discord.ui.TextInput[Self](label='Field Name', max_length=256)
    value = discord.ui.TextInput[Self](label='Field Value', max_length=1024, style=discord.TextStyle.paragraph)
    inline = discord.ui.TextInput[Self](
        label='Is inline?', placeholder='[ "Yes" | "No" ] (Default: Yes)', max_length=4, required=False
    )
    new_index = discord.ui.TextInput[Self](
        label='Index (where to place this field)',
        placeholder='Number between 1 and 25. Default: 25 (last)',
        max_length=2,
        required=False,
    )

    def __init__(self, parent_view: EmbedEditor, index: int) -> None:
        self.field = parent_view.embed.fields[index]
        self.title = f'Editing field number {index}'
        self.index = index

        super().__init__(parent_view)

    def update_defaults(self, embed: discord.Embed):
        self.name.default = self.field.name
        self.value.default = self.field.value
        self.inline.default = 'Yes' if self.field.inline else 'No'
        self.new_index.default = str(self.index + 1)

    def update_embed(self):
        failed = None

        name = self.name.value.strip()
        if not name:
            raise InvalidModalField('Name and Value are required.')
        value = self.value.value.strip()
        if not value:
            raise InvalidModalField('Name and Value are required.')
        _inline = self.inline.value.strip()

        inline = True
        if _inline:
            try:
                inline = to_boolean(_inline)
            except Exception as e:
                failed = str(e)
        if self.new_index.value.isdigit():
            self.parent_view.embed.remove_field(self.index)
            self.parent_view.embed.insert_field_at(int(self.new_index.value) - 1, name=name, value=value, inline=inline)
        else:
            self.parent_view.embed.set_field_at(self.index, name=name, value=value, inline=inline)

        if failed:
            raise InvalidModalField(failed)

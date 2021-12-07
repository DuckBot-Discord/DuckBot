import io
import logging
import re

import discord
import typing
import random

from asyncdagpi import ImageFeatures
from discord import Interaction, InvalidArgument
from discord.ext import commands

from DuckBot.helpers import constants
from typing import Union, TYPE_CHECKING

target_type = Union[discord.Member, discord.User, discord.PartialEmoji, discord.Guild, discord.Invite]

if TYPE_CHECKING:
    from DuckBot.__main__ import DuckBot
else:
    from discord.ext.commands import Bot as DuckBot


reminder_embeds = [
    discord.Embed(title='⭐ Support me by voting here!', colour=discord.Colour.yellow(), url='https://top.gg/bot/788278464474120202'),
    discord.Embed(title=f'{constants.INVITE} Invite me to your server!', colour=discord.Colour.yellow(),
                  url='https://discord.com/oauth2/authorize?client_id=788278464474120202&scope=applications.commands+bot&permissions=294171045078'),
    discord.Embed(title='🆘 Join my support server here!', colour=discord.Colour.yellow(), url='https://discord.gg/TdRfGKg8Wh'),
    discord.Embed(title='<:thanks:913507741727854702> suggest a feature with `db.suggest <feature>`!', colour=discord.Colour.yellow()),
]


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


class ConfirmButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, button_style: discord.ButtonStyle):
        super().__init__(style=button_style, label=label, emoji=emoji, )

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: Confirm = self.view
        view.value = True
        view.stop()


class CancelButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, button_style: discord.ButtonStyle):
        super().__init__(style=button_style, label=label, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: Confirm = self.view
        view.value = False
        view.stop()


class Confirm(discord.ui.View):
    def __init__(self, buttons: typing.Tuple[typing.Tuple[str]], timeout: int = 30):
        super().__init__(timeout=timeout)
        self.message = None
        self.value = None
        self.ctx: CustomContext = None
        self.add_item(ConfirmButton(emoji=buttons[0][0],
                                    label=buttons[0][1],
                                    button_style=(
                                            buttons[0][2] or discord.ButtonStyle.green
                                    )))
        self.add_item(CancelButton(emoji=buttons[1][0],
                                   label=buttons[1][1],
                                   button_style=(
                                           buttons[1][2] or discord.ButtonStyle.red
                                   )))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user.id in (self.ctx.bot.owner_id, self.ctx.author.id):
            return True
        messages = [
            "Oh no you can't do that! This belongs to **{user}**",
            'This is **{user}**\'s confirmation, sorry! 💢',
            '😒 Does this look yours? **No**. This is **{user}**\'s confirmation button',
            f'{constants.GET_SOME_HELP}',
            'HEYYYY!!!!! this is **{user}**\'s menu.',
            'Sorry but you can\'t mess with **{user}**\' menu :(',
            'No. just no. This is **{user}**\'s menu.',
            constants.BLOB_STOP_SIGN * 3,
            'You don\'t look like {user} do you...',
            '🤨 That\'s not yours! That\'s **{user}**\'s menu',
            '🧐 Whomst! you\'re not **{user}**',
            '_out!_ 👋'
        ]
        await interaction.response.send_message(random.choice(messages).format(user=self.ctx.author.display_name),
                                                ephemeral=True)

        return False


class CustomContext(commands.Context):
    bot: DuckBot

    @property
    def clean_prefix(self) -> str:
        """ Prefix with escaped MarkDown """
        return super().clean_prefix.replace('@', '(at)')

    @staticmethod
    def tick(opt: bool, text: str = None) -> str:
        """ Tick """
        emoji = constants.CUSTOM_TICKS.get(opt, constants.CUSTOM_TICKS[False])
        if text:
            return f"{emoji} {text}"
        return emoji

    @staticmethod
    def default_tick(opt: bool, text: str = None) -> str:
        """ Tick """
        emoji = constants.DEFAULT_TICKS.get(opt, constants.DEFAULT_TICKS[False])
        if text:
            return f"{emoji} {text}"
        return emoji

    @staticmethod
    def square_tick(opt: bool, text: str = None) -> str:
        """ Tick """
        emoji = constants.SQUARE_TICKS.get(opt, constants.SQUARE_TICKS[False])
        if text:
            return f"{emoji} {text}"
        return emoji

    @staticmethod
    def toggle(opt: bool, text: str = None) -> str:
        """ Tick """
        emoji = constants.TOGGLES.get(opt, constants.TOGGLES[False])
        if text:
            return f"{emoji} {text}"
        return emoji

    async def send(self, content: str = None, *, embed: discord.Embed = None,
                   embeds: typing.List[discord.Embed] = None, reply: bool = True, footer: bool = True,
                   reference: typing.Union[discord.Message, discord.MessageReference] = None,
                   gist: bool = False, extension: str = 'py', reminders: bool = True, file: discord.File = None,
                   maybe_attachment: bool = False, **kwargs) -> discord.Message:

        if gist is True and maybe_attachment is True:
            raise ValueError('You can\'t use both gist and attachment')

        if file is True and maybe_attachment is True:
            raise ValueError('You can\'t use both file and attachment')

        reference = (reference or self.message.reference or self.message) if reply is True else reference

        if reminders is True:
            reminders = random.randint(0, 200) == 100

        if embed and embeds:
            raise InvalidArgument('cannot pass both embed and embeds parameter to send()')

        if content or embed:
            test_string = re.sub("[^A-Za-z0-9._-]+", '', (str(content) or '') + str((embed.to_dict() if embed else '')))
            if self.bot.http.token in test_string.replace('\u200b', '').replace(' ', ''):
                raise commands.BadArgument('Could not send message as it contained the bot\'s token!')

        if embed and footer is True:
            if not embed.footer:
                embed.set_footer(text=f"Requested by {self.author}",
                                 icon_url=self.author.display_avatar.url)
                embed.timestamp = discord.utils.utcnow()

        if embed:
            colors = {embed.color} - {discord.Color.default(), discord.Embed.Empty}
            embed.colour = next(iter(colors), self.color)

        embeds = [embed] if embed else (embeds or [])

        if gist and content and len(content) > 2000:
            await self.trigger_typing()
            content = await self.bot.create_gist(filename=f'output.{extension}',
                                                 description='DuckBot send',
                                                 content=cleanup_code(content), public=True)
            content = f"<{content}>"

        elif maybe_attachment and len(content) > 2000:
            file = io.StringIO(cleanup_code(content))
            file = discord.File(file, filename=f'output.{extension}')
            content = None

        if reminders:
            if len(embeds) < 10 and sum(len(e) for e in embeds) < 5800:
                embeds.append(random.choice(reminder_embeds))

        try:
            return await super().send(content=content, embeds=embeds, reference=reference, file=file, **kwargs)
        except discord.HTTPException:
            return await super().send(content=content, embeds=embeds, reference=None, file=file, **kwargs)

    async def confirm(self, message: str = 'Do you want to confirm?',
                      buttons: typing.Tuple[typing.Union[discord.PartialEmoji, str],
                                            str, discord.ButtonStyle] = None, timeout: int = 30,
                      delete_after_confirm: bool = False,
                      delete_after_timeout: bool = False,
                      delete_after_cancel: bool = None,
                      return_message: bool = False) \
            -> typing.Union[bool, typing.Tuple[bool, discord.Message]]:
        """ A confirmation menu. """

        delete_after_cancel = delete_after_cancel if delete_after_cancel is not None else delete_after_confirm

        view = Confirm(buttons=buttons or (
            (None, 'Confirm', discord.ButtonStyle.green),
            (None, 'Cancel', discord.ButtonStyle.red)
        ), timeout=timeout)
        view.ctx = self
        message = await self.send(message, view=view)
        await view.wait()
        if False in (delete_after_cancel, delete_after_confirm, delete_after_timeout):
            view.children = [view.children[0]]
            for c in view.children:
                c.disabled = True
                if view.value is False:
                    c.label = 'Cancelled!'
                    c.emoji = None
                    c.style = discord.ButtonStyle.red
                elif view.value is True:
                    c.label = 'Confirmed!'
                    c.emoji = None
                    c.style = discord.ButtonStyle.green
                else:
                    c.label = 'Timed out!'
                    c.emoji = '⏰'
                    c.style = discord.ButtonStyle.gray
        view.stop()
        if view.value is None:

            try:
                if return_message is False:
                    (await message.edit(view=view)) if delete_after_timeout is False else (await message.delete())
            except (discord.Forbidden, discord.HTTPException):
                pass
            return (None, message) if delete_after_timeout is False and return_message is True else None

        elif view.value:

            try:
                if return_message is False:
                    (await message.edit(view=view)) if delete_after_confirm is False else (await message.delete())
            except (discord.Forbidden, discord.HTTPException):
                pass
            return (True, message) if delete_after_confirm is False and return_message is True else True

        else:

            try:
                if return_message is False:
                    (await message.edit(view=view)) if delete_after_cancel is False else (await message.delete())
            except (discord.Forbidden, discord.HTTPException):
                pass

            return (False, message) if delete_after_cancel is False and return_message is True else False

    @property
    def color(self):
        """ Returns DuckBot's color, or the author's color. Falls back to blurple """
        return self.me.color if self.me.color not in (discord.Color.default(), discord.Embed.Empty, None) \
            else self.author.color if self.author.color not in (discord.Color.default(), discord.Embed.Empty, None) \
            else discord.Color.blurple()

    @property
    def colour(self):
        """ Returns DuckBot's color, or the author's color. Falls back to blurple """
        return self.color

    async def gist(self, content: str, *, filename: str = 'output.py', description: str = 'Uploaded by DuckBot', public: bool = True):
        """ Shortcut of bot.create_gist + ctx.send(gist) """
        gist = await self.bot.create_gist(filename=filename, description=description, content=content, public=public)
        await self.send(f'<{gist}>')

    async def trigger_typing(self) -> None:
        try:
            await super().trigger_typing()
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def dagpi(self, target: target_type = None, *, feature: ImageFeatures, **kwargs) -> discord.File:
        await self.trigger_typing()
        try:
            return await self.bot.dagpi_request(self, target, feature=feature, **kwargs)
        except Exception as e:
            logging.error(f'Failed to get DAGPI for {target}', exc_info=e)
            raise commands.BadArgument(f'Something went wrong, oops. Please try again!')

    @property
    def reference(self) -> typing.Optional[discord.Message]:
        return getattr(self.message.reference, 'resolved', None)

    @property
    def referenced_user(self) -> typing.Optional[discord.abc.User]:
        return getattr(self.reference, 'author', None)

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union, overload, Literal

import discord
from discord.ext import commands

from .errors import SilentCommandError

if TYPE_CHECKING:
    from bot import DuckBot
    from discord.message import Message


__all__: Tuple[str, ...] = (
    'DuckContext',
    'DuckGuildContext',
    'tick',
)


VALID_EDIT_KWARGS: Dict[str, Any] = {
    'content': None,
    'embeds': [],
    'attachments': [],
    'suppress': False,
    'delete_after': None,
    'allowed_mentions': None,
    'view': None,
}


def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
    """A function to convert a boolean value with label to an emoji with label.

    Parameters
    ----------
    opt: Optional[:class:`bool`]
        The boolean value to convert.
    label: Optional[:class:`str`]
        The label to use for the emoji.

    Returns
    -------
    :class:`str`
        The emoji with label.
    """
    lookup = {True: '\N{WHITE HEAVY CHECK MARK}', False: '\N{CROSS MARK}', None: '\N{BLACK QUESTION MARK ORNAMENT}'}
    emoji = lookup.get(opt, '\N{CROSS MARK}')
    if label is not None:
        return f'{emoji} {label}'

    return emoji


class ConfirmationView(discord.ui.View):
    def __init__(self, ctx: DuckContext, *, timeout: int = 60, labels: tuple[str, str] = ('Confirm', 'Cancel')) -> None:
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value = None
        self.message: discord.Message | None = None
        self.ctx.bot.views.add(self)

        confirm, cancel = labels
        self.confirm.label = confirm
        self.cancel.label = cancel

    async def interaction_check(self, interaction: discord.Interaction[DuckBot]) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self) -> None:
        self.ctx.bot.views.discard(self)
        if self.message:
            for item in self.children:
                item.disabled = True  # type: ignore

            await self.message.edit(content=f'Timed out waiting for a button press from {self.ctx.author}.', view=self)

    def stop(self) -> None:
        self.ctx.bot.views.discard(self)
        super().stop()

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction[DuckBot], button: discord.ui.Button) -> None:
        assert interaction.message is not None

        self.value = True
        self.stop()
        await interaction.message.delete()

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction[DuckBot], button: discord.ui.Button) -> None:
        assert interaction.message is not None

        self.value = False
        self.stop()
        await interaction.message.delete()


class DuckContext(commands.Context['DuckBot']):
    """The subclassed Context to allow some extra functionality."""

    if TYPE_CHECKING:
        bot: DuckBot
        guild: discord.Guild
        user: Optional[Union[discord.User, discord.Member]]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.is_error_handled = False
        self._message_count: int = 0
        self.user = self.author
        self.client = self.bot

    @staticmethod
    @discord.utils.copy_doc(tick)
    def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
        return tick(opt, label)

    @discord.utils.cached_property
    def color(self) -> discord.Color:
        """:class:`~discord.Color`: Returns DuckBot's color, or the author's color. Falls back to blurple"""

        def check(color):
            return color not in {discord.Color.default(), None}

        checks = (
            me_color if check(me_color := self.me.color) else None,
            you_color if check(you_color := self.author.color) else None,
            self.bot.color,
        )

        result = discord.utils.find(lambda e: e, checks)
        if not result:
            raise RuntimeError('Unreachable code has been reached')

        return result

    async def send(self, content: str | None = None, *args: Any, **kwargs: Any) -> Message:
        """|coro|

        Sends a message to the invoking context's channel.

        View :meth:`~discord.ext.commands.Context.send` for more information of parameters.

        Returns
        -------
        :class:`~discord.Message`
            The message that was created.
        """
        if kwargs.get('embed') and kwargs.get('embeds'):
            raise TypeError('Cannot mix embed and embeds keyword arguments.')

        embeds = kwargs.pop('embeds', []) or ([kwargs.pop('embed')] if kwargs.get('embed', None) else [])
        if embeds:
            for embed in embeds:
                if embed.color is None:
                    # Made this the bot's vanity colour, although we'll
                    # be keeping self.color for other stuff like userinfo
                    embed.color = self.bot.color

        kwargs['embeds'] = embeds

        if self._previous_message:
            new_kwargs = deepcopy(VALID_EDIT_KWARGS)
            new_kwargs['content'] = content
            new_kwargs.update(kwargs)
            edit_kw = {k: v for k, v in new_kwargs.items() if k in VALID_EDIT_KWARGS}
            attachments = new_kwargs.pop('files', []) or ([new_kwargs.pop('file')] if new_kwargs.get('file', None) else [])
            if attachments:
                edit_kw['attachments'] = attachments
                new_kwargs['files'] = attachments

            try:
                m = await self._previous_message.edit(**edit_kw)
                self._previous_message = m
                self._message_count += 1
                return m
            except discord.HTTPException:
                self._previous_message = None
                self._previous_message = m = await super().send(content, **kwargs)
                return m

        self._previous_message = m = await super().send(content, **kwargs)
        self._message_count += 1
        return m

    @property
    def _previous_message(self) -> Optional[discord.Message]:
        if self.message:
            try:
                return self.bot.messages[repr(self)]
            except KeyError:
                return None

    @_previous_message.setter
    def _previous_message(self, message: Optional[discord.Message]) -> None:
        if isinstance(message, discord.Message):
            self.bot.messages[repr(self)] = message
        else:
            self.bot.messages.pop(repr(self), None)

    @overload
    async def confirm(
        self, content=None, /, *, timeout: int = 30, silent_on_timeout: Literal[False] = False, **kwargs
    ) -> bool | None: ...

    @overload
    async def confirm(self, content=None, /, *, timeout: int = 30, silent_on_timeout: Literal[True], **kwargs) -> bool: ...

    async def confirm(
        self,
        content=None,
        /,
        *,
        timeout: int = 30,
        silent_on_timeout: bool = False,
        labels: tuple[str, str] = ('Confirm', 'Cancel'),
        **kwargs,
    ) -> bool | None:
        """|coro|

        Prompts a confirmation message that users can confirm or deny.

        Parameters
        ----------
        content: str | None
            The content of the message. Can be an embed.
        timeout: int | None
            The timeout for the confirmation.
        kwargs:
            Additional keyword arguments to pass to `self.send`.

        Returns
        -------
        :class:`bool`
            Whether the user confirmed or not.
            None if the view timed out.
        """
        view = ConfirmationView(self, timeout=timeout, labels=labels)
        try:
            view.message = await self.channel.send(content, **kwargs, view=view)
            await view.wait()
            value = view.value
        except discord.HTTPException:
            view.stop()
            value = None

        if silent_on_timeout and value is None:
            raise SilentCommandError('Timed out waiting for a response.')
        return value

    def __repr__(self) -> str:
        if self.message:
            return f'<utils.DuckContext bound to message ({self.channel.id}-{self.message.id}-{self._message_count})>'
        elif self.interaction:
            return f'<utils.DuckContext bound to interaction {self.interaction}>'
        return super().__repr__()


class DuckGuildContext(DuckContext):
    author: discord.Member


async def setup(bot: DuckBot) -> None:
    """Sets up the DuckContext class.

    Parameters
    ----------
    bot: DuckBot
        The bot to set up the DuckContext class for.
    """
    bot.messages.clear()
    bot._context_cls = DuckContext


async def teardown(bot: DuckBot) -> None:
    """Tears down the DuckContext class.

    Parameters
    ----------
    bot: DuckBot
        The bot to tear down the DuckContext class for.
    """
    bot._context_cls = commands.Context

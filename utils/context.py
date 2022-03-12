from __future__ import annotations

from typing import TYPE_CHECKING, Tuple, Optional, List, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord.message import Message
    from bot import DuckBot

__all__: Tuple[str, ...] = (
    'DuckContext',
    'tick',
    'setup',
    'teardown'
)


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
    lookup = {
        True: '\N{WHITE HEAVY CHECK MARK}',
        False: '\N{CROSS MARK}',
        None: '\N{BLACK QUESTION MARK ORNAMENT}'
    }
    emoji = lookup.get(opt, '\N{CROSS MARK}')
    if label is not None:
        return f'{emoji} {label}'

    return emoji


class DuckContext(commands.Context):
    """The subclassed Context to allow some extra functionality."""
    if TYPE_CHECKING:
        bot: DuckBot

    __slots__: Tuple[str, ...] = ()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    @discord.utils.copy_doc(tick)
    def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
        return tick(opt, label)

    @discord.utils.cached_property
    def color(self) -> discord.Color:
        """:class:`~discord.Color`: Returns DuckBot's color, or the author's color. Falls back to blurple """
        check = lambda color: color not in {discord.Color.default(), discord.Embed.Empty, None}
        checks = (
            me_color if check(me_color := self.me.color) else None,
            you_color if check(you_color := self.author.color) else None,
            self.bot.color
        )

        result = discord.utils.find(lambda e: e, checks)
        if not result:
            raise RuntimeError('Unreachable code has been reached')

        return result

    async def send(self, *args, **kwargs) -> Message:
        """|coro|
        
        Sends a message to the invoking context's channel.

        View :meth:`~discord.ext.commands.Context.send` for more information of parameters.
        
        Returns
        -------
        :class:`~discord.Message`
            The message that was created.
        """
        if kwargs.get('embed') and kwargs.get('embeds'):
            raise ValueError('Cannot send both embed and embeds')

        embeds = kwargs.pop('embeds', []) or [kwargs.pop('embed', None)]
        if None in embeds:
            embeds.remove(None)
        if embeds:
            for embed in embeds:
                if embed.color is discord.Embed.Empty:
                    # Made this the bot's vanity colour, although we'll
                    # be keeping self.color for other stuff like userinfo
                    embed.color = self.bot.color

            kwargs['embeds'] = embeds

        return await super().send(*args, **kwargs)

    async def prompt_autocomplete(self, text: Optional[str] = "Choose an option...", choices: List[discord.SelectOption] = []):
        """|coro|
        
        Prompts an autocomplete select menu that users can select choices.

        Returns
        -------
        :class: `~str`
            The value the user chose.
        """
        ...


def setup(bot: DuckBot) -> None:
    """Sets up the DuckContext class.

    Parameters
    ----------
    bot: DuckBot
        The bot to set up the DuckContext class for.
    """
    bot._context_cls = DuckContext


def teardown(bot: DuckBot) -> None:
    """Tears down the DuckContext class.

    Parameters
    ----------
    bot: DuckBot
        The bot to tear down the DuckContext class for.
    """
    bot._context_cls = commands.Context

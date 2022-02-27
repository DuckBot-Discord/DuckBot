from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Tuple, Optional

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord.message import Message

__all__: Tuple[str, ...] = (
    'DuckContext',
    'tick',
)

def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
    lookup = {
        True: '✅',
        False: '❌',
        None: '❔',
    }
    emoji = lookup.get(opt, '❌')
    if label is not None:
        return f'{emoji}: {label}'
    
    return emoji


class DuckContext(commands.Context):
    """The subclassed Context to allow some extra functionality.
    
    Attributes
    ----------
    tick: Callable[[Optional[:class:`str`], Optional[:class:`str`]], :class:`str`]
        A function to convert a boolean value with label to an emoji with label.
    """
    __slots__: Tuple[str, ...] = (
        'tick',
    )
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tick: Callable[[Optional[bool], Optional[str]], str] = tick
        
    @discord.utils.cached_property
    def color(self) -> discord.Color:
        """:class:`~discord.Color`: Returns DuckBot's color, or the author's color. Falls back to blurple """
        check = lambda color: color not in {discord.Color.default(), discord.Embed.Empty, None}
        checks = (
            me_color if check(me_color := self.me.color) else None,
            you_color if check(you_color := self.author.color) else None,
            discord.Color.blurple()
        )
        return any(checks)
        
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

        embeds = kwargs.pop('embed', kwargs.pop('embeds', []))
        if embeds:
            for embed in embeds:
                if embed.color is embed.EmptyEmbed:
                    embed.color = self.color
                    
            kwargs['embeds'] = embeds
                    
        return await super().send(*args, **kwargs)
                
from __future__ import annotations

import uuid
from typing import (
    TYPE_CHECKING,
    Optional,
    Type,
    Tuple,
)

from discord.ext import commands

from .errors import *

if TYPE_CHECKING:
    from bot import DuckBot

__all__: Tuple[str, ...] = (
    'DuckCog',
)



class DuckCog(commands.Cog):
    """The base class for all DuckBot cogs.

    Attributes
    ----------
    bot: DuckBot
        The bot instance.
    """
    if TYPE_CHECKING:
        emoji: Optional[str]
        brief: Optional[str]

    #__metaclass__: DuckCogMeta = DuckCogMeta

    __slots__: Tuple[str, ...] = (
        'bot',
    )

    def __init_subclass__(cls: Type[DuckCog], **kwargs) -> None:
        """
        This is called when a subclass is created.
        Its purpose is to add parameters to the cog
        that will later be used in the help command.
        """
        cls.emoji = kwargs.pop('emoji', None)
        cls.brief = kwargs.pop('brief', None)
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: DuckBot, *args, **kwargs) -> None:
        self.bot: DuckBot = bot
        self.id: int = int(str(int(uuid.uuid4()))[:20])
        
        kwargs['bot'] = bot
        super().__init__(*args, **kwargs) # type: ignore

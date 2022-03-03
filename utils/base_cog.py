from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Optional,
    Type,
)

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

from discord.ext import commands

from .errors import *

if TYPE_CHECKING:
    from bot import DuckBot


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

    def __init__(self, bot: DuckBot) -> None:
        self.bot: DuckBot = bot

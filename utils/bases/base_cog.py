from __future__ import annotations
from typing_extensions import Self

import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    Type,
    Tuple,
)

from discord.ext import commands

from utils.bases.command import DuckCommand

if TYPE_CHECKING:
    from bot import DuckBot

__all__: Tuple[str, ...] = ("DuckCog",)


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
        hidden: bool

    __slots__: Tuple[str, ...] = ("bot", "hidden")

    def __init_subclass__(cls: Type[DuckCog], **kwargs: Any) -> None:
        """
        This is called when a subclass is created.
        Its purpose is to add parameters to the cog
        that will later be used in the help command.
        """
        cls.emoji = kwargs.pop("emoji", None)
        cls.brief = kwargs.pop("brief", None)
        cls.hidden = kwargs.pop("hidden", False)
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: DuckBot, *args: Any, **kwargs: Any) -> None:
        self.bot: DuckBot = bot
        self.id: int = int(str(int(uuid.uuid4()))[:20])

        next_in_mro = next(iter(self.__class__.__mro__))
        if hasattr(next_in_mro, "__is_jishaku__") or isinstance(
            next_in_mro, self.__class__
        ):
            kwargs["bot"] = bot

        super().__init__(*args, **kwargs)

    def get_commands(self) -> List[DuckCommand[Self, ..., Any]]:
        return super().get_commands()  # type: ignore

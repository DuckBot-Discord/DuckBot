from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from discord.ext import commands

if TYPE_CHECKING:
    from bot import DuckBot


class DuckCog(commands.Cog):
    __slots__: Tuple[str, ...] = (
        'bot',
    )
     
    def __init__(self, bot: DuckBot) -> None:
        self.bot: DuckBot = bot

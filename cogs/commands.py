from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

import discord
from discord.ext import commands

from utils import DuckCog

if TYPE_CHECKING:
    from bot import DuckBot

__all__: Tuple[str, ...] = (
    'Commands',
)

class Commands(DuckCog):
    ...
    
    
def setup(bot: DuckBot) -> None:
    bot.add_cog(Commands(bot))
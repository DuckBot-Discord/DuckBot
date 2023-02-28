from __future__ import annotations

from typing import TYPE_CHECKING

from .block import Block
from .tempmute import TempMute
from .standard import StandardModeration

if TYPE_CHECKING:
    from bot import DuckBot


class Moderation(
    TempMute,
    StandardModeration,
    Block,
    emoji='\N{HAMMER AND PICK}',
    brief='Moderation commands!',
):
    """All commands to moderate members, roles, channels, etc."""


async def setup(bot: DuckBot):
    await bot.add_cog(Moderation(bot))

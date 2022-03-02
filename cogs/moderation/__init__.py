from __future__ import annotations

from typing import TYPE_CHECKING

from .tempmute import TempMute
from .standard import StandardModeration

if TYPE_CHECKING:
    from bot import DuckBot
    
    
class Moderation(TempMute, StandardModeration, emoji='\N{HAMMER AND PICK}'):
    pass


def setup(bot: DuckBot):
    bot.add_cog(Moderation(bot))

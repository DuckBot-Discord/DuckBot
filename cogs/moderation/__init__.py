from __future__ import annotations

from typing import TYPE_CHECKING

from .tempmute import TempMute


if TYPE_CHECKING:
    from bot import DuckBot
    
    
class Moderation(TempMute, emoji='\N{HAMMER AND PICK}'):
    pass


def setup(bot: DuckBot):
    bot.add_cog(Moderation(bot))

from __future__ import annotations

from typing import TYPE_CHECKING

from .channel import ChannelModeration
from .mutes import TempMute
from .standard import StandardModeration
from .message import MessagePurge
from .new_account_gate import NewAccountGate

if TYPE_CHECKING:
    from bot import DuckBot


# ['archive', 'role', 'slowmode', 'snipe']


class Moderation(
    TempMute,
    StandardModeration,
    ChannelModeration,
    MessagePurge,
    NewAccountGate,
    emoji='\N{HAMMER AND PICK}',
    brief='Moderation commands!',
):
    """All commands to moderate members, roles, channels, etc."""


async def setup(bot: DuckBot):
    await bot.add_cog(Moderation(bot))

from __future__ import annotations

from bot import DuckBot

from .prefixes import PrefixChanges
from .commands import CommandConfig


class GuildConfig(
    PrefixChanges,
    CommandConfig,
    name="Guild Config",
    emoji="\N{WRENCH}",
    brief="Configurations for the current server.",
):
    pass

async def setup(bot: DuckBot):
    await bot.add_cog(GuildConfig(bot))

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
    """Commands that allow you to configure the bot for the current server,
    these include things such as permissions to use specific commands, making the
    bot ignore channels, change the custom prefixes for this server, logging, and much more!"""


async def setup(bot: DuckBot):
    await bot.add_cog(GuildConfig(bot))

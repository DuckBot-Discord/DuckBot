from bot import DuckBot
from .prefixes import PrefixChanges


class GuildConfig(
    PrefixChanges,
    name="Guild Config",
    emoji="\N{WRENCH}",
    brief="Configurations for the current server.",
):
    pass

def setup(bot: DuckBot):
    bot.add_cog(GuildConfig(bot))

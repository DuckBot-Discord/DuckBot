from .counting import Counting
from .invite_stats import InviteStats
from .logging import Logging
from .muterole import MuteRole
from .prefixes import Prefixes
from .suggestions import Suggestions
from .welcome import Welcome
from .modlog import ModLogs
from .command_settings import CommandConfigs

async def setup(bot):
    await bot.add_cog(GuildConfig(bot))


class GuildConfig(
    Counting,
    InviteStats,
    Logging,
    MuteRole,
    Prefixes,
    Suggestions,
    Welcome,
    ModLogs,
    name="Server Settings",
):
    select_emoji = "⚙"
    select_brief = "Manage Bot Settings, Like Prefix, Logs, etc."

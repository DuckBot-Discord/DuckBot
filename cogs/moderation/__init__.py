from .basic_mod import BasicModCommands
from .channel_management import ChannelManagementCommands
from .clear_messages import RemovalCommands
from .mute_members import MuteCommands
from .role_management import RoleManagementCommands
from .snipe import Snipe
from .new_account_gate import NewAccountGate
from discord.ext.commands import NoPrivateMessage


class Moderation(
    BasicModCommands,
    ChannelManagementCommands,
    RemovalCommands,
    MuteCommands,
    RoleManagementCommands,
    Snipe,
    NewAccountGate,
):
    """
    🔨 Commands to facilitate server moderation, and all utilities for admins and mods.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.select_emoji = "🔨"
        self.select_brief = "Mod Commands, like Ban and Mute"

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise NoPrivateMessage
        return True


async def setup(bot):
    await bot.add_cog(Moderation(bot))

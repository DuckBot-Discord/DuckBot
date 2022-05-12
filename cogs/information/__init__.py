from .user_info import UserInfo
from .perms import PermsViewer


class Info(UserInfo, PermsViewer, emoji='📜', brief="Informational commands."):
    """All commands that provide information about the users, channels, etc."""

    ...


async def setup(bot):
    await bot.add_cog(Info(bot))

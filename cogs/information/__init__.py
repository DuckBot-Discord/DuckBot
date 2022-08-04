from .user_info import UserInfo
from .perms import PermsViewer
from .audit_logs import AuditLogViewer


class Info(UserInfo, PermsViewer, AuditLogViewer, emoji='📜', brief="Informational commands."):
    """All commands that provide information about the users, channels, etc."""


async def setup(bot):
    await bot.add_cog(Info(bot))

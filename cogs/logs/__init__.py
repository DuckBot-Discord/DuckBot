from .join_leave_logs import JoinLeaveLogs
from .memer_logs import MemberLogs
from .message_logs import MessageLogs
from .server_logs import ServerLogs
from .voice_logs import VoiceLogs
from .modlog import ModLogs


class LoggingBackend(JoinLeaveLogs, MemberLogs, MessageLogs, ServerLogs, ModLogs):
    pass


async def setup(bot):
    await bot.add_cog(LoggingBackend(bot))

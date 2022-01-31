from .join_leave_logs import JoinLeaveLogs
from .memer_logs import MemberLogs
from .message_logs import MessageLogs
from .server_logs import ServerLogs
from .voice_logs import VoiceLogs


class LoggingBackend(JoinLeaveLogs, MemberLogs, MessageLogs, ServerLogs, VoiceLogs):
    pass


def setup(bot):
    bot.add_cog(LoggingBackend(bot))
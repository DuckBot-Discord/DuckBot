from .afk import Afk
from .emoji_utils import EmojiUtils
from .message_utils import MessageUtils
from .misc_utils import MiscUtils
from .server_info import ServerInfo
from .todo_list import TodoList
from .user_info import UserInfo


__all__ = ()


class Utility(Afk, EmojiUtils, MessageUtils, MiscUtils, ServerInfo, TodoList, UserInfo):
    """
    💬 Text and utility commands, mostly to display information about a server.
    """
    select_emoji = '💬'
    select_brief = 'Utility And General Information Commands.'


def setup(bot):
    bot.add_cog(Utility(bot))

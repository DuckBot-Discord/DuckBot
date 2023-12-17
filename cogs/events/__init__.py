from .afk_handler import AfkHandler
from .arrival_and_cleanup import ArrivalAndCleanup
from .automatic_blacklist import AutoBlacklist
from .custom_welcome_messages import WelcomeMessages
from .error_handler import ErrorHandler
from .muted_members import MutedMembers
from .private_events import PrivateEvents
from .reactions import ReactionHandling
from .suggestion_channels import SuggestionChannels
from .tasks import Tasks


class Handler(
    AfkHandler,
    ArrivalAndCleanup,
    AutoBlacklist,
    WelcomeMessages,
    ErrorHandler,
    MutedMembers,
    PrivateEvents,
    ReactionHandling,
    SuggestionChannels,
    Tasks,
):
    """
    This class is the event handler for the bot.
    """

    pass


async def setup(bot):
    await bot.add_cog(Handler(bot))

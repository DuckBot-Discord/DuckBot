from .afk_handler import AfkHandler
from .arrival_and_cleanup import ArrivalAndCleanup
from .automatic_blacklist import AutoBlacklist
from .custom_welcome_messages import WelcomeMessages
from .error_handler import ErrorHandler
from .muted_members import MutedMembers
from .private_events import PrivateEvents
from .reactions import ReactionHandling
from .suggestion_channels import SuggestionChannels
from .blackout_mode import BlackoutMode
from .tasks import Tasks


class Handler(AfkHandler, ArrivalAndCleanup, AutoBlacklist,
              WelcomeMessages, ErrorHandler, MutedMembers, PrivateEvents,
              ReactionHandling, SuggestionChannels, Tasks, BlackoutMode):
    """
    This class is the event handler for the bot.
    """
    pass


def setup(bot):
    bot.add_cog(Handler(bot))

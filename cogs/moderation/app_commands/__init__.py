from .standard import ApplicationStandard
from .block import ApplicationBlock

class ApplicationModeration(
    ApplicationStandard,
    ApplicationBlock,
):
    """ Moderation cog with Application commands. """

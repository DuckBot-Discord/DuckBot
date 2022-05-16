from .news import ApplicationNews
from .reminders import ApplicationReminders


class ApplicationMeta(ApplicationNews, ApplicationReminders):
    """Application commands of meta cog."""

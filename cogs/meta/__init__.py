import discord
from .news import News
from bot import DuckBot
from utils.errors import DuckBotNotStarted
from .reminders import Reminders


class Meta(News, Reminders, emoji="\N{INFORMATION SOURCE}"):
    """All commands about the bot itself."""

    @discord.utils.cached_property
    def brief(self):
        if not self.bot.user:
            raise DuckBotNotStarted('Somehow, the bot has not logged in yet')
        return f"Commands related to {self.bot.user.name}"

def setup(bot: DuckBot):
    bot.add_cog(Meta(bot))

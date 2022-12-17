from collections import Counter
from discord.ext import commands

from bot import DuckBot


class EventsBase(commands.Cog):
    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.error_channel = 880181130408636456
        self.mapping = commands.CooldownMapping.from_cooldown(1, 2, commands.BucketType.user)
        self._auto_spam_count = Counter()

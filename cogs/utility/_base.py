from discord.ext import commands
from ...__main__ import DuckBot


class UtilityBase(commands.Cog):
    def __init__(self, bot: DuckBot):
        self.bot = bot

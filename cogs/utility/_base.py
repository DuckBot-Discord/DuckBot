from discord.ext import commands
from bot import DuckBot


class UtilityBase(commands.Cog):
    def __init__(self, bot: DuckBot):
        self.bot = bot

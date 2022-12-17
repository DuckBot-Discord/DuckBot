import discord
from discord.ext import commands

from bot import DuckBot


class FunBase(commands.Cog):
    def __init__(self, bot: DuckBot):
        self.bot = bot

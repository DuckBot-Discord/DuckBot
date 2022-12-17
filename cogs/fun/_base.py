import discord
from discord.ext import commands

from DuckBot.__main__ import DuckBot


class FunBase(commands.Cog):
    def __init__(self, bot: DuckBot):
        self.bot = bot

# exceptions.py
from discord.ext import commands

class NoEmojisFound(commands.CheckFailure):
    pass

class HigherRole(commands.CheckFailure):
    pass

class NoQuotedMessage(commands.CheckFailure):
    pass

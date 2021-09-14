# exceptions.py
from discord.ext import commands


class NoEmojisFound(commands.CheckFailure):
    pass


class HigherRole(commands.CheckFailure):
    pass


class NoQuotedMessage(commands.CheckFailure):
    pass


class WaitForCancelled(commands.CheckFailure):
    pass


class MuteRoleNotFound(commands.CheckFailure):
    pass

class UserBlacklisted(commands.CheckFailure):
    pass
    

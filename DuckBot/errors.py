# exceptions.py
import datetime

import discord
from discord import Enum
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


class NoWelcomeChannel(commands.CheckFailure):
    pass


class BotUnderMaintenance(commands.CheckFailure):
    pass


class NoHideout(commands.CheckFailure):
    pass


class EconomyNotSetup(commands.CheckFailure):
    def __init__(self, prompt: bool = False):
        self.prompt: bool = prompt


class AccountNotFound(commands.CheckFailure):
    def __init__(self, user: discord.User):
        self.user: discord.User = user


class AccountAlreadyExists(commands.CheckFailure):
    def __init__(self, user: discord.User):
        self.user: discord.User = user


class CooldownType(Enum):
    WORK = 0
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3


class EconomyOnCooldown(commands.CheckFailure):
    def __init__(self, cooldown_type: CooldownType, next_run: datetime.datetime):
        self.cooldown_type = cooldown_type
        self.next_run = next_run


class WalletInUse(commands.CheckFailure):
    def __init__(self, user: discord.User):
        self.user = user


class BaseError(commands.CommandError):
    def __init__(self, e) -> None:
        self.custom = True
        self.message = e
        super().__init__(e)
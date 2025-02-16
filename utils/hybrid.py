from typing import TypeVar

from discord import app_commands
from discord.ext import commands

T = TypeVar('T')


def hybrid_permissions_check(guild: bool = False, **perms: bool):
    user_perms = {p: v for p, v in perms.items() if not p.startswith('bot_')}
    user_perms = {p[4:]: v for p, v in perms.items() if p.startswith('bot_')}
    commands_perms_check = commands.has_guild_permissions if guild else commands.has_permissions
    commands_bot_perms_check = commands.bot_has_guild_permissions if guild else commands.bot_has_permissions

    def decorator(func: T) -> T:
        commands_perms_check(**user_perms)(func)
        app_commands.default_permissions(**user_perms)(func)
        commands_bot_perms_check(**user_perms)
        return func

    return decorator

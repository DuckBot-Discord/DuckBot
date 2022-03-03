from __future__ import annotations

from typing import (
    TYPE_CHECKING,
)

from discord.ext import commands

from bot import DuckBot
from utils import errors

if TYPE_CHECKING:
    from .context import DuckContext

async def on_command_error(ctx: DuckContext, error: Exception) -> None:
    """|coro|

    A handler called when an error is raised while invoking a command.

    Parameters
    ----------
    ctx: :class:`DuckContext`
        The context for the command.
    error: :class:`commands.CommandError`
        The error that was raised.
    """
    error = getattr(error, 'original', error)
    
    ignored = (
        commands.CommandNotFound,
        commands.CheckFailure,
        errors.SilentCommandError,
    )

    if isinstance(error, ignored):
        return
    # Did pycharm give you shit about this? It's fine lmfao
    elif isinstance(error, (commands.UserInputError,errors.DuckBotException)):
        await ctx.send(error)
    elif isinstance(error, commands.CommandInvokeError):
        return await on_command_error(ctx, error.original)
    else:
        await ctx.bot.exceptions.add_error(error=error, ctx=ctx)


def setup(bot: DuckBot):
    """adds the event to the bot

    Parameters
    ----------
    bot: :class:`DuckBot`
        The bot to add the event to.
    """
    bot.add_listener(on_command_error)

from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Tuple
)

import discord
from discord.ext import commands

from utils import errors

if TYPE_CHECKING:
    from .context import DuckContext
    from bot import DuckBot
    
__all__: Tuple[str, ...] = (
    'on_command_error',
    'setup',
)

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
        errors.EntityBlacklisted,
    )

    if isinstance(error, ignored):
        return
    elif isinstance(error, (commands.UserInputError, errors.DuckBotException)):
        await ctx.send(error)
    elif isinstance(error, commands.CommandInvokeError):
        logging.error('what')
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

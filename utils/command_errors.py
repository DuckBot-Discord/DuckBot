from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from discord.ext import commands

from utils.bases import errors

if TYPE_CHECKING:
    from utils.bases.context import DuckContext
    from bot import DuckBot

__all__: Tuple[str, ...] = ()


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
    if ctx.is_error_handled is True:
        return

    error = getattr(error, 'original', error)

    ignored = (
        commands.CommandNotFound,
        commands.CheckFailure,
        errors.SilentCommandError,
        errors.EntityBlacklisted,
    )
    children_not_ignored = (commands.BotMissingPermissions,)

    if isinstance(error, ignored) and not isinstance(error, children_not_ignored):
        return
    elif isinstance(error, (commands.UserInputError, errors.DuckBotException, commands.BotMissingPermissions)):
        await ctx.send(str(error))
    elif isinstance(error, commands.CommandInvokeError):
        return await on_command_error(ctx, error.original)
    elif isinstance(error, errors.DuckBotNotStarted):
        await ctx.send('Oop! Duckbot has not started yet, try again soon.')
    else:
        await ctx.bot.exceptions.add_error(error=error, ctx=ctx)


async def setup(bot: DuckBot):
    """adds the event to the bot

    Parameters
    ----------
    bot: :class:`DuckBot`
        The bot to add the event to.
    """
    bot.add_listener(on_command_error)

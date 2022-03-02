from discord.ext import commands

from bot import DuckBot
from utils.errors import DuckBotException
from utils.context import DuckContext


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
    ignored = (
        commands.CommandNotFound,
        commands.CheckFailure,
    )
    if isinstance(error, ignored):
        return
    elif isinstance(error, (commands.UserInputError, DuckBotException)):
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

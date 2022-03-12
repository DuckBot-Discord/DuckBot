import typing
import inspect
import asyncio

from typing import TypeVar, List, Any, Generic, Optional

import discord

from discord.ext import commands

DC = TypeVar("DC", bound="DuckCommand")

"""
@cmd.autocomplete('param', timeout=25)
async def param_auto(ctx, user_input) -> Optional[str]:
    valid_choices: List[str] = ...
    value = await ctx.prompt_autocomplete(
        text = "Sorry, that's not one of the valid params! Select one of these:",
         choices = valid_choices,
    )
    return value # Could be None if the user didn't select
"""

# TODO: Finish AutoComplete.

@discord.utils.copy_doc(commands.Command)
class DuckCommand(commands.Command, Generic[DC]):

    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)

    def autocomplete(self, argument: str, timeout: Optional[int] = 30):
        def decorator(func: typing.Callable):
            func_parameters = ((inspect.signature(func))._parameters).keys()
            if not func_parameters:
                raise ValueError("No function parameters provided.")
            if func_parameters[0] != "ctx":
                raise TypeError('First parameter is not "ctx"')
            if not asyncio.iscoroutinefunction(func):
                raise Exception(f"The `{func.__name__}` method is not a coroutine.")
            
        return decorator
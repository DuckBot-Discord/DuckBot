import typing
import inspect
import asyncio
import functools

from typing import Callable, Dict, TypeVar, List, Any, Generic, Optional

import discord

from discord.ext import commands

from utils.autocomplete import AutoComplete

DC = TypeVar("DC", bound="DuckCommand")

def hooked_wrapped_callback(command, ctx, coro):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
        try:
            ret = await coro(*args, **kwargs)
        except commands.CommandError:
            ctx.command_failed = True
            raise
        except asyncio.CancelledError:
            ctx.command_failed = True
            return
        except Exception as exc:
            ctx.command_failed = True
            raise commands.CommandInvokeError(exc) from exc
        finally:
            if command._max_concurrency is not None:
                await command._max_concurrency.release(ctx)

            await command.call_after_hooks(ctx)
        return ret

    return wrapped

@discord.utils.copy_doc(commands.Command)
class DuckCommand(commands.Command, Generic[DC]):
	
	def __init__(self, func, **kwargs):
		super().__init__(func, **kwargs)
		self.autocompletes: Dict[str, AutoComplete] = {}
		
	async def invoke(self, ctx: commands.Context) -> None:
		await self.prepare(ctx)
		
		ctx.invoked_subcommand = None
		ctx.subcommand_passed = None
		injected = hooked_wrapped_callback(self, ctx, self.callback)
		for autocomplete, ac in self.autocompletes:
			for name in ctx.kwargs.keys():
				if autocomplete == name:
					ctx.kwargs[name] = (await ac.callback(ctx, ctx.kwargs[name]))
					ctx.command.timeout = ac._timeout
		await injected(*ctx.args, **ctx.kwargs)
		
	def autocomplete(self, argument: str):
		def decorator(func: typing.Callable):
			self.autocompletes[argument] = AutoComplete(func=func)
				
		return decorator
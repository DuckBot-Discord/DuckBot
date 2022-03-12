import typing
import inspect
import asyncio

from typing import Callable, Dict, TypeVar, List, Any, Generic, Optional

import discord

from discord.ext import commands
from discord.ext.commands import hooked_wrapped_callback

from utils.autocomplete import AutoComplete

DC = TypeVar("DC", bound="DuckCommand")

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
			func_parameters = ((inspect.signature(func))._parameters).keys()
			if not func_parameters:
				raise ValueError("No function parameters provided.")
			if func_parameters[0] != "ctx":
				raise TypeError('First parameter is not "ctx"')
			if not asyncio.iscoroutinefunction(func):
				raise Exception(f"The `{func.__name__}` method is not a coroutine.")
			self.autocompletes[argument] = AutoComplete(func=func)
				
		return decorator
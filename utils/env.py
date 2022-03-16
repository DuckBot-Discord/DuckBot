from __future__ import annotations

import os
from typing import (
	Dict,
	Any,
	Generic,
	Tuple,
	TypeVar
)

import aiofile

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')

__all__: Tuple[str, ...] = (
	'Environment',
	'load_env',
)


class Environment(object):
	"""A base class that implements an "Attribute Dictionary" for storing
	env values.
	"""
	# Was this really that hard ?
	def __init__(self, **kwargs) -> None:
		self.__dict__= kwargs 


async def load_env(file_name: str = ".env") -> Environment:
	"""|coro|
 
 	Loads a file to load the environment values from.

	Parameters
	----------
	file_name: :class:`str`
		The filename to load the env values from. Defaults to ".env".

	Returns
	-------
	:class:`Environment`
 		Represents the environment the `~load_env` function returns.
	"""
	async with aiofile.async_open(file_name) as f:
		content = await f.read()
  
	values: Dict[str, Any] = {}
	for line in content:
		try:
			key, value = line.split('=')
		except ValueError: # Not enough to unpack
			raise RuntimeError(f"Invalid line in {file_name}: {line}")
      
		values[key] = value
		os.environ[key] = value
  
	env = Environment(**values)
	return env

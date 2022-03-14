# std
import typing
import os

# 3rd party
import aiofiles

class Environment(object):
	def __init__(self, values: typing.Dict[str, typing.Any]) -> None:
		for k, v in values.items():
			setattr(self, k, v)

async def load_env(file_name: str = ".env"):
	"""Loads a file to load the environment values from.

	Parameters
	----------
		file_name (`~str`): The filename to load the env values from. Defaults to ".env".

	Returns
	-------
		`~Environment`: Represents the environment the `~load_env` function returns.
	"""
	async with aiofiles.open(file_name, "r") as file:
		content = await file.readlines()
	values: typing.Dict[str, typing.Any] = {}
	for line in content:
		contents = line.split("=")
		values[contents[0]] = contents[1]
	for name, value in values.items():
		os.environ[name] = value
	env = Environment(values)
	return env

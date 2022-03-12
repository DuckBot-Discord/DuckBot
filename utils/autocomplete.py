import discord

from discord.ext import commands

from typing import Callable, Optional, TypeVar, Dict, Generic, List, NamedTuple, Tuple


AC = TypeVar("AC", bound="AutoComplete")


class Dropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Red", description="Your favourite colour is red", emoji="🟥"),
            discord.SelectOption(label="Green", description="Your favourite colour is green", emoji="🟩"),
            discord.SelectOption(label="Blue", description="Your favourite colour is blue", emoji="🟦"),
        ]
        super().__init__(placeholder="Choose your favourite colour...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Your favourite colour is {self.values[0]}")


class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(Dropdown())
	
class AutoComplete(Generic[AC]):
	"""
    Represents an autocompletion of an argument.

    Attributes
    ----------
    choices: List[:class:`Option`]
      An array of options.
    """

	__slots__: Tuple[str, ...] = ("choices", "timeout", "_timeout",)
	
	def __init__(self, func: Callable, timeout: Optional[int] = None) -> None:
		self.callback: Callable = func
		self._timeout = timeout
		
	@property
	def timeout(self):
		return self._timeout
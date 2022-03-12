from logging.config import valid_ident
import discord

from discord.ext import commands

from typing import Callable, Optional, TypeVar, Dict, Generic, List, NamedTuple, Tuple


class Dropdown(discord.ui.Select):
	def __init__(self, options: List[discord.SelectOption]):
		options = options
		super().__init__(placeholder="Choose your favourite colour...", min_values=1, max_values=1, options=options)
		
	async def callback(self, interaction: discord.Interaction):
		self.value = self.values[0]
		await interaction.response.send_message(f"You chose {self.values[0]}.", ephemeral=True)


class DropdownView(discord.ui.View):
	def __init__(self, context: commands.Context, options: List[discord.SelectOption], timeout: Optional[int] = 30):
		super().__init__(timeout=timeout)
		self.add_item(Dropdown(options))
		self.context = context

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		if self.context.author.id in self.context.bot.owner_ids or self.context.author.id == interaction.user.id:
			return True

		await interaction.response.send_message("You did not invoke the interaction, please invoke your own command.", ephemeral=True)
		return False

	async def on_timeout(self) -> None:
		self.value = None
class AutoComplete:
	"""
    Represents an autocompletion of an argument.

    Attributes
    ----------
    choices: List[:class:`Option`]
      An array of options.

	Example
	-------
	@cmd.autocomplete('param')
	async def param_auto(ctx, user_input) -> Optional[str]:
		valid_choces: List[str] = ...
		value = await ctx.prompt_autocomplete(
			text="Sorry, that's not one of the valid params! Select one of these:",
			choices=valid_choices,
			timeout=25,
		)
		return value
    """

	__slots__: Tuple[str, ...] = ("choices", "timeout", "_timeout",)
	
	def __init__(self, func: Callable, timeout: Optional[int] = None) -> None:
		self.callback: Callable = func
		self._timeout = timeout
		
	@property
	def timeout(self):
		return self._timeout
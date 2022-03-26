from typing import Callable, Optional, TypeVar, Generic, List

import discord
from discord.ext import commands

AC = TypeVar("AC", bound="AutoComplete")


class Dropdown(discord.ui.Select['DropdownView']):
    def __init__(self, options: List[discord.SelectOption]):
        options = options
        super().__init__(placeholder="Choose an option...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.values[0]
        self.view.stop()
        try:
            await interaction.message.delete()
        except Exception as e:
            return e

class DropdownView(discord.ui.View):
    def __init__(self, context: commands.Context, options: List[discord.SelectOption], timeout: Optional[int] = 30):
        super().__init__(timeout=timeout)
        self.add_item(Dropdown(options))
        self.context = context
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.context.author.id in self.context.bot.owner_ids or self.context.author.id == interaction.user.id:
            return True

        await interaction.response.defer()
        return False

    async def on_timeout(self) -> None:
        self.value = None


class AutoComplete(Generic[AC]):
    """
    Represents an autocompletion of an argument.

    Parameters
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

    def __init__(self, func: Callable, timeout: Optional[int] = None) -> None:
        self.callback: Callable = func
        self._timeout = timeout

    @property
    def timeout(self):
        return self._timeout

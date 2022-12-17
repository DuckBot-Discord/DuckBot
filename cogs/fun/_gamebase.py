import discord
from discord import Interaction

from helpers.context import CustomContext


class LookingForButton(discord.ui.Button):
    sep = '\u2001'

    def __init__(self, disabled: bool = False, label: str = None):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label=(label or f'{self.sep*11}Join this game!{self.sep*11}'),
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LookingToPlay = self.view
        if interaction.user and interaction.user.id == view.ctx.author.id:
            return await interaction.response.send_message(
                '**Congratulations, you played yourself!**\nWait... You can\'t...', ephemeral=True
            )
        view.value = interaction.user
        view.stop()


class RequestToPlayView(discord.ui.View):
    def __init__(self, ctx: CustomContext, member: discord.Member, game: str = 'Rock Paper Scissors'):
        super().__init__(timeout=15)
        self.member = member
        self.ctx = ctx
        self.message: discord.Message = None
        self.value: bool = None
        self.game = game

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id in (self.ctx.author.id, self.member.id):
            return True
        await interaction.response.defer()

    @discord.ui.button(label='Confirm', emoji='✅')
    async def confirm(self, interaction: Interaction, _):
        if interaction.user.id == self.member.id:
            await interaction.response.defer()
            self.clear_items()
            self.message.content = None
            self.value = True
            self.stop()
        else:
            await interaction.response.defer()

    @discord.ui.button(label='Deny', emoji='❌')
    async def deny(self, interaction: Interaction, _):
        if interaction.user.id == self.ctx.author.id:
            await interaction.response.edit_message(
                content=f"{self.ctx.author.mention}, you have cancelled the challenge.", view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"{self.ctx.author.mention}, {self.member} has denied your challenge.", view=None
            )
        self.value = False
        self.stop()

    async def start(self):
        self.message = await self.ctx.send(
            f"{self.member.mention}, {self.ctx.author} is challenging you to at {self.game}, do you accept?", view=self
        )

    async def on_timeout(self) -> None:
        self.clear_items()
        await self.message.edit(content=f"{self.ctx.author.mention}, did not respond in time to the challenge!")
        self.stop()


class CancelGame(discord.ui.Button):
    def __init__(self, disabled: bool = False, label: str = None):
        super().__init__(style=discord.ButtonStyle.red, label='cancel', row=2, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: LookingToPlay = self.view
        if interaction.user.id == view.ctx.author.id:
            view.value = None
            for item in view.children:
                item.disabled = True
                item.label = item.label.replace('cancel', 'Cancelled!').replace('Join this game!\u2001', 'Game has ended!')
            await view.message.edit(view=view)
            view.stop()
        else:
            await interaction.response.send_message('Only the game author can do that action!', ephemeral=True)


class LookingToPlay(discord.ui.View):
    def __init__(self, timeout: int = 120, label: str = None):
        super().__init__(timeout=timeout)
        self.message: discord.Message = None
        self.value: discord.User = None
        self.ctx: CustomContext = None
        self.add_item(LookingForButton(label=label))
        self.add_item(CancelGame())

    async def on_timeout(self) -> None:
        for button in self.children:
            button.disabled = True
            button.label = button.label.replace('Join this game!\u2001', 'Game has ended!')
        await self.message.edit(content='⏰ | **Timed out!** - game has ended.', view=self)

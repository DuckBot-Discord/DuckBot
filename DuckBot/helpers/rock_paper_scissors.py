import asyncio

import discord
from discord import Interaction

from DuckBot.helpers.context import CustomContext


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
    async def confirm(self, _, interaction: Interaction):
        if interaction.user.id == self.member.id:
            await interaction.response.defer()
            self.clear_items()
            self.message.content = None
            self.value = True
            self.stop()
        else:
            await interaction.response.defer()

    @discord.ui.button(label='Deny', emoji='❌')
    async def deny(self, _, interaction: Interaction):
        if interaction.user.id == self.ctx.author.id:
            await interaction.response.edit_message(content=f"{self.ctx.author.mention}, you have cancelled the challenge.", view=None)
        else:
            await interaction.response.edit_message(content=f"{self.ctx.author.mention}, {self.member} has denied your challenge.", view=None)
        self.value = False
        self.stop()

    async def start(self):
        self.message = await self.ctx.send(f"{self.member.mention}, {self.ctx.author} is challenging you to at {self.game}, do you accept?", view=self)

    async def on_timeout(self) -> None:
        self.clear_items()
        await self.message.edit(content=f"{self.ctx.author.mention}, did not respond in time to the challenge!")
        self.stop()


class RockPaperScissors(discord.ui.View):

    def __init__(self, ctx: CustomContext, player1: discord.Member, player2: discord.Member):
        super().__init__()
        self.message: discord.Message = None
        self.ctx: CustomContext = ctx
        self.player1: discord.Member = player1
        self.player2: discord.Member = player2
        self.responses = {}

    @discord.ui.button(label='Rock', emoji='🗿')
    async def rock(self, button: discord.ui.Button, interaction: Interaction):
        await self.update_message(button, interaction)

    @discord.ui.button(label='Paper', emoji='📄')
    async def paper(self, button: discord.ui.Button, interaction: Interaction):
        await self.update_message(button, interaction)

    @discord.ui.button(label='Scissors', emoji='✂')
    async def scissors(self, button: discord.ui.Button, interaction: Interaction):
        await self.update_message(button, interaction)

    async def update_message(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.responses[interaction.user.id] = button.label

        embed = self.message.embeds[0].copy()
        embed.description = f"> {self.ctx.default_tick(self.player1.id in self.responses)} {self.player1.display_name}" \
                            f"\n> {self.ctx.default_tick(self.player2.id in self.responses)} {self.player2.display_name}"

        await self.message.edit(embed=embed)

        if len(self.responses) == 2:
            response = self.check_winner()
            embed.description = f"> ✅ **{self.player1.display_name}** chose **{self.responses[self.player1.id]}**" \
                                f"\n> ✅ **{self.player2.display_name}** chose **{self.responses[self.player2.id]}**" \
                                f"\n" \
                                f"\n{response}"

            self.disable_items()
            await self.message.edit(embed=embed, view=self)
            self.stop()

    def disable_items(self):
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not interaction.user or interaction.user.id not in (self.player1.id, self.player2.id):
            await interaction.response.send_message('You are not a part of this game!', ephemeral=True)
            return False
        if interaction.user.id in self.responses:
            await interaction.response.send_message(f'You already selected **{self.responses[interaction.user.id]}**, sorry!', ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.placeholder = "Timed out! Please try again."
            item.disabled = True
        await self.message.edit(view=self)

    def check_winner(self):
        mapping = {
            'Rock': 0,
            'Paper': 1,
            'Scissors': 2
        }
        win_1 = f'**{self.responses[self.player1.id]}** beats **{self.responses[self.player2.id]}** - **{self.player1.display_name}** wins! 🎉'
        win_2 = f'**{self.responses[self.player2.id]}** beats **{self.responses[self.player1.id]}** - **{self.player2.display_name}** wins! 🎉'
        tie = f'It\'s a **tie**! both players lose. 👔'

        if self.responses[self.player1.id] == self.responses[self.player2.id]:
            return tie
        elif (mapping[self.responses[self.player1.id]] + 1) % 3 == mapping[self.responses[self.player2.id]]:
            return win_2
        else:
            return win_1

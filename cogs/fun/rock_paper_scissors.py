import discord
from discord import Interaction
from discord.ext import commands

from ._base import FunBase
from ._gamebase import LookingToPlay, RequestToPlayView
from ...helpers import constants
from ...helpers.context import CustomContext


class RockPaperScissors(discord.ui.View):

    def __init__(self, ctx: CustomContext, player1: discord.Member, player2: discord.Member):
        super().__init__()
        self.message: discord.Message = None  # type: ignore
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


class RockPaperScissorsCommand(FunBase):

    @commands.command(name='rock-paper-scissors', aliases=['rps', 'rock_paper_scissors'], usage='[to-invite]')
    async def rock_paper_scissors(self, ctx: CustomContext, to_invite: discord.Member = None):
        """Starts a rock-paper-scissors game."""
        player1 = ctx.author
        if not to_invite:
            embed = discord.Embed(description=f'🔎 | **{ctx.author.display_name}**'
                                              f'\n👀 | User is looking for someone to play **Rock-Paper-Scissors**')
            embed.set_thumbnail(url=constants.SPINNING_MAG_GLASS)
            embed.set_author(name='Rock-Paper-Scissors', icon_url='https://i.imgur.com/ZJvaA90.png')

            sep = '\u2001'
            view = LookingToPlay(timeout=120, label=f'{sep * 13}Join this game!{sep * 13}')
            view.ctx = ctx
            view.message = await ctx.send(embed=embed,
                                          view=view, footer=False)
            await view.wait()
            player2 = view.value
        else:
            view = RequestToPlayView(ctx, to_invite)
            await view.start()
            await view.wait()
            if view.value:
                player2 = to_invite
            else:
                player2 = None

        if player2:
            embed = discord.Embed(description=f"> ❌ {player1.display_name}"
                                              f"\n> ❌ {player2.display_name}",
                                  colour=discord.Colour.blurple())
            embed.set_author(name='Rock-Paper-Scissors', icon_url='https://i.imgur.com/ZJvaA90.png')
            rps = RockPaperScissors(ctx, player1, player2)
            rps.message = await view.message.edit(embed=embed, content=None, view=rps)
            await rps.wait()

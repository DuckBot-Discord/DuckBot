import asyncio

import discord
from discord import Interaction
from discord.ext import commands

from DuckBot.__main__ import DuckBot
from DuckBot.helpers.context import CustomContext
from DuckBot.helpers.tictactoe import LookingToPlay


class ObjectSelector(discord.ui.Select):
    def __init__(self):
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Rock', description='Rock beats Scissors', emoji='🗿'),
            discord.SelectOption(label='Paper', description='Paper beats Rock', emoji='📄'),
            discord.SelectOption(label='Scissors', description='Scissors beats Paper', emoji='✂')
        ]
        super().__init__(placeholder='Select your object...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RockPaperScissors = self.view
        view.responses[interaction.user.id] = self.values[0]

        embed = view.message.embeds[0].copy()
        embed.description = f"> {view.ctx.default_tick(view.player1.id in view.responses)} {view.player1.display_name}" \
                            f"\n> {view.ctx.default_tick(view.player2.id in view.responses)} {view.player2.display_name}"

        await view.message.edit(embed=embed)

        if len(view.responses) == 2:
            response = view.check_winner()
            embed.description = f"> ✅ **{view.player1.display_name}** chose **{view.responses[view.player1.id]}**" \
                                f"\n> ✅ **{view.player2.display_name}** chose **{view.responses[view.player2.id]}**" \
                                f"\n" \
                                f"\n{response}"

            for item in view.children:
                if isinstance(item, discord.ui.Select):
                    item.placeholder = "Game has ended!"
                item.disabled = True

            await asyncio.sleep(1)
            await view.message.edit(embed=embed, view=view)


class RockPaperScissors(discord.ui.View):

    def __init__(self, ctx: CustomContext, player1: discord.Member, player2: discord.Member):
        super().__init__()
        self.message: discord.Message = None
        self.ctx: CustomContext = ctx
        self.player1: discord.Member = player1
        self.player2: discord.Member = player2
        self.responses = {}
        self.add_item(ObjectSelector())

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


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    @commands.command()
    async def rps(self, ctx: CustomContext):
        embed = discord.Embed(description=f'🔎 | **{ctx.author.display_name}**'
                                          f'\n👀 | User is looking for someone to play **Rock-Paper-Scissors**')
        embed.set_thumbnail(url='https://i.imgur.com/DZhQwnD.gif')
        embed.set_author(name='Rock-Paper-Scissors', icon_url='https://i.imgur.com/ZJvaA90.png')

        sep = '\u2001'
        view = LookingToPlay(timeout=120, label=f'{sep*13}Join this game!{sep*13}')
        view.ctx = ctx
        view.message = await ctx.send(embed=embed,
                                      view=view, footer=False)
        await view.wait()
        player1 = ctx.author
        player2 = view.value

        if player2:
            embed = discord.Embed(description=f"> ❌ {player1.display_name}"
                                              f"\n> ❌ {player2.display_name}",
                                  colour=discord.Colour.blurple())
            embed.set_author(name='Rock-Paper-Scissors', icon_url='https://i.imgur.com/ZJvaA90.png')
            rps = RockPaperScissors(ctx, player1, player2)
            rps.message = await view.message.edit(embed=embed, view=rps)

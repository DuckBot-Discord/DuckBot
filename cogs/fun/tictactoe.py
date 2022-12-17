import random

import discord
import typing

from discord.ext import commands

from ._base import FunBase
from ._gamebase import RequestToPlayView, LookingToPlay
from helpers import constants
from helpers.context import CustomContext


class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='  ', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X_won, view.O_won):
            return

        if view.current_player == view.player1:
            self.style = discord.ButtonStyle.blurple
            self.label = '\U0001f1fd'
            self.disabled = True
            view.board[self.y][self.x] = view.X_won
        else:
            self.style = discord.ButtonStyle.red
            self.label = '🅾'
            self.disabled = True
            view.board[self.y][self.x] = view.O_won

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X_won:
                content = f'\U0001f1fd | **{view.current_player.name}** won! 🎉'
            elif winner == view.O_won:
                content = f'🅾 | **{view.current_player.name}** won! 🎉'
            else:
                content = f"\U0001f454 | It's a tie! both players loose!"

            for child in view.children:
                child.disabled = True

            view.stop()

        else:
            if view.current_player == view.player1:
                view.current_player = view.player2
                content = f"🅾 | It's **{view.current_player.name}**'s turn"
            else:
                view.current_player = view.player1
                content = f"\U0001f1fd | It's **{view.current_player.name}**'s turn"

        await interaction.response.edit_message(content=content, view=view)


class TicTacToe(discord.ui.View):
    children: typing.List[TicTacToeButton]
    X_won = -1
    O_won = 1
    Tie = 2

    def __init__(self, ctx: CustomContext, player1: discord.Member, player2: discord.Member, starter: discord.User):
        super().__init__()
        self.current_player = starter
        self.ctx: CustomContext = ctx
        self.player1: discord.Member = player1
        self.player2: discord.Member = player2
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O_won
            elif value == -3:
                return self.X_won

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O_won
            elif value == -3:
                return self.X_won

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O_won
        elif diag == -3:
            return self.X_won

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O_won
        elif diag == -3:
            return self.X_won

        # If we're here, we need to check if a tie was made
        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.current_player.id:
            return True
        elif interaction.user and interaction.user.id in (self.player1.id, self.player2.id):
            await interaction.response.send_message('Not your turn!', ephemeral=True)
        elif interaction.user:
            await interaction.response.send_message('You aren\'t a part of this game!', ephemeral=True)
        return False


class TicTacToeCommand(FunBase):
    @commands.max_concurrency(1, commands.BucketType.user, wait=False)
    @commands.command(aliases=['ttt', 'tic'])
    async def tictactoe(self, ctx: CustomContext, to_invite: discord.Member = None):
        """Starts a tic-tac-toe game."""
        player1 = ctx.author
        if not to_invite:
            embed = discord.Embed(
                description=f'🔎 | **{ctx.author.display_name}**' f'\n👀 | User is looking for someone to play **Tic-Tac-Toe**'
            )
            embed.set_thumbnail(url=constants.SPINNING_MAG_GLASS)
            embed.set_author(name='Tic-Tac-Toe', icon_url='https://i.imgur.com/SrRrarG.png')
            view = LookingToPlay(timeout=120)
            view.ctx = ctx
            view.message = await ctx.send(embed=embed, view=view, footer=False)
            await view.wait()
            player2 = view.value
        else:
            view = RequestToPlayView(ctx, to_invite, game='Tic-Tac-Toe')
            await view.start()
            await view.wait()
            if view.value:
                player2 = to_invite
            else:
                player2 = None

        if player2:
            starter = random.choice([player1, player2])
            ttt = TicTacToe(ctx, player1, player2, starter=starter)
            ttt.message = await view.message.edit(content=f'#️⃣ | **{starter.name}** goes first', view=ttt, embed=None)
            await ttt.wait()

import random

import discord
from discord.ext import commands
from typing import List

from DuckBot.__main__ import DuckBot, CustomContext


def setup(bot):
    bot.add_cog(Test(bot))


class LookingForButton(discord.ui.Button):
    def __init__(self, disabled: bool = False):
        super().__init__(style=discord.ButtonStyle.green, label='\u200b          Click to play          \u200b',
                         disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: Confirm = self.view
        view.value = interaction.user
        await view.message.edit(content=f'**{interaction.user}** is now playing '
                                        f'Tic Tac Toe with **{view.ctx.author}**', view=None)
        view.stop()


class Confirm(discord.ui.View):
    def __init__(self, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.message: discord.Message = None
        self.value: discord.User = None
        self.ctx: CustomContext = None
        self.add_item(LookingForButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id != self.ctx.author.id:
            return True
        await interaction.response.send_message('**Congratulations, you player yourself!**\nWait... You can\'t...',
                                                ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        await self.message.edit(content='Timed out! Nobody is playing', view=None)


# Defines a custom button that contains the logic of the game.
# The ['TicTacToe'] bit is for type hinting purposes to tell your IDE or linter
# what the type of `self.view` is. It is not required.
class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        # A label is required, but we don't need one so a zero-width space is used
        # The row parameter tells the View which row to place the button under.
        # A View can only contain up to 5 rows -- each row can only have 5 buttons.
        # Since a Tic Tac Toe grid is 3x3 that means we have 3 rows and 3 columns.
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.player1:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.player2
            content = f"It is now **{view.current_player.name}**'s turn"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.player1
            content = f"It is now **{view.current_player.name}**'s turn"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X or winner == view.O:
                content = f'**{view.current_player.name}** won!'
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)


# This is our actual board View
class TicTacToe(discord.ui.View):
    # This tells the IDE or linter that all our children will be TicTacToeButtons
    # This is not required
    children: List[TicTacToeButton]
    X = -1
    O = 1
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

        # Our board is made up of 3 by 3 TicTacToeButtons
        # The TicTacToeButton maintains the callbacks and helps steer
        # the actual game.
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    # This method checks for the board winner -- it is used by the TicTacToeButton
    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        # If we're here, we need to check if a tie was made
        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.current_player.id:
            return True
        await interaction.response.send_message('Not your turn!', ephemeral=True)
        return False


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    @commands.command(aliases=['ttt', 'tic'])
    async def tictactoe(self, ctx: CustomContext):
        """Starts a tic-tac-toe game."""
        player1 = ctx.author
        view = Confirm()
        view.ctx = ctx
        view.message = await ctx.send(f'**{ctx.author}** is looking to play Tic Tac Toe', view=view)
        await view.wait()
        player2 = view.value
        if player2:
            starter = random.choice([player1, player2])
            ttt = TicTacToe(ctx, player1, player2, starter=starter)
            ttt.message = await ctx.send(f'Tic Tac Toe: **{starter.name}** goes first', view=ttt)

from .apis import Apis
from .basic import BasicFun
from .embed import EmbedMaker
from .fun_text import FancyText
from .rock_paper_scissors import RockPaperScissorsCommand
from .tictactoe import TicTacToeCommand
from .typerace import TypeRace
from .vc_games import DiscordActivities

import os

optional = []

if os.getenv('ASYNC_PRAW_CID'):
    from .reddit import Reddit

    optional.append(Reddit)


class Fun(
    Apis,
    BasicFun,
    EmbedMaker,
    FancyText,
    RockPaperScissorsCommand,
    TicTacToeCommand,
    TypeRace,
    DiscordActivities,
    *optional,
):
    """
    🤪 General entertainment commands, and all other commands that don't fit within other categories.
    """

    select_emoji = "🤪"
    select_brief = "General Entertainment Commands"


async def setup(bot):
    await bot.add_cog(Fun(bot))

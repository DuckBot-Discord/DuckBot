from .apis import Apis
from .basic import BasicFun
from .embed import EmbedMaker
from .fun_text import FancyText
from .reddit import Reddit
from .rock_paper_scissors import RockPaperScissorsCommand
from .tictactoe import TicTacToeCommand
from .typerace import TypeRace
from .vc_games import DiscordActivities


class Fun(
    Apis,
    BasicFun,
    EmbedMaker,
    FancyText,
    Reddit,
    RockPaperScissorsCommand,
    TicTacToeCommand,
    TypeRace,
    DiscordActivities,
):
    """
    🤪 General entertainment commands, and all other commands that don't fit within other categories.
    """

    select_emoji = "🤪"
    select_brief = "General Entertainment Commands"


async def setup(bot):
    await bot.add_cog(Fun(bot))

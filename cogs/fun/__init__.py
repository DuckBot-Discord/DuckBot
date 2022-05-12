from .app_commands import *


class Fun(ApplicationApis, emoji="🤪", brief="Fun commands."):
    """All sorts of entertainment commands. These range from image manipulation stuff,
    sending random images, games, etc. Everything that is fun is here!"""

    ...


async def setup(bot):
    await bot.add_cog(Fun(bot))

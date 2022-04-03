from .app_commands import *

class Fun(ApplicationApis, emoji="🤪"):
    """ Fun commands. """
    ...

async def setup(bot):
    bot.add_cog(Fun(bot))

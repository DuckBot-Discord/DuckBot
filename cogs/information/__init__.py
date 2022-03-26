from .user_info import UserInfo
from .perms import PermsViewer

class Info(UserInfo, PermsViewer, emoji='📜'):
    """ Information commands. """
    ...

async def setup(bot):
    await bot.add_cog(Info(bot))

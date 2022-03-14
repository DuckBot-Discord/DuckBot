from .user_info import UserInfo

class Info(UserInfo):
    """ Information commands. """
    ...

async def setup(bot):
    await bot.add_cog(Info(bot))

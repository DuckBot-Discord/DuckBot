from .user_info import UserInfo

class Info(UserInfo):
    """ Information commands. """
    ...

def setup(bot):
    bot.add_cog(Info(bot))

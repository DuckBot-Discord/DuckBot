from discord.ext import commands

class NotOSP(commands.CheckFailure):
    pass

def is_osp_server():
    def predicate(ctx):
        # a function that takes ctx as it's only arg, that returns
        # a truethy or falsey value, or raises an exception
        if ctx.guild.id == 831897006812561409: return True
        else: raise NotOSP("**This command is restricted to OSP!**\ndiscord.gg/tkuDSz6wsc")
    return commands.check(predicate)

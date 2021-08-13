from discord.ext import commands
import yaml

def is_stylized_mod():
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage(message=ctx.message):
            return
        for role in ctx.author.roles:
            if role.id in
        # a function that takes ctx as it's only arg, that returns
        # a truethy or falsey value, or raises an exception
        if ctx.guild.id == 831897006812561409: return True
        else: raise NotOSP("**This command is restricted to OSP!**\ndiscord.gg/tkuDSz6wsc")
    return commands.check(predicate)





        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

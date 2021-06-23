
import  discord, asyncio
from discord.ext import commands

class handler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(5)
        try:
            await ctx.message.delete()
            return
        except: return

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, discord.ext.commands.errors.CheckFailure):
            await self.perms_error(ctx)
            return
        if isinstance(error, discord.ext.commands.errors.CommandNotFound):
#            await ctx.message.add_reaction('❓')
#            await asyncio.sleep(2)
#            await ctx.message.remove_reaction('❓', self.bot.user)
            return
        if isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            await ctx.send("command is on cooldown")

        if ctx.command:
            await self.bot.get_channel(847943387083440128).send(f"""```{ctx.command} command raised an error:
{error}```""")
        else:
            await self.bot.get_channel(847943387083440128).send(f"""```{error}```""")
        raise error
def setup(bot):
    bot.add_cog(handler(bot))

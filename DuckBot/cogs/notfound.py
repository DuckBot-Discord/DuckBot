
import  discord
from discord.ext import commands

class handler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, discord.ext.commands.errors.CommandNotFound) or isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            return

        if ctx.command:
            await self.bot.get_channel(847943387083440128).send(f"""```{ctx.command} command raised an error:
{error}```""")
        else:
            await self.bot.get_channel(847943387083440128).send(f"""```{error}```""")


        if ctx.author.id == 349373972103561218:
            if ctx.command in ['reload','load','unload']: return
            embed=discord.Embed(description=
f"""**An error ocurred while handling the command `{ctx.command}`**
```{error}```
""", color=ctx.me.color)
            await ctx.send(embed=embed)
        raise error
def setup(bot):
    bot.add_cog(handler(bot))

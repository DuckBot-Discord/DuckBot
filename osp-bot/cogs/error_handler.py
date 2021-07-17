
import  discord, asyncio
from discord.ext import commands
from discord.ext.commands import BucketType

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
            embed = discord.Embed(color=0xD7342A, description = f'Please try again in {round(error.retry_after, 2)} seconds')
            embed.set_author(name = 'Command is on cooldown!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.cooldown.type == BucketType.default: per = ""
            if error.cooldown.type == BucketType.user: per = "per user"
            if error.cooldown.type == BucketType.guild: per = "per server"
            if error.cooldown.type == BucketType.channel: per = "per channel"
            if error.cooldown.type == BucketType.member: per = "per member"
            if error.cooldown.type == BucketType.category: per = "per category"
            if error.cooldown.type == BucketType.role: per = "per role"

            embed.set_footer(text=f"{error.cooldown.rate} per {error.cooldown.per}s {per}")
            await ctx.send(embed=embed)
            return

        if isinstance(error, discord.ext.commands.errors.MaxConcurrencyReached):
            embed = discord.Embed(color=0xD7342A, description = f"Please try again once you are done running the command")
            embed.set_author(name = 'Command is alrady running!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.per == BucketType.default: per = ""
            if error.per == BucketType.user: per = "per user"
            if error.per == BucketType.guild: per = "per server"
            if error.per == BucketType.channel: per = "per channel"
            if error.per == BucketType.member: per = "per member"
            if error.per == BucketType.category: per = "per category"
            if error.per == BucketType.role: per = "per role"

            embed.set_footer(text=f"limit is {error.number} command(s) running {per}")
            await ctx.send(embed=embed)
            return

        if ctx.command:
            await self.bot.get_channel(847943387083440128).send(f"""```{ctx.command} command raised an error:
{error}```""")
        else:
            await self.bot.get_channel(847943387083440128).send(f"""```{error}```""")
        raise error
def setup(bot):
    bot.add_cog(handler(bot))

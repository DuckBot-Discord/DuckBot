
import  discord, asyncio
from discord.ext import commands
from discord.ext.commands import BucketType
from errors import HigherRole

class handler(commands.Cog):
    """🆘 Handle them errors 👀"""
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

        embed = discord.Embed(color=0xD7342A)
        embed.set_author(name = 'Missing permissions!', icon_url='https://i.imgur.com/OAmzSGF.png')

        if isinstance(error, commands.MissingPermissions):
            text=f"You're missing the following permissions: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description=text
                await ctx.send(embed=embed)
            except:
                try: await ctx.send(text)
                except: pass
            return

        elif isinstance(error, commands.BotMissingPermissions):
            text=f"I'm missing the following permissions: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description=text
                await ctx.send(embed=embed)
            except:
                try: await ctx.send(text)
                except: pass
            return

        elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            embed = discord.Embed(color=0xD7342A, description = f'Please try again in {round(error.retry_after, 2)} seconds')
            embed.set_author(name = 'Command is on cooldown!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.cooldown.type == BucketType.default: per = ""
            if error.cooldown.type == BucketType.user: per = "per user"
            if error.cooldown.type == BucketType.guild: per = "per server"
            if error.cooldown.type == BucketType.channel: per = "per channel"
            if error.cooldown.type == BucketType.member: per = "per member"
            if error.cooldown.type == BucketType.category: per = "per category"
            if error.cooldown.type == BucketType.role: per = "per role"

            embed.set_footer(text=f"cooldown: {error.cooldown.rate} per {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        elif isinstance(error, HigherRole):
            await ctx.send("error handled")

        elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
            pass

        elif isinstance(error, discord.ext.commands.errors.CheckFailure):
            await self.perms_error(ctx)

        else:
            await self.bot.wait_until_ready()
            await self.bot.get_channel(847943387083440128).send(f"""```{ctx.command} command raised an error:
    {error}```""")
            raise error

def setup(bot):
    bot.add_cog(handler(bot))

import  discord, asyncio, typing
from discord.ext import commands
from discord.ext.commands import BucketType
import custom_errors

class handler(commands.Cog):
    """🆘 Handle them errors 👀"""
    def __init__(self, bot):
        self.bot = bot

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        try: await ctx.message.delete(delay=5)
        except: pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, discord.ext.commands.CheckAnyFailure):
            for e in error.errors:
                if error != commands.NotOwner:
                    error = e
                    break

        if isinstance(error, discord.ext.commands.BadUnionArgument):
            for e in error.errors:
                error = e
                break

        embed = discord.Embed(color=0xD7342A)
        embed.set_author(name = 'Missing permissions!', icon_url='https://i.imgur.com/OAmzSGF.png')

        if isinstance(error, commands.NotOwner):
            await ctx.send(f"you must own `{ctx.me.display_name}` to use `{ctx.command}`")
            return

        if isinstance(error, commands.TooManyArguments):
            await ctx.send(f"Too many arguments passed to the command!")
            return

        if isinstance(error, discord.ext.commands.MissingPermissions):
            text=f"You're missing the following permissions: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description=text
                await ctx.send(embed=embed)
            except:
                try: await ctx.send(text)
                except: pass
            return

        if isinstance(error, discord.ext.commands.BotMissingPermissions):
            text=f"I'm missing the following permissions: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description=text
                await ctx.send(embed=embed)
            except:
                try: await ctx.send(text)
                except: pass
            return

        elif isinstance(error, discord.ext.commands.MissingRequiredArgument):
            missing=f"{str(error.param).split(':')[0]}"
            command = f"{ctx.prefix}{ctx.command} {ctx.command.signature}"
            separator = (' ' * (len(command.split(missing)[0])-1))
            indicator = ('^' * (len(missing)+2))
            print(f"`{separator}`  `{indicator}`")
            print(error.param)
            print()
            await ctx.send(f"""```
{command}
{separator}{indicator}
{missing} is a required argument that is missing.
```""")

        elif isinstance(error, commands.errors.PartialEmojiConversionFailure):
            await ctx.send(f"`{error.argument}` is not a valid Custom Emoji")

        elif isinstance(error, commands.errors.CommandOnCooldown):
            embed = discord.Embed(color=0xD7342A, description = f'Please try again in {round(error.retry_after, 2)} seconds')
            embed.set_author(name = 'Command is on cooldown!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.type == BucketType.default: per = ""
            elif error.type == BucketType.user: per = "per user"
            elif error.type == BucketType.guild: per = "per server"
            elif error.type == BucketType.channel: per = "per channel"
            elif error.type == BucketType.member: per = "per member"
            elif error.type == BucketType.category: per = "per category"
            elif error.type == BucketType.role: per = "per role"

            embed.set_footer(text=f"cooldown: {error.cooldown.rate} per {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        elif isinstance(error, custom_errors.NoQuotedMessage):
            await ctx.send("<:reply:824240882488180747> Missing reply!")
            return

        elif isinstance(error, custom_errors.NoEmojisFound):
            await ctx.send("I couldn't find any emojis there.")
            return

        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"I couldn't fin `{error.argument}` in this server")

        elif isinstance(error, commands.errors.UserNotFound):
            await ctx.send(f"I've searched far and wide, but `{error.argument}` doesn't seem to be a member discord user...")

        elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
            pass

        else:
            await self.bot.wait_until_ready()
            await self.bot.get_channel(847943387083440128).send(f"""```{ctx.command} command raised an error:
    {error}```""")
            raise error

def setup(bot):
    bot.add_cog(handler(bot))

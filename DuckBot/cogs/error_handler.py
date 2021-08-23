import logging

import errors
import discord
from discord.ext import commands
from discord.ext.commands import BucketType


def setup(bot):
    bot.add_cog(Handler(bot))


class Handler(commands.Cog, name='Handler'):
    """
    🆘 Handle them errors 👀
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        print(error)
        ignored = (
            commands.CommandNotFound,
        )
        if isinstance(error, ignored):
            return

        if isinstance(error, discord.ext.commands.CheckAnyFailure):
            for e in error.errors:
                if error != commands.NotOwner:
                    error = e
                    break

        if isinstance(error, discord.ext.commands.BadUnionArgument):
            if e.errors:
                error = e.errors[0]

        embed = discord.Embed(color=0xD7342A)
        embed.set_author(name='Missing permissions!', icon_url='https://i.imgur.com/OAmzSGF.png')

        if isinstance(error, commands.NotOwner):
            return await ctx.send(f"you must own `{ctx.me.display_name}` to use `{ctx.command}`")

        if isinstance(error, commands.TooManyArguments):
            return await ctx.send(f"Too many arguments passed to the command!")

        if isinstance(error, discord.ext.commands.MissingPermissions):
            text = f"You're missing the following permissions: \n**{', '.join(error.missing_perms)}**"
            embed.description = text
            try:
                return await ctx.send(embed=embed)
            except:
                try:
                    return await ctx.send(text)
                except:
                    pass
                finally:
                    return

        if isinstance(error, discord.ext.commands.BotMissingPermissions):
            text = f"I'm missing the following permissions: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description = text
                await ctx.send(embed=embed)
            except:
                pass
            finally:
                return

        elif isinstance(error, discord.ext.commands.MissingRequiredArgument):
            missing = f"{str(error.param).split(':')[0]}"
            command = f"{ctx.clean_prefix}{ctx.command} {ctx.command.signature}"
            command = f"{ctx.clean_prefix}{ctx.command} {ctx.command.signature}"
            separator = (' ' * (len(command.split(missing)[0]) - 1))
            indicator = ('^' * (len(missing) + 2))

            logging.info(f"`{separator}`  `{indicator}`")
            logging.info(error.param)
            print()

            return await ctx.send(
                f"```{command}\n{separator}{indicator}\n{missing} is a required argument that is missing.\n```")

        elif isinstance(error, commands.errors.PartialEmojiConversionFailure):
            return await ctx.send(f"`{error.argument}` is not a valid Custom Emoji")

        elif isinstance(error, commands.errors.CommandOnCooldown):
            embed = discord.Embed(color=0xD7342A,
                                  description=f'Please try again in {round(error.retry_after, 2)} seconds')
            embed.set_author(name='Command is on cooldown!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.type == BucketType.default:
                per = ""
            elif error.type == BucketType.user:
                per = "per user"
            elif error.type == BucketType.guild:
                per = "per server"
            elif error.type == BucketType.channel:
                per = "per channel"
            elif error.type == BucketType.member:
                per = "per member"
            elif error.type == BucketType.category:
                per = "per category"
            elif error.type == BucketType.role:
                per = "per role"

            embed.set_footer(text=f"cooldown: {error.cooldown.rate} per {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        elif isinstance(error, errors.NoQuotedMessage):
            return await ctx.send("<:reply:824240882488180747> Missing reply!")

        elif isinstance(error, errors.NoEmojisFound):
            return await ctx.send("I couldn't find any emojis there.")

        elif isinstance(error, commands.errors.MemberNotFound):
            return await ctx.send(f"I couldn't fin `{error.argument}` in this server")

        elif isinstance(error, commands.errors.UserNotFound):
            return await ctx.send(
                f"I've searched far and wide, but `{error.argument}` doesn't seem to be a member discord user...")

        await self.bot.wait_until_ready()
        await self.bot.get_channel(847943387083440128).send(f"```\n{ctx.command} command raised an error:{error}\n```")
        raise error

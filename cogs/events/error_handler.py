import copy
import difflib
import io
import itertools
import logging
import traceback

import discord
from discord.ext import commands
from discord.ext.commands import BucketType

import errors
from bot import CustomContext
from helpers import constants
from helpers import time_inputs
from ._base import EventsBase

warned = []


class ErrorHandler(EventsBase):
    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx: CustomContext, error):
        error = getattr(error, "original", error)
        ignored = errors.NoHideout

        if isinstance(error, ignored):
            return

        if isinstance(error, errors.UserBlacklisted):
            if ctx.author.id not in warned:
                warned.append(ctx.author.id)
                reason = await self.bot.db.fetchval('SELECT reason FROM blacklist WHERE user_id = $1', ctx.author.id)
                return await ctx.send(
                    "Sorry, you are blacklisted from using DuckBot" + (f" for {reason}" if reason else "") + "."
                )
            else:
                return

        if isinstance(error, errors.BotUnderMaintenance):
            return await ctx.send(self.bot.maintenance or 'I am under maintenance... sorry!')

        if isinstance(error, errors.EconomyNotSetup):
            return await ctx.send(f"❗ **You do not have a wallet!** Start with the `{ctx.clean_prefix}eco start` command.")

        if isinstance(error, errors.AccountNotFound):
            return await ctx.send(f"❗ Sorry but **{error.user}** does not have a wallet!")

        if isinstance(error, errors.AccountAlreadyExists):
            return await ctx.send(f"❗ Sorry but **{error.user}** already has a wallet!")

        if isinstance(error, errors.EconomyOnCooldown):
            messages = {
                errors.CooldownType.WORK: "work",
                errors.CooldownType.DAILY: "get your daily reward",
                errors.CooldownType.WEEKLY: "get your weekly reward",
                errors.CooldownType.MONTHLY: "get your monthly reward",
            }
            return await ctx.send(
                f"❗ You can **{messages[error.cooldown_type]}** again **in {time_inputs.human_timedelta(error.next_run, brief=True)}**."
            )

        if isinstance(error, errors.WalletInUse):
            return await ctx.send(
                f"❗ Sorry but **{error.user}**\'s wallet is currently in use... Please wait and try again later!"
            )

        if isinstance(error, commands.CommandNotFound):
            if self.bot.maintenance is not None or ctx.author.id in self.bot.blacklist or ctx.prefix == '':
                return
            command_names = []
            for command in [c for c in self.bot.commands]:
                # noinspection PyBroadException
                try:
                    if await command.can_run(ctx):
                        command_names.append([command.name] + command.aliases)
                except:
                    continue

            command_names = list(itertools.chain.from_iterable(command_names))

            matches = difflib.get_close_matches(ctx.invoked_with, command_names)

            if matches:
                confirm = await ctx.confirm(
                    message=f"Sorry, but the command **{ctx.invoked_with}** was not found."
                    f"\n{f'**did you mean... `{matches[0]}`?**' if matches else ''}",
                    delete_after_confirm=True,
                    delete_after_timeout=True,
                    delete_after_cancel=True,
                    buttons=(('▶', f'execute {matches[0]}', discord.ButtonStyle.gray), ('🗑', None, discord.ButtonStyle.red)),
                    timeout=15,
                )
                if confirm is True:
                    message = copy.copy(ctx.message)
                    message._edited_timestamp = discord.utils.utcnow()
                    message.content = message.content.replace(ctx.invoked_with, matches[0])
                    return await self.bot.process_commands(message)
                else:
                    return

            else:
                return

        if isinstance(error, commands.CheckAnyFailure):
            for e in error.errors:
                if not isinstance(error, commands.NotOwner):
                    error = e
                    break

        if isinstance(error, commands.BadUnionArgument):
            if error.errors:
                error = error.errors[0]

        if isinstance(error, commands.NotOwner):
            return await ctx.send(f"you must own `{ctx.me.display_name}` to use `{ctx.command}`")

        if isinstance(error, commands.DisabledCommand):
            return await ctx.send(f"Sorry, but the `{ctx.command.qualified_name}` command is disabled")

        if isinstance(error, commands.TooManyArguments):
            return await ctx.send(f"Too many arguments passed to the command!")

        if isinstance(error, commands.MissingPermissions):
            missing = [(e.replace('_', ' ').replace('guild', 'server')).title() for e in error.missing_permissions]
            perms_formatted = ", ".join(missing[:-2] + [" and ".join(missing[-2:])])
            return await ctx.send(f"You're missing **{perms_formatted}** permissions!")

        if isinstance(error, commands.BotMissingPermissions):
            missing = [(e.replace('_', ' ').replace('guild', 'server')).title() for e in error.missing_permissions]
            perms_formatted = ", ".join(missing[:-2] + [" and ".join(missing[-2:])])
            return await ctx.send(f"I'm missing **{perms_formatted}** permissions!")

        if isinstance(error, commands.MissingRequiredArgument):
            missing = f"{error.param.name}"
            command = f"{ctx.clean_prefix}{ctx.command} {ctx.command.signature}"
            separator = ' ' * (len([item[::-1] for item in command[::-1].split(missing[::-1], 1)][::-1][0]) - 1)
            indicator = '^' * (len(missing) + 2)
            return await ctx.send(
                f"> **Usage: `<required>` - `[optional]` - `[multiple]...`**"
                f"\n```css\n{command}\n{separator}{indicator}"
                f'\n"{missing}" is a required argument that is missing.\n```'
            )

        if isinstance(error, commands.errors.PartialEmojiConversionFailure):
            return await ctx.send(f"`{error.argument}` is not a valid Custom Emoji")

        if isinstance(error, commands.errors.CommandOnCooldown):
            if error.type in (commands.BucketType.user, commands.BucketType.member) and await self.bot.is_owner(ctx.author):
                if ctx.command:
                    ctx.command.reset_cooldown(ctx)
                return await self.bot.process_commands(ctx.message)
            embed = discord.Embed(color=0xD7342A, description=f'Please try again in {round(error.retry_after, 2)} seconds')
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
            else:
                per = ""

            embed.set_footer(text=f"cooldown: {error.cooldown.rate} per {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        if isinstance(error, commands.errors.MaxConcurrencyReached):
            embed = discord.Embed(color=0xD7342A, description=f"Please try again once you are done running the command")
            embed.set_author(name='Command is already running!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.per == BucketType.default:
                per = ""
            elif error.per == BucketType.user:
                per = "per user"
            elif error.per == BucketType.guild:
                per = "per server"
            elif error.per == BucketType.channel:
                per = "per channel"
            elif error.per == BucketType.member:
                per = "per member"
            elif error.per == BucketType.category:
                per = "per category"
            elif error.per == BucketType.role:
                per = "per role"
            else:
                per = ""

            embed.set_footer(text=f"limit is {error.number} command(s) running {per}")
            return await ctx.send(embed=embed)

        if isinstance(error, errors.NoQuotedMessage):
            return await ctx.send(f"{constants.REPLY_BUTTON} You did not reply to message!")

        if isinstance(error, errors.MuteRoleNotFound):
            return await ctx.send(
                "This server doesn't have a mute role, or it was deleted!"
                "\nAssign it with `muterole [new_role]` command, "
                "or can create it with the `muterole create` command"
            )

        if isinstance(error, errors.NoEmojisFound):
            return await ctx.send("I couldn't find any emojis there.")

        if isinstance(error, commands.errors.MemberNotFound):
            return await ctx.send(f"I've searched far and wide, but I couldn't find `{error.argument}` in this server...")

        if isinstance(error, commands.errors.UserNotFound):
            return await ctx.send(f"I've searched far and wide, but `{error.argument}` doesn't seem to be a discord user...")

        if isinstance(error, commands.BadArgument):
            if isinstance(error, commands.BadInviteArgument):
                return await ctx.send(f'{error.argument[0:100]} is not a valid invite or it expired.')
            if isinstance(error, commands.BadBoolArgument):
                return await ctx.send(f'Expected a boolean [yes|no|on|off|y|n|1|0], got `{error.argument[0:100]}` instead')
            return await ctx.send(str(error or "Bad argument given!"))

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("This command does not work inside DMs")

        if isinstance(error, commands.PrivateMessageOnly):
            return await ctx.send("This command only works inside DMs")

        if isinstance(error, commands.NSFWChannelRequired):
            return await ctx.send('This commands only works in NSFW channels')

        if isinstance(error, commands.CheckFailure):
            return await ctx.send(f'You are not allowed to use this command!: {error}')

        error_channel: discord.TextChannel = self.bot.get_channel(self.error_channel)  # type: ignore

        await ctx.send(f"An unexpected error occurred. Perhaps, try again later? Our team has been notified.")

        traceback_string = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        escaped = '`\u200b' * 3
        if ctx.guild:
            command_data = (
                f"by: {ctx.author.name} ({ctx.author.id})"
                f"\ncommand: {ctx.message.content[0:1700].replace('```', escaped)}"
                f"\nguild: {ctx.guild.id} - channel: {ctx.channel.id} - owner: {ctx.guild.owner_id}"
                f"\nbot admin: {ctx.default_tick(ctx.bot_permissions.administrator)} ({ctx.bot_permissions.value})"
                f"- role pos: {ctx.me.top_role.position}"
            )
        else:
            command_data = f"by: {ctx.author.name} ({ctx.author.id}) (DM) \ncommand: {ctx.message.content[0:1700].replace('```', escaped)}"

        to_send = f"```\n{command_data}``````py\n{traceback_string}\n```"
        if len(to_send) <= 2000:
            sent_error = await error_channel.send(to_send)
        else:
            sent_error = await error_channel.send(
                f"```\n{command_data}``````py\nCommand: {ctx.command}" f"Raised the following error:\n```",
                file=discord.File(io.BytesIO(traceback_string.encode()), filename='traceback.py'),
            )
        try:
            await sent_error.add_reaction('🗑')
        except (discord.HTTPException, discord.Forbidden):
            pass
        logging.error('Unhandled Exception in command %s', ctx.command, exc_info=error)

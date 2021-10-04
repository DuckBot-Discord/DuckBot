import copy
import io
import itertools
import re
import traceback
import discord
from discord.ext import commands, tasks
from discord.ext.commands import BucketType
import difflib

from jishaku.paginators import WrappedPaginator

import DuckBot.errors as errors
from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.cogs import music as music_cog
from DuckBot.cogs.info import suggestions_channel, ServerInvite

warned = []


def setup(bot):
    bot.add_cog(Handler(bot))


class Handler(commands.Cog, name='Handler'):
    """
    🆘 Handle them errors 👀 How did you manage to get a look at this category????
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.error_channel = 880181130408636456
        self.do_member_count_update.start()

    def cog_unload(self):
        self.do_member_count_update.cancel()

    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx: CustomContext, error):
        error = getattr(error, "original", error)
        ignored = (
            music_cog.NoPlayer,
            music_cog.FullVoiceChannel,
            music_cog.NotAuthorized,
            music_cog.IncorrectChannelError,
            music_cog.AlreadyConnectedToChannel,
            music_cog.NoVoiceChannel,
            music_cog.QueueIsEmpty,
            music_cog.NoCurrentTrack,
            music_cog.PlayerIsAlreadyPaused,
            music_cog.PlayerIsNotPaused,
            music_cog.NoMoreTracks,
            music_cog.InvalidTimeString,
            music_cog.NoPerms,
            music_cog.NoConnection,
            music_cog.AfkChannel,
            music_cog.SkipInLoopMode,
            music_cog.InvalidTrack,
            music_cog.InvalidPosition,
            music_cog.InvalidVolume,
            music_cog.OutOfTrack,
            music_cog.NegativeSeek
        )

        if isinstance(error, ignored):
            return

        if isinstance(error, errors.UserBlacklisted):
            if ctx.author.id not in warned:
                warned.append(ctx.author.id)
                return await ctx.send("You can't do that! You're blacklisted.")
            else:
                return

        if isinstance(error, errors.BotUnderMaintenance):
            return await ctx.send(self.bot.maintenance or 'I am under maintenance... sorry!')

        if isinstance(error, commands.CommandNotFound):
            ignored_cogs = ('Bot Management', 'jishaku') if ctx.author.id != self.bot.owner_id else ()
            command_names = []
            for command in [c for c in self.bot.commands if c.cog_name not in ignored_cogs]:
                # noinspection PyBroadException
                try:
                    if await command.can_run(ctx):
                        command_names.append([command.name] + command.aliases)
                except:
                    continue

            command_names = list(itertools.chain.from_iterable(command_names))

            matches = difflib.get_close_matches(ctx.invoked_with, command_names)

            if matches:
                confirm = await ctx.confirm(message=f"Sorry, but the command **{ctx.invoked_with}** was not found."
                                                    f"\n{f'**did you mean... `{matches[0]}`?**' if matches else ''}",
                                            delete_after_confirm=True, delete_after_timeout=True,
                                            delete_after_cancel=True, buttons=(
                                                    ('▶', f'execute {matches[0]}', discord.ButtonStyle.gray),
                                                    ('🗑', None, discord.ButtonStyle.red)
                                                ), timeout=15
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

        if isinstance(error, discord.ext.commands.CheckAnyFailure):
            for e in error.errors:
                if not isinstance(error, commands.NotOwner):
                    error = e
                    break

        if isinstance(error, discord.ext.commands.BadUnionArgument):
            if error.errors:
                error = error.errors[0]

        if isinstance(error, commands.NotOwner):
            return await ctx.send(f"you must own `{ctx.me.display_name}` to use `{ctx.command}`")

        if isinstance(error, commands.TooManyArguments):
            return await ctx.send(f"Too many arguments passed to the command!")

        if isinstance(error, discord.ext.commands.MissingPermissions):
            missing = [(e.replace('_', ' ').replace('guild', 'server')).title() for e in error.missing_permissions]
            perms_formatted = ", ".join(missing[:-2] + [" and ".join(missing[-2:])])
            return await ctx.send(f"You're missing **{perms_formatted}** permissions!")

        if isinstance(error, discord.ext.commands.BotMissingPermissions):
            missing = [(e.replace('_', ' ').replace('guild', 'server')).title() for e in error.missing_permissions]
            perms_formatted = ", ".join(missing[:-2] + [" and ".join(missing[-2:])])
            return await ctx.send(f"I'm missing **{perms_formatted}** permissions!")

        if isinstance(error, discord.ext.commands.MissingRequiredArgument):
            missing = f"{error.param.name}"
            command = f"{ctx.clean_prefix}{ctx.command} {ctx.command.signature}"
            separator = (' ' * (len([item[::-1] for item in command[::-1].split(missing[::-1], 1)][::-1][0]) - 1))
            indicator = ('^' * (len(missing) + 2))
            return await ctx.send(f"```\n{command}\n{separator}{indicator}\n{missing} "
                                  f"is a required argument that is missing.\n```")

        if isinstance(error, commands.errors.PartialEmojiConversionFailure):
            return await ctx.send(f"`{error.argument}` is not a valid Custom Emoji")

        if isinstance(error, commands.errors.CommandOnCooldown):
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
            else:
                per = ""

            embed.set_footer(text=f"cooldown: {error.cooldown.rate} per {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        if isinstance(error, discord.ext.commands.errors.MaxConcurrencyReached):
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
            return await ctx.send("<:reply:824240882488180747> Missing reply!")

        if isinstance(error, errors.MuteRoleNotFound):
            return await ctx.send("This server doesn't have a mute role, or it was deleted!"
                                  "\nAssign it with `muterole [new_role]` command, "
                                  "or can create it with the `muterole create` command")

        if isinstance(error, errors.NoEmojisFound):
            return await ctx.send("I couldn't find any emojis there.")

        if isinstance(error, commands.errors.MemberNotFound):
            return await ctx.send(f"I've searched far and wide, "
                                  f"but I couldn't find `{error.argument}` in this server...")

        if isinstance(error, commands.errors.UserNotFound):
            return await ctx.send(
                f"I've searched far and wide, but `{error.argument}` doesn't seem to be a discord user...")

        if isinstance(error, commands.BadArgument):
            return await ctx.send(error or "Bad argument given!")

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("This command does not work inside DMs")

        if isinstance(error, commands.PrivateMessageOnly):
            return await ctx.send("This command only works inside DMs")

        if isinstance(error, commands.NSFWChannelRequired):
            return await ctx.send('This commands only works in NSFW channels')

        error_channel = self.bot.get_channel(self.error_channel)

        nl = '\n'
        await ctx.send(f"**An unexpected error ocurred... For more info, join my support server**"
                       f"\n> ```py\n> {f'{nl}> '.join(str(error).split(nl))}\n> ```", view=ServerInvite())

        traceback_string = "".join(traceback.format_exception(
            etype=None, value=error, tb=error.__traceback__))

        if ctx.guild:
            command_data = f"by: {ctx.author.name} ({ctx.author.id})" \
                           f"\ncommand: {ctx.message.content[0:1700]}" \
                           f"\nguild_id: {ctx.guild.id} - channel_id: {ctx.channel.id}" \
                           f"\nowner: {ctx.guild.owner.name} ({ctx.guild.owner.id})" \
                           f"\nbot admin: {ctx.default_tick(ctx.me.guild_permissions.administrator)} " \
                           f"- role pos: {ctx.me.top_role.position}"
        else:
            command_data = f"command: {ctx.message.content[0:1700]}" \
                           f"\nCommand executed in DMs"

        to_send = f"```yaml\n{command_data}``````py\n{ctx.command} " \
                  f"command raised an error:\n{traceback_string}\n```"
        if len(to_send) < 2000:
            try:
                sent_error = await error_channel.send(to_send)

            except (discord.Forbidden, discord.HTTPException):
                sent_error = await error_channel.send(f"```yaml\n{command_data}``````py Command: {ctx.command}"
                                                      f"Raised the following error:\n```",
                                                      file=discord.File(io.StringIO(traceback_string),
                                                                        filename='traceback.py'))
        else:
            sent_error = await error_channel.send(f"```yaml\n{command_data}``````py Command: {ctx.command}"
                                                  f"Raised the following error:\n```",
                                                  file=discord.File(io.StringIO(traceback_string),
                                                                    filename='traceback.py'))
        try:
            await sent_error.add_reaction('🗑')
        except (discord.HTTPException, discord.Forbidden):
            pass
        raise error

    @commands.Cog.listener('on_raw_reaction_add')
    async def wastebasket(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id == self.error_channel and await \
                self.bot.is_owner(payload.member) and str(payload.emoji == '🗑'):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if not message.author == self.bot.user:
                return
            error = '```py\n' + '\n'.join(message.content.split('\n')[7:])
            await message.edit(content=f"{error}```fix\n✅ Marked as fixed by the developers.```")
            await message.clear_reactions()

        if payload.channel_id == suggestions_channel and await \
                self.bot.is_owner(payload.member) and str(payload.emoji) in ('🔼', '🔽'):

            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if not message.author.bot or not message.embeds:
                return
            embed = message.embeds[0]

            sub = {
                'Suggestion ': 'suggestion',
                'suggestion ': 'suggestion',
                'Denied ': '',
                'Approved ': ''
            }

            pattern = '|'.join(sorted(re.escape(k) for k in sub))
            title = re.sub(pattern, lambda m: sub.get(m.group(0).upper()), embed.title, flags=re.IGNORECASE)

            scheme = {
                '🔼': (0x6aed64, f'Approved suggestion {title}'),
                '🔽': (0xf25050, f'Denied suggestion {title}')
            }[str(payload.emoji)]

            embed.title = scheme[1]
            embed.colour = scheme[0]
            # noinspection PyBroadException
            try:
                user_id = int(embed.footer.text.replace("Sender ID: ", ""))
            except:
                user_id = None
            suggestion = embed.description

            if str(payload.emoji) == '🔼' and user_id:
                try:
                    user = (self.bot.get_user(user_id) or (await self.bot.fetch_user(user_id)))
                    user_embed = discord.Embed(title="🎉 Suggestion approved! 🎉",
                                               description=f"**Your suggestion has been approved! "
                                                           f"You suggested:**\n{suggestion}")
                    user_embed.set_footer(text='Reply to this DM if you want to stay in contact '
                                               'with us while we work on your suggestion!')
                    await user.send(embed=user_embed)
                    embed.set_footer(text=f"DM sent - ✅ - {user_id}")
                except (discord.Forbidden, discord.HTTPException):
                    embed.set_footer(text=f"DM sent - ❌ - {user_id}")
            else:
                embed.set_footer(text='Suggestion denied. No DM sent.')

            await message.edit(embed=embed)
            await message.clear_reactions()

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        print(data)

    @tasks.loop(minutes=30)
    async def do_member_count_update(self):
        await self.bot.top_gg.post_guild_count()

    @commands.Cog.listener('on_message')
    async def on_afk_user_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if message.author.id in self.bot.afk_users:
            try:
                if self.bot.auto_un_afk[message.author.id] is False:
                    return
            except KeyError:
                pass

            self.bot.afk_users.pop(message.author.id)

            info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', message.author.id)
            await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, null, null) '
                                      'ON CONFLICT (user_id) DO UPDATE SET start_time = null, reason = null', message.author.id)

            await message.channel.send(f'**Welcome back, {message.author.mention}, afk since: {discord.utils.format_dt(info["start_time"], "R")}**'
                                       f'\n**With reason:** {info["reason"]}', delete_after=10)

            await message.add_reaction('👋')

    @commands.Cog.listener('on_message')
    async def on_afk_user_mention(self, message: discord.Message):
        if not message.guild:
            return
        if message.author == self.bot.user:
            return
        if message.mentions:
            pinged_afk_user_ids = list(set([u.id for u in message.mentions]).intersection(self.bot.afk_users))
            paginator = WrappedPaginator(prefix='', suffix='')
            for user_id in pinged_afk_user_ids:
                member = message.guild.get_member(user_id)
                if member and member.id != message.author.id:
                    info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', user_id)
                    paginator.add_line(f'**woah there, {message.author.mention}, it seems like {member.mention} has been afk '
                                       f'since {discord.utils.format_dt(info["start_time"], style="R")}!**'
                                       f'\n**With reason:** {info["reason"]}\n')

            ctx: CustomContext = await self.bot.get_context(message)
            for page in paginator.pages:
                await ctx.send(page, allowed_mentions=discord.AllowedMentions(replied_user=True,
                                                                              users=False,
                                                                              roles=False,
                                                                              everyone=False))

    @commands.Cog.listener('on_message')
    async def on_suggestion_receive(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.bot.suggestion_channels:
            return
        if self.bot.suggestion_channels[message.channel.id] is True and not message.attachments and \
                not message.channel.permissions_for(message.author).manage_messages:
            await message.delete(delay=0)
            return await message.channel.send(f'⚠ | {message.author.mention} this **suggestions channel** is set to **image-only** mode!', delete_after=5)

        await message.add_reaction('<:upvote:893588750242832424>')
        await message.add_reaction('<:downvote:893588792164892692>')

import argparse
import asyncio
import contextlib
import datetime
import difflib
import random
import discord
import re
import shlex
import typing
from collections import Counter

from discord.ext import commands, tasks

from DuckBot import errors
from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers import time_inputs as helpers, constants


def setup(bot):
    bot.add_cog(Moderation(bot))


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


def ensure_muterole(*, required: bool = True):
    async def predicate(ctx: CustomContext):
        if not ctx.guild:
            raise commands.BadArgument('Only servers can have mute roles')
        if not required:
            return True
        if not (role := await ctx.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)):
            raise commands.BadArgument('This server has no mute role set')
        if not (role := ctx.guild.get_role(role)):
            raise commands.BadArgument("It seems like I could not find this server's mute role. Was it deleted?")
        if role >= ctx.me.top_role:
            raise commands.BadArgument("This server's mute role seems to be above my top role. I can't assign it!")
        return True
    return commands.check(predicate)


async def muterole(ctx) -> discord.Role:
    if not ctx.guild:
        raise commands.BadArgument('Only servers can have mute roles')
    if not (role := await ctx.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)):
        raise commands.BadArgument('This server has no mute role set')
    if not (role := ctx.guild.get_role(role)):
        raise commands.BadArgument("It seems like I could not find this server's mute role. Was it deleted?")
    if role >= ctx.me.top_role:
        raise commands.BadArgument("This server's mute role seems to be above my top role. I can't assign it!")
    return role


# noinspection PyProtocol
class BannedMember(commands.Converter):
    async def convert(self, ctx: CustomContext, argument):
        await ctx.trigger_typing()
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        if not (entity := discord.utils.find(lambda u: str(u.user).lower() == argument.lower(), ban_list)):
            entity = discord.utils.find(lambda u: str(u.user.name).lower() == argument.lower(), ban_list)
            if not entity:
                matches = difflib.get_close_matches(argument, [str(u.user.name) for u in ban_list])
                if matches:
                    entity = discord.utils.find(lambda u: str(u.user.name) == matches[0], ban_list)
                    if entity:
                        val = await ctx.confirm(f'Found closest match: **{entity.user}**. Do you want me to unban them?',
                                                delete_after_cancel=True, delete_after_confirm=True,
                                                delete_after_timeout=False, timeout=60,
                                                buttons=((None, 'Yes', discord.ButtonStyle.green), (None, 'No', discord.ButtonStyle.grey)))
                        if val is None:
                            raise errors.NoHideout
                        elif val is False:
                            try:
                                await ctx.message.add_reaction(random.choice(constants.DONE))
                            except discord.HTTPException:
                                pass
                            raise errors.NoHideout

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity


def can_execute_action(ctx, user, target):
    if isinstance(target, discord.Member):
        return user == ctx.guild.owner or (user.top_role > target.top_role and target != ctx.guild.owner)
    elif isinstance(target, discord.User):
        return True
    raise TypeError(f'argument \'target\' expected discord.User, received {type(target)} instead')


def bot_can_execute_action(ctx: CustomContext, target: discord.Member):
    if isinstance(target, discord.Member):
        if target.top_role > ctx.guild.me.top_role:
            raise commands.BadArgument('This member has a higher role than me.')
        elif target == ctx.guild.owner:
            raise commands.BadArgument('I cannot perform that action, as the target is the owner.')
        elif target == ctx.guild.me:
            raise commands.BadArgument('I cannot perform that action on myself.')
        return True


class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f'{ctx.author} (ID: {ctx.author.id}): {argument}'

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret


def safe_reason_append(base, to_append):
    appended = base + f'({to_append})'
    if len(appended) > 512:
        return base
    return appended


class Moderation(commands.Cog):
    """
    🔨 Commands to facilitate server moderation, and all utilities for admins and mods.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.temporary_mutes.start()
        self.select_emoji = '🔨'
        self.select_brief = 'Mod Commands, like Ban and Mute'

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    def cog_unload(self):
        self.temporary_mutes.cancel()

    # --------------- FUNCTIONS --------------- #

    @staticmethod
    async def perms_error(ctx):
        await ctx.message.add_reaction('🚫')
        await ctx.message.delete(delay=5)
        return

    @staticmethod
    async def error_message(ctx, message):
        embed = discord.Embed()
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=5)
        await ctx.message.delete(delay=5)

    @staticmethod
    async def do_removal(ctx: CustomContext, limit: int, predicate, *, before=None, after=None, bulk: bool = True):
        if limit > 2000:
            return await ctx.send(f'Too many messages to search given ({limit}/2000)')

        async with ctx.typing():
            if before is None:
                before = ctx.message
            else:
                before = discord.Object(id=before)

            if after is not None:
                after = discord.Object(id=after)

            try:
                deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate, bulk=bulk)
            except discord.Forbidden:
                return await ctx.send('I do not have permissions to delete messages.')
            except discord.HTTPException as e:
                return await ctx.send(f'Error: {e} (try a smaller search?)')

            spammers = Counter(m.author.display_name for m in deleted)
            deleted = len(deleted)
            messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
            if deleted:
                messages.append('')
                spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
                messages.extend(f'**{name}**: {count}' for name, count in spammers)

            to_send = '\n'.join(messages)

            if len(to_send) > 2000:
                await ctx.send(f'Successfully removed {deleted} messages.', delete_after=10, reply=False)
            else:
                await ctx.send(to_send, delete_after=10, reply=False)

    # ------------ TASKS ---------- #

    @tasks.loop()
    async def temporary_mutes(self):
        # if you don't care about keeping records of old tasks, remove this WHERE and change the UPDATE to DELETE
        next_task = await self.bot.db.fetchrow('SELECT * FROM temporary_mutes ORDER BY end_time LIMIT 1')
        # if no remaining tasks, stop the loop
        if next_task is None:
            self.temporary_mutes.cancel()
            return

        await discord.utils.sleep_until(next_task['end_time'])

        guild: discord.Guild = self.bot.get_guild(next_task['guild_id'])

        if guild:

            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1',
                                                   next_task['guild_id'])
            if mute_role:

                role = guild.get_role(int(mute_role))
                if isinstance(role, discord.Role):

                    if not role > guild.me.top_role:
                        try:
                            member = (guild.get_member(next_task['member_id']) or
                                      await guild.fetch_member(next_task['member_id']))
                            if member:
                                await member.remove_roles(role)
                        except(discord.Forbidden, discord.HTTPException):
                            pass

        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                  next_task['guild_id'], next_task['member_id'])

    @temporary_mutes.before_loop
    async def wait_for_bot_ready(self):
        await self.bot.wait_until_ready()

    def mute_task(self):
        if self.temporary_mutes.is_running():
            self.temporary_mutes.restart()
        else:
            self.temporary_mutes.start()

    @commands.command(help="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, kick_members=True)
    async def kick(self, ctx: CustomContext, member: discord.Member, *, reason: typing.Optional[str] = None):
        bot_can_execute_action(ctx, member)
        if not can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument('You cannot kick this member.')
        await member.kick(reason=f"Kicked by {ctx.author} ({ctx.author.id}) " + (f" for {reason}" if reason else ""))
        await ctx.send(f'👢 **|** **{ctx.author}** kicked **{member}**' + (f"\nFor {reason}" if reason else ""))

    @commands.command(help="Bans a member from the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    async def ban(self, ctx: CustomContext, user: typing.Union[discord.Member, discord.User], delete_days: typing.Optional[int] = 1, *, reason: str = None):
        if delete_days and not 8 > delete_days > -1:
            raise commands.BadArgument("**delete_days** must be between 0 and 7 days")

        bot_can_execute_action(ctx, user)

        if can_execute_action(ctx, ctx.author, user):
            await ctx.guild.ban(user, reason=f"Banned by {ctx.author} ({ctx.author.id})" + (f'for {reason}' if reason else ''), delete_message_days=delete_days)
            return await ctx.send(f'🔨 **|** banned **{discord.utils.escape_markdown(str(user))}**' + (f' for {reason}' if reason else ''))
        await ctx.send('Sorry, but you can\'t ban that member')

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    async def softban(self, ctx: CustomContext, user: typing.Union[discord.Member, discord.User], delete_days: typing.Optional[int] = 1, *, reason: str = None):
        """ Soft-bans a member from the server.
        What is soft ban?
        """
        if delete_days and not 8 > delete_days > -1:
            raise commands.BadArgument("**delete_days** must be between 0 and 7 days")

        bot_can_execute_action(ctx, user)

        if can_execute_action(ctx, ctx.author, user):
            await ctx.guild.ban(user, reason=f"Soft-banned by {ctx.author} ({ctx.author.id})" + (f'for {reason}' if reason else ''), delete_message_days=delete_days)
            await ctx.guild.unban(user, reason=f"Soft-banned by {ctx.author} ({ctx.author.id})" + (f'for {reason}' if reason else ''))
            return await ctx.send(f'🔨 **|** soft-banned **{discord.utils.escape_markdown(str(user))}**' + (f' for {reason}' if reason else ''))
        await ctx.send('Sorry, but you can\'t ban that member')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx: CustomContext, *, user: BannedMember):
        """unbans a user from this server.
        Can search by:
        - `user ID` (literal - number)
        - `name#0000` (literal - case insensitive)
        - `name` (literal - case insensitive)
        - `name` (close matches - will prompt to confirm)
        """
        user: discord.guild.BanEntry
        await ctx.guild.unban(user.user, reason=f"Unban by {ctx.author} ({ctx.author.id})")
        extra = f"Previously banned for: {user.reason}" if user.reason else ''
        return await ctx.send(f"Unbanned **{discord.utils.escape_markdown(str(user.user))}**\n{extra}")

    @commands.command(aliases=['sn', 'nick'])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(send_messages=True, manage_nicknames=True)
    async def setnick(self, ctx: CustomContext, member: discord.Member, *, new: str = None) -> \
            typing.Optional[discord.Message]:
        """
        Removes someone's nickname. Don't send a new nickname to remove it.
        """
        new = new or member.name
        old = member.display_name
        if len(new) > 32:
            raise commands.BadArgument(f'Nickname too long. {len(new)}/32')
        if not can_execute_action(ctx, ctx.author, member) and ctx.guild.id != 745059550998298756:
            raise commands.MissingPermissions(['role_hierarchy'])

        await member.edit(nick=new)
        return await ctx.send(f"✏ {ctx.author.mention} edited {member.mention}"
                              f"\nnickname: **`{old}`** -> **`{new}`**",
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.group(name="clean", aliases=['purge', 'delete', 'remove', 'clear'])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def remove(self, ctx, search: typing.Optional[int] = 100):
        """
        Removes messages that meet a criteria.

        Note: If ran without any sub-commands, it will remove all messages that are NOT pinned to the channel.
        Use "remove all <amount>" to remove all messages, including pinned.
        """

        if ctx.invoked_subcommand is None:
            await self.do_removal(ctx, search, lambda e: not e.pinned)

    @remove.command(name="embeds", aliases=['embed'])
    async def remove_embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @remove.command(name="files", aliases=["attachments"])
    async def remove_files(self, ctx, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @remove.command(name="images")
    async def remove_images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @remove.command(name='all')
    async def remove_all(self, ctx, search=100):
        """Removes all messages."""
        await self.do_removal(ctx, search, lambda e: True)

    @remove.command(name="user")
    async def remove_user(self, ctx, member: discord.Member, search=100):
        """Removes all messages by the member."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @remove.command(name="contains", aliases=["has"])
    async def remove_contains(self, ctx, *, text: str):
        """Removes all messages containing a substring.
        The substring must be at least 3 characters long.
        """
        if len(text) < 3:
            await ctx.send('The substring length must be at least 3 characters.')
        else:
            await self.do_removal(ctx, 100, lambda e: text in e.content)

    @remove.command(name='bot', aliases=['bots'])
    async def remove_bot(self, ctx, prefix: typing.Optional[str] = None, search=100):
        """Removes a bot user's messages and messages with their optional prefix."""

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await self.do_removal(ctx, search, predicate)

    @remove.command(name='emoji', aliases=['emojis'])
    async def remove_emoji(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        custom_emoji = re.compile(r'<a?:[a-zA-Z0-9_]+:([0-9]+)>')

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @commands.has_permissions(manage_threads=True)
    @commands.bot_has_permissions(manage_threads=True)
    @remove.command(name='threads', aliases=['thread'])
    async def remove_threads(self, ctx, search: int = 100):
        async with ctx.typing():
            if search > 2000:
                return await ctx.send(f'Too many messages to search given ({search}/2000)')

            def check(m: discord.Message):
                return m.flags.has_thread

            deleted = await ctx.channel.purge(limit=search, check=check)
            thread_ids = [m.id for m in deleted]
            if not thread_ids:
                return await ctx.send("No threads found!")

            for thread_id in thread_ids:
                thread = self.bot.get_channel(thread_id)
                if isinstance(thread, discord.Thread):
                    await thread.delete()
                    await asyncio.sleep(0.5)

            spammers = Counter(m.author.display_name for m in deleted)
            deleted = len(deleted)
            messages = [f'{deleted} message'
                        f'{" and its associated thread was" if deleted == 1 else "s and their associated messages were"} '
                        f'removed.']

            if deleted:
                messages.append('')
                spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
                messages.extend(f'**{name}**: {count}' for name, count in spammers)

            to_send = '\n'.join(messages)

            if len(to_send) > 2000:
                await ctx.send(f'Successfully removed {deleted} messages and their associated threads.',
                               delete_after=10, reply=False)
            else:
                await ctx.send(to_send, delete_after=10, reply=False)

    @remove.command(name='reactions')
    async def remove_reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""
        async with ctx.typing():
            if search > 2000:
                return await ctx.send(f'Too many messages to search for ({search}/2000)')

            total_reactions = 0
            async for message in ctx.history(limit=search, before=ctx.message):
                if len(message.reactions):
                    total_reactions += sum(r.count for r in message.reactions)
                    await message.clear_reactions()
                    await asyncio.sleep(0.5)

            await ctx.send(f'Successfully removed {total_reactions} reactions.')

    @remove.command(name="custom")
    async def remove_custom(self, ctx, *, args: str):
        """A more advanced purge command, with a command-line-like syntax.
        # Do "%PRE%remove help" for usage.
        """
        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument('--user', nargs='+')
        parser.add_argument('--contains', nargs='+')
        parser.add_argument('--starts', nargs='+')
        parser.add_argument('--ends', nargs='+')
        parser.add_argument('--or', action='store_true', dest='_or')
        parser.add_argument('--not', action='store_true', dest='_not')
        parser.add_argument('--emoji', action='store_true')
        parser.add_argument('--bot', action='store_const', const=lambda m: m.author.bot)
        parser.add_argument('--embeds', action='store_const', const=lambda m: len(m.embeds))
        parser.add_argument('--files', action='store_const', const=lambda m: len(m.attachments))
        parser.add_argument('--reactions', action='store_const', const=lambda m: len(m.reactions))
        parser.add_argument('--search', type=int)
        parser.add_argument('--after', type=int)
        parser.add_argument('--before', type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            await ctx.send(str(e))
            return

        predicates = []
        if args.bot:
            predicates.append(args.bot)

        if args.embeds:
            predicates.append(args.embeds)

        if args.files:
            predicates.append(args.files)

        if args.reactions:
            predicates.append(args.reactions)

        if args.emoji:
            custom_emoji = re.compile(r'<:(\w+):(\d+)>')
            predicates.append(lambda m: custom_emoji.search(m.content))

        if args.user:
            users = []
            converter = commands.MemberConverter()
            for u in args.user:
                try:
                    user = await converter.convert(ctx, u)
                    users.append(user)
                except Exception as e:
                    await ctx.send(str(e))
                    return

            predicates.append(lambda m: m.author in users)

        if args.contains:
            predicates.append(lambda m: any(sub in m.content for sub in args.contains))

        if args.starts:
            predicates.append(lambda m: any(m.content.startswith(s) for s in args.starts))

        if args.ends:
            predicates.append(lambda m: any(m.content.endswith(s) for s in args.ends))

        op = all if not args._or else any

        def predicate(m):
            r = op(p(m) for p in predicates)
            if args._not:
                return not r
            return r

        if args.after:
            if args.search is None:
                args.search = 2000

        if args.search is None:
            args.search = 100

        args.search = max(0, min(2000, args.search))  # clamp from 0-2000
        await self.do_removal(ctx, args.search, predicate, before=args.before, after=args.after)

    @remove.command(name="help", hidden=True)
    async def remove_custom_readme(self, ctx):
        """A more advanced purge command.
        This command uses a powerful "command line" syntax.
        Most options support multiple values to indicate 'any' match.
        If the value has spaces it must be quoted.
        The messages are only deleted if all options are met unless
        the --or flag is passed, in which case only if any is met.

        The following options are valid.
         --user: A mention or name of the user to remove.
         --contains: A substring to search for in the message.
         --starts: A substring to search if the message starts with.
         --ends: A substring to search if the message ends with.
         --search: Messages to search. Default 100. Max 2000.
         --after: Messages after this message ID.
         --before: Messages before this message ID.

        Flag options (no arguments):
         --bot: Check if it's a bot user.
         --embeds: Checks for embeds.
         --files: Checks for attachments.
         --emoji: Checks for custom emoji.
         --reactions: Checks for reactions.
         --or: Use logical OR for ALL options.
         --not: Use logical NOT for ALL options.
        """
        await ctx.send_help(ctx.command)

    @commands.command()
    async def cleanup(self, ctx: CustomContext, amount: int = 25):
        """
        Cleans up the bots messages. it defaults to 25 messages. if you or the bot don't have manage_messages permission, the search will be limited to 25 messages.
        """
        if amount > 25:
            if not ctx.channel.permissions_for(ctx.author).manage_messages:
                await ctx.send("You must have `manage_messages` permission to perform a search greater than 25")
                return
            if not ctx.channel.permissions_for(ctx.me).manage_messages:
                await ctx.send("I need the `manage_messages` permission to perform a search greater than 25")
                return

        if ctx.channel.permissions_for(ctx.me).manage_messages:
            prefix = await self.bot.get_pre(self.bot, ctx.message)
            if self.bot.noprefix and await self.bot.is_owner(ctx.author):
                with contextlib.suppress(ValueError):
                    prefix.remove('')
            prefix = tuple(prefix)
            bulk = True

            def check(msg):
                return msg.author == ctx.me or msg.content.startswith(prefix)
        else:
            bulk = False

            def check(msg):
                return msg.author == ctx.me

        await self.do_removal(ctx, predicate=check, bulk=bulk, limit=amount)

    # --------------------------------------------------------------------------------#
    # -------------------------------- MUTE STUFF ------------------------------------#
    # --------------------------------------------------------------------------------#

    # Indefinitely mute member

    @commands.command()
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None) -> discord.Message:
        """
        Mutes a member indefinitely.
        """
        if not can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        try:
            await member.add_roles(role, reason=f"Muted by {ctx.author} ({ctx.author.id}) {f'for: {reason}' if reason else ''}"[0:500])
        except discord.Forbidden:
            raise commands.BadArgument(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                  ctx.guild.id, member.id)

        self.mute_task()

        if ctx.channel.permissions_for(role).send_messages_in_threads:
            embed = discord.Embed(color=discord.Color.red(),
                                  description='The mute role has permissions to create threads!'
                                              '\nYou may want to fix that using the `muterole fix` command!'
                                              '\nIf you don\'t want to receive security warnings, you can do `warnings off` command',
                                  title='Warning')
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.send(embed=embed)

        if reason:
            reason = f"\nReason: {reason}"
        return await ctx.send(f"**{ctx.author}** muted **{member}**{reason or ''}",
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['mass-mute', 'multi_mute', 'mass_mute', 'multimute'], name='multi-mute')
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def multi_mute(self, ctx: CustomContext, members: commands.Greedy[discord.Member],
                         reason: str = None) -> discord.Message:
        """
        Mutes a lot of members indefinitely indefinitely.
        """

        role = await muterole(ctx)

        reason = f"Mute by {ctx.author} ({ctx.author.id}){f': {reason}' if reason else ''}"[0:500]

        successful: typing.List[discord.Member] = []
        failed_perms: typing.List[discord.Member] = []
        failed_internal: typing.List[discord.Member] = []

        for member in members:
            if not can_execute_action(ctx, ctx.author, member):
                failed_perms.append(member)
                continue

            try:
                await member.add_roles(role, reason=reason)
                successful.append(member)
            except (discord.Forbidden, discord.HTTPException):
                failed_internal.append(member)
                continue

            await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                      ctx.guild.id, member.id)

        failed = ""

        if failed_perms:
            failed += f"\n**{len(failed_perms)} failed** because the author didn't have the required permissions to mute them."
        if failed_internal:
            failed += f"\n**{len(failed_internal)}** failed due to a discord error."

        await ctx.send(f"**Successfully muted {len(successful)}/{len(members)}**:"
                       f"\n**Successful:** {', '.join([m.display_name for m in successful])}{failed}")

        self.mute_task()

    @commands.command(aliases=['hardmute'], name='hard-mute')
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def hardmute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None) -> discord.Message:
        """
        Mutes a member indefinitely, and removes all their roles.
        """
        if not can_execute_action(ctx, ctx.author, member):
            return await ctx.send("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        roles = [r for r in member.roles if not r.is_assignable()] + [role]

        try:
            await member.edit(roles=roles, reason=f"Mute by {ctx.author} ({ctx.author.id}) {f'for {reason}' if reason else ''}"[0:500])
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                  ctx.guild.id, member.id)

        self.mute_task()

        not_removed = [r for r in member.roles if not r.is_assignable() and not r.is_default()]
        nl = '\n'
        if not reason:
            return await ctx.send(f"✅ **|** **{ctx.author}** hard-muted **{member}** "
                                  f"{f'{nl}⚠ **|** Could not remove **{len(not_removed)}** role(s).' if not_removed else ''}",
                                  allowed_mentions=discord.AllowedMentions().none())
        return await ctx.send(f"✅ **|** **{ctx.author}** hard-muted **{member}**"
                              f"\nℹ **| With reason:** {reason[0:1600]}"
                              f"{f'{nl}⚠ **|** Could not remove **{len(not_removed)}** role(s).' if not_removed else ''}",
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.command()
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """
        Unmutes a member
        """
        if not can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        try:
            await member.remove_roles(role, reason=f"Unmute by {ctx.author} ({ctx.author.id}) {f'for {reason}' if reason else ''}"[0:500])
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to remove the `{role.name}` role")

        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                  ctx.guild.id, member.id)

        self.mute_task()

        reason = f"\nReason: {reason}" if reason else ""
        await ctx.send(f"**{ctx.author}** unmuted **{member}**{reason}",
                       allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['mass-unmute', 'multi_unmute', 'mass_unmute', 'massunmute'], name='multi-unmute')
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def multi_unmute(self, ctx: CustomContext, members: commands.Greedy[discord.Member],
                           reason: str = None) -> discord.Message:
        """
        Mutes a lot of members indefinitely indefinitely.
        """
        if not can_execute_action(ctx, ctx.author, members):
            raise commands.BadArgument("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        successful: typing.List[discord.Member] = []
        failed_perms: typing.List[discord.Member] = []
        failed_internal: typing.List[discord.Member] = []

        for member in members:
            if not can_execute_action(ctx, ctx.author, member):
                failed_perms.append(member)
                continue

            try:
                await member.remove_roles(role, reason=reason)
                successful.append(member)
            except (discord.Forbidden, discord.HTTPException):
                failed_internal.append(member)
                continue

            await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                      ctx.guild.id, member.id)

        await ctx.send(f"**Successfully unmuted {len(successful)}/{len(members)}**:"
                       f"\n**Successful:** {', '.join([m.display_name for m in successful])}"
                       f"\n**Failed:** {', '.join([m.display_name for m in failed_perms + failed_internal])}")

        self.mute_task()

    @commands.command()
    @ensure_muterole()
    @commands.bot_has_permissions(manage_roles=True)
    async def selfmute(self, ctx, *, duration: helpers.ShortTime):
        """
        Temporarily mutes yourself for the specified duration.
          note that: `relative_time` must be a short time!
        for example: 1d, 5h, 3m or 25s, or a combination of those, like 3h5m25s (without spaces between these times)
        You can only mute yourself for a maximum of 24 hours and a minimum of 5 minutes.
        # ❓❔ Do not ask a moderator to unmute you! ❓❔
        """
        reason = "self mute"

        role = await muterole(ctx)

        created_at = ctx.message.created_at
        if duration.dt > (created_at + datetime.timedelta(days=1)):
            return await ctx.send('Duration is too long. Must be at most 24 hours.')

        if duration.dt < (created_at + datetime.timedelta(minutes=5)):
            return await ctx.send('Duration is too short. Must be at least 5 minutes.')

        delta = helpers.human_timedelta(duration.dt, source=created_at)
        warning = (f"_Are you sure you want to mute yourself for **{delta}**?_"
                   f"\n**__Don't ask the moderators to undo this!__**")

        if not await ctx.confirm(warning, delete_after_confirm=True):
            return

        try:
            await ctx.author.add_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute("INSERT INTO temporary_mutes(guild_id, member_id, reason, end_time) "
                                  "VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, member_id) DO "
                                  "UPDATE SET reason = $3, end_time = $4",
                                  ctx.guild.id, ctx.author.id, reason, duration.dt)

        self.mute_task()

        await ctx.send(f"{constants.SHUT_SEAGULL} 👍")

    # Temp-mute

    @commands.command()
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def tempmute(self, ctx, member: discord.Member, *, duration: helpers.ShortTime):
        """
        Temporarily mutes a member for the specified duration.
        # Duration must be a short time, for example: 1s, 5m, 3h, or a combination of those, like 3h5m25s
        """

        reason = f"Temporary mute by {ctx.author} ({ctx.author.id})"

        if not can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument("You're not high enough in role hierarchy to do that!")

        role = await muterole(ctx)

        created_at = ctx.message.created_at
        if duration.dt < (created_at + datetime.timedelta(minutes=1)):
            return await ctx.send('Duration is too short. Must be at least 1 minute.')

        delta = helpers.human_timedelta(duration.dt, source=created_at)

        try:
            await member.add_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute("INSERT INTO temporary_mutes(guild_id, member_id, reason, end_time) "
                                  "VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, member_id) DO "
                                  "UPDATE SET reason = $3, end_time = $4",
                                  ctx.guild.id, member.id, reason, duration.dt)

        self.mute_task()

        await ctx.send(f"**{ctx.author}** muted **{member}** for **{delta}**")

    @commands.Cog.listener('on_guild_channel_create')
    async def automatic_channel_update(self, channel: discord.abc.GuildChannel) -> None:
        """
        Adds mute overwrites to any newly created channels.
        """
        if not channel.permissions_for(channel.guild.me).manage_channels:
            return
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', channel.guild.id)
        if not mute_role:
            return
        role = channel.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            return
        if role > channel.guild.me.top_role:
            return

        perms = channel.overwrites_for(role)
        perms.update(send_messages=False,
                     add_reactions=False,
                     connect=False,
                     speak=False,
                     create_public_threads=False,
                     create_private_threads=False,
                     send_messages_in_threads=False,
                     )
        return await channel.set_permissions(role, overwrite=perms, reason="DuckBot automatic mute role permissions")

    @commands.command(aliases=['lock', 'ld'])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def lockdown(self, ctx, channel: typing.Optional[discord.TextChannel], role: typing.Optional[discord.Role]):
        """
        Locks down the channel. Optionally, you can specify a channel and role to lock lock down.
        Channel: You and the bot must have manage roles permission in the channel.
        Role: The specified role must be lower than yours and the bots top role.
        """

        role = role if role and (role < ctx.me.top_role or ctx.author == ctx.guild.owner) \
                       and role < ctx.author.top_role else ctx.guild.default_role

        channel = channel if channel and channel.permissions_for(ctx.author).manage_roles and channel.permissions_for(
            ctx.me).manage_roles else ctx.channel

        perms = channel.overwrites_for(ctx.me)
        perms.update(send_messages=True,
                     add_reactions=True,
                     create_public_threads=True,
                     create_private_threads=True
                     )

        await channel.set_permissions(ctx.me, overwrite=perms,
                                      reason=f'Channel lockdown by {ctx.author} ({ctx.author.id})')

        perms = channel.overwrites_for(role)
        perms.update(send_messages=False,
                     add_reactions=False,
                     create_public_threads=False,
                     create_private_threads=False
                     )

        await channel.set_permissions(role, overwrite=perms,
                                      reason=f'Channel lockdown for {role.name} by {ctx.author} ({ctx.author.id})')
        await ctx.send(f"Locked down **{channel.name}** for **{role.name}**",
                       allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['unlockdown', 'uld'])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unlock(self, ctx, channel: typing.Optional[discord.TextChannel], role: typing.Optional[discord.Role]):
        """
        Unlocks the channel. Optionally, you can specify a channel and role to lock lock down.
        Channel: You must have manage roles permission, and the bot must do so too.
        Role: The specified role must be lower than yours and the bots top role.
        """

        role = role if role and (role < ctx.me.top_role or ctx.author == ctx.guild.owner) \
                       and role < ctx.author.top_role else ctx.guild.default_role

        channel = channel if channel and channel.permissions_for(ctx.author).manage_roles and channel.permissions_for(
            ctx.me).manage_roles else ctx.channel

        perms = channel.overwrites_for(ctx.guild.default_role)
        perms.update(send_messages=None,
                     add_reactions=None,
                     create_public_threads=None,
                     create_private_threads=None
                     )

        await channel.set_permissions(role, overwrite=perms,
                                      reason=f'Channel lockdown for {role.name} by {ctx.author} ({ctx.author.id})')

        await ctx.send(f"Unlocked **{channel.name}** for **{role.name}**",
                       allowed_mentions=discord.AllowedMentions().none())

    @commands.command(usage="[channel] <duration|reset>")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: CustomContext, channel: typing.Optional[discord.TextChannel], *,
                       duration: helpers.ShortTime = None) -> discord.Message:
        """
        Sets the current slow mode to a delay between 1s and 6h. If specified, sets it for another channel.
        # Duration must be a short time, for example: 1s, 5m, 3h, or a combination of those, like 3h5m25s.
        # To reset the slow mode, execute command without specifying a duration.
        Channel: You must have manage channel permission, and the bot must do so too.
        """

        channel = channel if channel and channel.permissions_for(
            ctx.author).manage_channels and channel.permissions_for(ctx.me).manage_channels else ctx.channel

        if not duration:
            await channel.edit(slowmode_delay=0)
            return await ctx.send(f"Messages in **{channel.name}** can now be sent without slow mode")

        created_at = ctx.message.created_at
        delta: datetime.timedelta = duration.dt > (created_at + datetime.timedelta(hours=6))
        if delta:
            return await ctx.send('Duration is too long. Must be at most 6 hours.')
        seconds = (duration.dt - ctx.message.created_at).seconds
        await channel.edit(slowmode_delay=int(seconds))

        human_delay = helpers.human_timedelta(duration.dt, source=created_at)
        return await ctx.send(f"Messages in **{channel.name}** can now be sent **every {human_delay}**")

    @commands.command()
    async def archive(self, ctx, channel: typing.Optional[discord.Thread], *, reason: str = None):
        """
        Archives the current thread, or any thread mentioned.
        # Optionally, input a reason to be displayed in the message.
        """
        channel = channel or ctx.channel
        if not isinstance(channel, discord.Thread):
            return await ctx.send("That's not a thread!")

        await channel.send(f"Thread archived by **{ctx.author}**"
                           f"\n{f'**With reason:** {reason}' if reason else ''}")
        await channel.edit(archived=True)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def block(self, ctx, *, member: discord.Member):
        """Blocks a user from your channel."""

        if not can_execute_action(ctx, ctx.author, member):
            return await ctx.send('You are not high enough in role hierarchy to do that!')

        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        try:
            await ctx.channel.set_permissions(member, reason=reason,
                                              send_messages=False,
                                              add_reactions=False,
                                              create_public_threads=False,
                                              create_private_threads=False,
                                              send_messages_in_threads=False)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send('Something went wrong...')
        else:
            await ctx.send(f'✅ **|** Blocked **{discord.utils.remove_markdown(str(member))}** from **{ctx.channel}**')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unblock(self, ctx, *, member: discord.Member):
        """Unblocks a user from your channel."""

        if not can_execute_action(ctx, ctx.author, member):
            return await ctx.send('You are not high enough in role hierarchy to do that!')

        reason = f'Unblock by {ctx.author} (ID: {ctx.author.id})'

        try:
            await ctx.channel.set_permissions(member, reason=reason,
                                              send_messages=None,
                                              add_reactions=None,
                                              create_public_threads=None,
                                              create_private_threads=None,
                                              send_messages_in_threads=None)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send('Something went wrong...')
        else:
            await ctx.send(f'✅ **|** Unblocked **{discord.utils.remove_markdown(str(member))}** from **{ctx.channel}**')

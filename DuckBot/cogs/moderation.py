import argparse
import asyncio
import datetime
import time

import discord
import re
import shlex
import typing
from collections import Counter

from discord.ext import commands, tasks, menus

from helpers import time_inputs as helpers

import errors


def setup(bot):
    bot.add_cog(Moderation(bot))


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


def can_execute_action(ctx, user, target):
    return user == ctx.guild.owner or \
           (user.top_role > target.top_role and
            target != ctx.guild.owner)


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


class BanEmbed(menus.ListPageSource):
    def __init__(self, data, per_page=15):
        super().__init__(data, per_page=per_page)

    @staticmethod
    async def format_page(entries):
        embed = discord.Embed(title=f"Server bans ({len(entries)})",
                              description="\n".join(entries))
        embed.set_footer(text=f"To unban do db.unban [entry]\nMore user info do db.baninfo [entry]")
        return embed


class Confirm(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


class Moderation(commands.Cog):
    """
    🔨 Commands to facilitate server moderation, and all utilities for admins and mods.
    """

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.temporary_mutes.start()

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
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=5)
        await ctx.message.delete(delay=5)

    @staticmethod
    async def do_removal(ctx: commands.Context, limit: int, predicate, *, before=None, after=None):
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
                deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
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

    @commands.group(invoke_without_command=True, aliases=['prefix'])
    async def prefixes(self, ctx: commands.Context) -> discord.Message:
        """ Lists all the bots prefixes. """
        prefixes = await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True)
        embed = discord.Embed(title="Here are my prefixes:",
                              description=ctx.me.mention + '\n' + '\n'.join(prefixes),
                              color=ctx.me.color)
        return await ctx.send(embed=embed)

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefixes.command(name="add")
    async def prefixes_add(self, ctx: commands.Context,
                           new: str) -> discord.Message:
        """Adds a prefix to the bots prefixes.\nuse quotes to add spaces: %PRE%prefix \"duck \" """

        old = list(await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True))

        if len(new) > 50:
            return await ctx.send("Prefixes can only be up to 50 characters!")

        if len(old) > 30:
            return await ctx.send("You can only have up to 20 prefixes!")

        if new not in old:
            old.append(new)
            await self.bot.db.execute(
                "INSERT INTO prefixes(guild_id, prefix) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET prefix = $2",
                ctx.guild.id, old)

            self.bot.prefixes[ctx.guild.id] = old

            return await ctx.send(f"**Successfully added `{new}`**\nMy prefixes are: `{'`, `'.join(old)}`")
        else:
            return await ctx.send(f"That is already one of my prefixes!")

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefixes.command(name="remove", aliases=['delete'])
    async def prefixes_remove(self, ctx: commands.Context,
                              prefix: str) -> discord.Message:
        """Removes a prefix from the bots prefixes.\nuse quotes to add spaces: %PRE%prefix \"duck \" """

        old = list(await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True))

        if prefix in old:
            old.remove(prefix)
            await self.bot.db.execute(
                "INSERT INTO prefixes(guild_id, prefix) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET prefix = $2",
                ctx.guild.id, old)

            self.bot.prefixes[ctx.guild.id] = old

            return await ctx.send(f"**Successfully removed `{prefix}`**\nMy prefixes are: `{'`, `'.join(old)}`")
        else:
            return await ctx.send(f"That is not one of my prefixes!")

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefixes.command(name="clear", aliases=['delall'])
    async def prefixes_clear(self, ctx):
        """ Clears the bots prefixes, resetting it to default. """
        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, prefix) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET prefix = $2",
            ctx.guild.id, None)
        self.bot.prefixes[ctx.guild.id] = self.bot.PRE
        return await ctx.send("**Cleared prefixes!**")

    @commands.command(help="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: typing.Optional[str] = None):
        if member == ctx.author:
            await self.error_message(ctx, 'You can\'t kick yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            return await self.error_message(ctx, 'I\'m not high enough in role hierarchy to kick that member!')
        if member.top_role < ctx.author.top_role or ctx.author.id == ctx.guild.owner_id:
            mem_embed = discord.Embed(description=f"**{ctx.message.author}** has kicked you from **{ctx.guild.name}**",
                                      color=ctx.me.color)
            if reason:
                mem_embed.set_footer(text=f'reason: {reason}')
            try:
                await member.send(embed=mem_embed)
                dm_success = '✅'
            except discord.HTTPException:
                dm_success = '❌'
            await member.kick(reason=f"{ctx.author} (ID: {ctx.author.id}): {reason}")
            if reason:
                action_reason = f"\n```\nreason: {reason}```"
            else:
                action_reason = ''

            embed = discord.Embed(
                description=f"{ctx.author.mention} kicked **{member}**({member.mention}){action_reason}",
                color=ctx.me.color)
            embed.set_footer(text=f'ID: {member.id} | DM sent: {dm_success}')
            await ctx.send(embed=embed)

        else:
            await self.error_message(ctx, 'Member is higher than you in role hierarchy')
            return

    @commands.command(help="Bans a member from the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    async def ban(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: typing.Optional[str] = None):
        member = user
        if member == ctx.author:
            return await self.error_message(ctx, 'You can\'t ban yourself')
        if isinstance(user, discord.Member):
            if member.top_role >= ctx.me.top_role:
                return await self.error_message(ctx, 'I\'m not high enough in role hierarchy to ban that member!')
            if member.top_role < ctx.author.top_role or ctx.author.id == ctx.guild.owner_id:
                mem_embed = discord.Embed(
                    description=f"**{ctx.message.author}** has banned you from **{ctx.guild.name}**",
                    color=ctx.me.color)
                if isinstance(reason, str):
                    mem_embed.set_footer(text=f'reason: {reason}')
                try:
                    await member.send(embed=mem_embed)
                    dm_success = '✅'
                except discord.HTTPException:
                    dm_success = '❌'
            else:
                await self.error_message(ctx, 'Member is higher than you in role hierarchy')
                return

        else:
            dm_success = '❌'

        if isinstance(reason, str):
            action_reason = f"\n```\nreason: {reason}```"
        else:
            action_reason = ''

        embed = discord.Embed(description=f"{ctx.author.mention} banned **{member}**({member.mention}){action_reason}",
                              color=ctx.me.color)
        embed.set_footer(text=f'ID: {member.id} | DM sent: {dm_success}')
        await ctx.send(embed=embed)

        await ctx.guild.ban(member, reason=f"{ctx.author} (ID: {ctx.author.id}): {reason or ''}")

    @commands.command(aliases=['sn', 'nick'])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, manage_nicknames=True)
    async def setnick(self, ctx: commands.Context, member: discord.Member, *, new: str = None) -> \
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
    async def cleanup(self, ctx: commands.Context, amount: int = 25):
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

        async with ctx.typing():
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                prefix = tuple(await self.bot.get_pre(self.bot, ctx.message))

                def check(msg):
                    return msg.author == ctx.me or msg.content.startswith(prefix)

                deleted = await ctx.channel.purge(limit=amount, check=check, before=ctx.message.created_at)
            else:
                def check(msg):
                    return msg.author == ctx.me

                deleted = await ctx.channel.purge(limit=amount, check=check, bulk=False, before=ctx.message.created_at)
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

    # ------------------------------------------------------------------------------#
    # --------------------------------- UNBAN --------------------------------------#
    # ------------------------------------------------------------------------------#

    @commands.command(help="unbans a member # run without arguments to get a list of entries")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx, entry: int):
        number = entry
        if number <= 0:
            embed = discord.Embed(color=0xFF0000,
                                  description=f"__number__ must be greater than 1"
                                              f"\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`"
                                              f"\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        bans = await ctx.guild.bans()

        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return

        try:
            ban_entry = bans[number]
        except IndexError:
            embed = discord.Embed(color=0xFF0000,
                                  description=f"That member was not found. "
                                              f"\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`"
                                              f"\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        await ctx.guild.unban(ban_entry.user)
        await ctx.send(f'unbanned **{ban_entry.user}**')

    # ------------------------------------------------------------------------------#
    # -------------------------------- BAN LIST ------------------------------------#
    # ------------------------------------------------------------------------------#

    @commands.command(help="Gets the current guild's list of bans")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def bans(self, ctx: commands.Context) -> discord.Message:
        bans = await ctx.guild.bans()
        if not bans:
            return await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
        desc = []
        number = 1
        for ban_entry in bans:
            desc.append(f"**{number}) {ban_entry.user}**")
            number = number + 1
        pages = menus.MenuPages(source=BanEmbed(desc), clear_reactions_after=True)
        await pages.start(ctx)

    # ------------------------------------------------------------------------------#
    # -------------------------------- BAN INFO ------------------------------------#
    # ------------------------------------------------------------------------------#

    @commands.command(help="brings info about a ban # run without arguments to get a list of entries", usage="[entry]")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def baninfo(self, ctx, number: typing.Optional[int]):
        """
        Information about a ban from the list of bans.
        For the list of bans do %PRE%bans
        """
        if not ctx.channel.permissions_for(ctx.me).ban_members:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return

        if not number:
            bans = await ctx.guild.bans()

            if not bans:
                await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
                return

            desc = []
            number = 1
            for ban_entry in bans:
                desc.append(f"**{number}) {ban_entry.user}**")
                number = number + 1
            pages = menus.MenuPages(source=BanEmbed(desc), clear_reactions_after=True)
            await pages.start(ctx)
            return

        if number <= 0:
            embed = discord.Embed(
                color=0xFF0000,
                description=f"__number__ must be greater than 1"
                            f"\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`"
                            f"\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        bans = await ctx.guild.bans()

        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return
        try:
            ban_entry = bans[number]
        except IndexError:
            embed = discord.Embed(color=0xFF0000,
                                  description=f"That member was not found. "
                                              f"\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`"
                                              f"\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        date = ban_entry.user.created_at
        embed = discord.Embed(color=ctx.me.color,
                              description=f"""```yaml
       user: {ban_entry.user}
    user id: {ban_entry.user.id}
     reason: {ban_entry.reason}
 created at: {date.strftime("%b %-d %Y at %-H:%M")} UTC
```""")
        embed.set_author(name=ban_entry.user, icon_url=ban_entry.user.display_avatar.url)
        await ctx.send(embed=embed)

    # --------------------------------------------------------------------------------#
    # -------------------------------- MUTE STUFF ------------------------------------#
    # --------------------------------------------------------------------------------#

    # Indefinitely mute member

    @commands.command(aliases=['stfu', 'shut', 'silence'])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, reason: str = None) -> discord.Message:
        """
        Mutes a member indefinitely.
        """
        only_reason = reason
        reason = reason or "No reason given"
        reason = f"Mute by {ctx.author} ({ctx.author.id}): {reason}"
        if not can_execute_action(ctx, ctx.author, member):
            return await ctx.send("You're not high enough in role hierarchy to mute that member.")

        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            raise errors.MuteRoleNotFound

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to assign that role.")

        try:
            await member.add_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                  ctx.guild.id, member.id)

        # in a command that adds new task in db
        if self.temporary_mutes.is_running():
            self.temporary_mutes.restart()
        else:
            self.temporary_mutes.start()

        if not only_reason:
            return await ctx.send(f"**{ctx.author}** muted **{member}**",
                                  allowed_mentions=discord.AllowedMentions().none())
        return await ctx.send(f"**{ctx.author}** muted **{member}**"
                              f"\nReason: {only_reason}",
                              allowed_mentions=discord.AllowedMentions().none())

    # Get mute role

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, reason: str = None):
        """
        Unmutes a member
        """
        only_reason = reason
        reason = reason or "No reason given"
        reason = f"Mute by {ctx.author} ({ctx.author.id}): {reason}"
        if not can_execute_action(ctx, ctx.author, member):
            return await ctx.send("You're not high enough in role hierarchy to mute that member.")

        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            raise errors.MuteRoleNotFound

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to assign that role.")

        try:
            await member.remove_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to remove the `{role.name}` role")

        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
                                  ctx.guild.id, member.id)

        # in a command that adds new task in db
        if self.temporary_mutes.is_running():
            self.temporary_mutes.restart()
        else:
            self.temporary_mutes.start()

        if not only_reason:
            await ctx.send(f"**{ctx.author}** unmuted **{member}**",
                           allowed_mentions=discord.AllowedMentions().none())
        else:
            await ctx.send(f"**{ctx.author}** unmuted **{member}**"
                           f"\nReason: {only_reason}",
                           allowed_mentions=discord.AllowedMentions().none())

    # Add mute role

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole(self, ctx: commands.Context, new_role: discord.Role = None):
        """
        Manages the current mute role. If no role is specified, shows the current mute role.
        """
        if ctx.invoked_subcommand is None:
            if new_role:
                await self.bot.db.execute(
                    "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                    "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                    ctx.guild.id, new_role.id)

                return await ctx.send(f"Updated the muted role to {new_role.mention}!",
                                      allowed_mentions=discord.AllowedMentions().none())

            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                raise errors.MuteRoleNotFound

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                raise errors.MuteRoleNotFound

            return await ctx.send(f"This server's mute role is {role.mention}"
                                  f"\nChange it with the `muterole [new_role]` command",
                                  allowed_mentions=discord.AllowedMentions().none())

    # Remove mute role

    @commands.has_permissions(manage_guild=True)
    @muterole.command(name="remove", aliases=["unset"])
    async def muterole_remove(self, ctx: commands.Context):
        """
        Unsets the mute role for the server,
        note that this will NOT delete the role, but only remove it from the bot's database!
        If you want to delete it, do "%PRE%muterole delete" instead
        """
        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
            ctx.guild.id, None)

        return await ctx.send(f"Removed this server's mute role!",
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.has_permissions(manage_guild=True)
    @muterole.command(name="create")
    async def muterole_create(self, ctx: commands.Context):
        starting_time = time.monotonic()

        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

        role = ctx.guild.get_role(int(mute_role))
        if isinstance(role, discord.Role):
            raise errors.MuteRoleNotFound

        await ctx.send(f"Creating Muted role, and applying it to all channels."
                       f"\nThis may take awhile ETA: {len(ctx.guild.channels)} seconds.")

        async with ctx.typing():
            permissions = discord.Permissions(send_messages=False,
                                              add_reactions=False,
                                              connect=False,
                                              speak=False)
            role = await ctx.guild.create_role(name="Muted", colour=0xff4040, permissions=permissions,
                                               reason=f"DuckBot mute-role creation. Requested "
                                                      f"by {ctx.author} ({ctx.author.id})")
            await self.bot.db.execute(
                "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                ctx.guild.id, role.id)

            modified = 0
            for channel in ctx.guild.channels:
                perms = channel.overwrites_for(role)
                perms.send_messages = False
                perms.add_reactions = False
                perms.connect = False
                perms.speak = False
                try:
                    await channel.set_permissions(role, overwrite=perms,
                                                  reason=f"DuckBot mute-role creation. Requested "
                                                         f"by {ctx.author} ({ctx.author.id})")
                    modified += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
                await asyncio.sleep(1)

            ending_time = time.monotonic()
            complete_time = (ending_time - starting_time)
            await ctx.send(f"done! took {round(complete_time, 2)} seconds"
                           f"\nSet permissions for {modified} channel{'' if modified == 1 else 's'}!")

    @muterole.command(name="delete")
    @commands.has_permissions(manage_guild=True)
    async def muterole_delete(self, ctx: commands.Context):
        """
        Deletes the server's mute role if it exists.
        # If you want to keep the role but not
        """
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            await self.bot.db.execute(
                "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                ctx.guild.id, None)

            return await ctx.send("It seems like the muted role was already deleted, or I can't find it right now!"
                                  "\n I removed it from my database. If the mute role still exists, delete it manually")

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to delete that role!")

        if role > ctx.author.top_role:
            return await ctx.send("You're not high enough in role hierarchy to delete that role!")

        try:
            await role.delete(reason=f"Mute role deletion. Requested by {ctx.author} ({ctx.author.id})")
        except discord.Forbidden:
            return await ctx.send("I can't delete that role! But I deleted it from my database")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while deleting the muted role!")
        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
            ctx.guild.id, None)
        await ctx.send("🚮")

    @muterole.command(name="fix")
    @commands.has_permissions(manage_guild=True)
    async def muterole_fix(self, ctx: commands.Context):
        async with ctx.typing():
            starting_time = time.monotonic()
            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                raise errors.MuteRoleNotFound

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                raise errors.MuteRoleNotFound

            modified = 0
            for channel in ctx.guild.channels:
                perms = channel.overwrites_for(role)
                perms.send_messages = False
                perms.add_reactions = False
                perms.connect = False
                perms.speak = False
                try:
                    await channel.set_permissions(role, overwrite=perms,
                                                  reason=f"DuckBot mute-role creation. Requested "
                                                         f"by {ctx.author} ({ctx.author.id})")
                    modified += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
                await asyncio.sleep(1)

            ending_time = time.monotonic()
            complete_time = (ending_time - starting_time)
            await ctx.send(f"done! took {round(complete_time, 2)} seconds"
                           f"\nSet permissions for {modified} channel{'' if modified == 1 else 's'}!")

    # self mutes

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    async def selfmute(self, ctx, *, duration: helpers.ShortTime):
        """
        Temporarily mutes yourself for the specified duration.
        Duration must be a short time, for example: 1s, 5m, 3h, or a combination of those, like 3h5m25s
        You can only mute yourself for a maximum of 24 hours and a minimum of 5 minutes.
        note: # Do not ask a moderator to unmute you.
        """
        reason = "self mute"
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            raise errors.MuteRoleNotFound

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to assign the muted role!")

        created_at = ctx.message.created_at
        if duration.dt > (created_at + datetime.timedelta(days=1)):
            return await ctx.send('Duration is too long. Must be at most 24 hours.')

        if duration.dt < (created_at + datetime.timedelta(minutes=5)):
            return await ctx.send('Duration is too short. Must be at least 5 minutes.')

        delta = helpers.human_timedelta(duration.dt, source=created_at)
        warning = (f"_Are you sure you want to mute yourself for **{delta}**?_"
                   f"\n**__Don't ask the moderators to undo this!__**")
        confirm = await Confirm(warning).prompt(ctx)
        if not confirm:
            return

        try:
            await ctx.author.add_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute("INSERT INTO temporary_mutes(guild_id, member_id, reason, end_time) "
                                  "VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, member_id) DO "
                                  "UPDATE SET reason = $3, end_time = $4",
                                  ctx.guild.id, ctx.author.id, reason, duration.dt)

        # in a command that adds new task in db
        if self.temporary_mutes.is_running():
            self.temporary_mutes.restart()
        else:
            self.temporary_mutes.start()

        await ctx.send("<:shut:882382724382490644> 👍")

    # Temp-mute

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def tempmute(self, ctx, member: discord.Member, *, duration: helpers.ShortTime):
        """
        Temporarily mutes a member for the specified duration.
        # Duration must be a short time, for example: 1s, 5m, 3h, or a combination of those, like 3h5m25s
        """

        reason = f"Temporary mute by {ctx.author} ({ctx.author.id})"

        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            raise errors.MuteRoleNotFound

        if not can_execute_action(ctx, ctx.author, member):
            return await ctx.send("You're not high enough in role hierarchy to do that!")

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to assign that role.")

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

        if self.temporary_mutes.is_running():
            self.temporary_mutes.restart()
        else:
            self.temporary_mutes.start()

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
        perms.send_messages = False
        perms.add_reactions = False
        perms.connect = False
        perms.speak = False
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
        perms.send_messages = True
        perms.add_reactions = True

        await channel.set_permissions(ctx.me, overwrite=perms,
                                      reason=f'Channel lockdown by {ctx.author} ({ctx.author.id})')

        perms = channel.overwrites_for(role)
        perms.send_messages = False
        perms.add_reactions = False

        await channel.set_permissions(role, overwrite=perms,
                                      reason=f'Channel lockdown for {role.name} by {ctx.author} ({ctx.author.id})')
        await ctx.send(f"Locked down **{channel.name}** for **{role.name}**", allowed_mentions=discord.AllowedMentions().none())

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
        perms.send_messages = None
        perms.add_reactions = None

        await channel.set_permissions(role, overwrite=perms,
                                      reason=f'Channel lockdown for {role.name} by {ctx.author} ({ctx.author.id})')

        await ctx.send(f"Unlocked **{channel.name}** for **{role.name}**", allowed_mentions=discord.AllowedMentions().none())

    @commands.command(usage="[channel] <duration|reset>")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], *,
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

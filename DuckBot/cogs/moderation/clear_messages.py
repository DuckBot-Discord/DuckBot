import argparse
import contextlib
from datetime import timedelta
import re
import shlex
import typing
from collections import Counter

import asyncio
import discord
from discord.ext import commands

from DuckBot.helpers.context import CustomContext
from DuckBot.errors import NoQuotedMessage
from ._base import ModerationBase


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class RemovalCommands(ModerationBase):
    @staticmethod
    async def do_removal(
        ctx: CustomContext, limit: typing.Optional[int], predicate, *, before=None, after=None, bulk: bool = True
    ):
        if limit and limit > 2000:
            return await ctx.send(f'Too many messages to search given ({limit}/2000)')
        assert isinstance(ctx.channel, (discord.abc.GuildChannel, discord.Thread))

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

    @commands.group(name="clean", aliases=['purge', 'delete', 'remove', 'clear'])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def remove(self, ctx, search: int = 100):
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
            messages = [
                f'{deleted} message'
                f'{" and its associated thread was" if deleted == 1 else "s and their associated messages were"} '
                f'removed.'
            ]

            if deleted:
                messages.append('')
                spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
                messages.extend(f'**{name}**: {count}' for name, count in spammers)

            to_send = '\n'.join(messages)

            if len(to_send) > 2000:
                await ctx.send(
                    f'Successfully removed {deleted} messages and their associated threads.', delete_after=10, reply=False
                )
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

    @remove.command(name='between')
    async def remove_between(self, ctx: CustomContext):
        if not ctx.reference:
            raise NoQuotedMessage
        await self.do_removal(ctx, limit=None, predicate=lambda m: not m.pinned, after=ctx.reference.id)

    @remove.command(
        name="custom",
        brief="A more advanced purge command, with a command line-like interface. "
        "\nSee help on this command for more info, using `%PRE%help remove custom`",
    )
    async def remove_custom(self, ctx, *, args: str):
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
            args: typing.Any = parser.parse_args(shlex.split(args))
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

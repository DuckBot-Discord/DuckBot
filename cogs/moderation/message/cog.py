from __future__ import annotations

import datetime
from collections import Counter
from typing import Optional, Annotated

import discord
from discord.ext import commands

from utils import DuckCog, DuckContext, group, command
from .parser import SearchResult, PurgeSearchConverter
from .tokens import DateDeterminer


class MessagePurge(DuckCog):
    async def purge(self, ctx: commands.Context, search: int | None, predicate, **extra_kwargs):
        if not isinstance(ctx.channel, discord.abc.GuildChannel):
            return "..."

        async with ctx.typing():
            messages = await ctx.channel.purge(limit=search, check=predicate, **extra_kwargs)

            spammers = Counter(str(m.author) for m in messages)
            deletion_header = f"Deleted {len(messages)} message" + ('s.' if len(messages) != 1 else '.')

            if spammers:
                formatted_counts = '\n\n' + '\n'.join(
                    f"**{k}:** {v}" for k, v in sorted(spammers.items(), key=lambda x: x[1], reverse=True)
                )

                if (len(deletion_header) + len(formatted_counts)) <= 2000:
                    deletion_header += formatted_counts

        return deletion_header

    @group(
        name='purge',
        aliases=['remove', 'clear', 'delete', 'clean'],
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.is_owner()
    async def purge_messages(
        self,
        ctx: DuckContext,
        search: Optional[int] = 500,
        *,
        search_argument: Annotated[Optional[SearchResult], PurgeSearchConverter] = None,
    ):
        """Removes messages that meet a criteria.

        This command uses syntax similar to Discord's search bar. Arguments can be separated with `and` and `or` for a more granular search. You can also use parentheses to narrow down your search.

        Flags
        -----

        `user: <@someone>` Removes messages from the given user.
        `has: [link|embed|file|video|image|sound|sticker|reaction|emoji]` Checks if the message has one one of these things, just like in the discord search feature.
        `is: [bot|human|webhook]` Checks the type of user. \\*`bot` does not match webhooks.
        `contains: <text>` Messages that contain a substring.
        `prefix: <text>` Messages that start with a string.
        `suffix: <text>` Messages that end with a string.
        `pinned: [yes|no]` Whether a message is pinned. (default: no)

        To narrow down *when* to search, you can use these arguments:
        These three date arguments must __not__ be within parentheses, and __cannot__ be separated with `or` from other search terms.
        `before: <Message ID>` Messages before the given message ID.
        `after: <Message ID>` Messages after the given message ID.
        `around: <Message ID>` Messages around the given message ID. (or `during:`)

        Notes
        -----

        In order to use this command, you must have Manage Messages permissions. So does the bot. Cannot be executed in DMs.
        When the command is done, you will get a recap of the removed messages, composed of the authors and a count of messages for each.

        Examples
        --------

        `db.purge from: @duckbot has: image`
        `db.purge has: link or has: reactions`
        `db.purge 100`
        `db.purge 350 from: @leocx1000 contains: discord.gg`
        `db.purge (has:link contains: google.com) or pinned:yes`

        """
        extra_kwargs = {}

        if search_argument:
            await search_argument.init(ctx)

            predicate = search_argument.build_predicate()

            # Let's look for `after`, `before` and `around` (DateDelim)
            for token in search_argument.predicates:
                if isinstance(token, DateDeterminer):
                    extra_kwargs[token.invoked_with] = token.parsed_argument.created_at

        else:
            predicate = lambda m: not m.pinned

        # Only allow BULK deletion. Single-message-deletion is too rate-limited, especially for ancient messages.
        if 'after' in extra_kwargs:
            after = extra_kwargs['after']
            cut_off = ctx.message.created_at - datetime.timedelta(days=14)
            if after > cut_off:
                return await ctx.send(
                    f'Cannot delete messages older than 14 days. ({discord.utils.format_dt(cut_off, "D")})'
                )
        else:
            extra_kwargs['after'] = ctx.message.created_at - datetime.timedelta(days=14)

        if 'before' not in extra_kwargs:
            # For accountability, set this so it doesn't delete OP's message.
            extra_kwargs['before'] = ctx.message.created_at

        if isinstance(ctx.channel, discord.abc.GuildChannel):
            if not await ctx.confirm(f'Are you sure you want to search through {search} messages and delete matching ones?'):
                return

            deletion_header = await self.purge(ctx, search, predicate, **extra_kwargs)
            await ctx.send(deletion_header, delete_after=10)
        else:
            await ctx.send('Somehow this was ran in a DM?')

    @command()
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def cleanup(self, ctx: DuckContext, search: int = 25):
        """
        Cleans up the bot's messages from the channel.

        If a search number is specified, it searches that many messages to delete.
        If the bot has Manage Messages permissions then it will try to delete
        messages that look like they invoked the bot as well.

        After the cleanup is completed, the bot will send you a message with
        which people got their messages deleted and their count. This is useful
        to see which users are spammers.

        Members with Manage Messages can search up to 1000 messages.
        Members without can search up to 25 messages.
        """
        if not ctx.permissions.manage_messages:
            search = min(search, 25)
        else:
            search = min(search, 1000)
        prefixes = tuple(await ctx.bot.get_prefix(ctx.message))
        check = lambda m: (m.author == ctx.me or m.content.startswith(prefixes)) and not m.mentions
        message = await self.purge(ctx, search, check)
        await ctx.send(message, delete_after=10)

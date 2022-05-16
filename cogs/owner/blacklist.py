from __future__ import annotations

import datetime
import math
import asyncpg
import discord
from typing import List, Optional, Union


from utils import DuckCog, DuckContext, ShortTime, mdr, format_date, human_timedelta, group


class BlackListManagement(DuckCog):
    async def format_entry(self, entry: asyncpg.Record) -> Optional[str]:
        """Formats an entry from the blacklist.

        Parameters
        ----------
        entry: List[List[str, int, int, datetime.datetime]]
            the entry to format.

        Returns
        -------
        str
            the formatted entry.
        """
        blacklist_type: str = entry['blacklist_type']
        entity_id: int = entry['entity_id']
        guild_id: int = entry['guild_id']
        created: datetime.datetime = entry['created_at']
        # No tuple unpacking.

        time = format_date(created)

        guild = f"{self.bot.get_guild(guild_id) or 'Unknown Guild'} ({guild_id})" if guild_id else 'Global'

        if blacklist_type == "user":
            user = f"@{await self.bot.get_or_fetch_user(entity_id) or 'Unknown User'} ({entity_id})"
            return f"[{time} | USER] {user}" + (f" in guild: {guild}" if guild else '')

        elif blacklist_type == "guild":
            guild = f"{self.bot.get_guild(entity_id) or 'Unknown Guild'} ({entity_id})"
            return f"[{time} | GUILD] {guild}"

        elif blacklist_type == "channel":
            or_g = self.bot.get_guild(guild_id)
            meth = or_g.get_channel if isinstance(or_g, discord.Guild) else self.bot.get_channel

            chan = f"{meth(entity_id) or 'Unknown Channel'} ({entity_id})"  # type: ignore
            return f"[{time} | CHANNEL] {chan}" + (f" in guild: {guild}" if guild else '')

    @group(name='blacklist', aliases=['bl'], invoke_without_command=True)
    async def blacklist(
        self,
        ctx: DuckContext,
        entity: Union[discord.Guild, discord.User, discord.abc.GuildChannel],
        when: Optional[ShortTime] = None,
    ) -> None:
        """|coro|

        Base command for blacklist management.
        Also adds an entity to the bot globally.

        Parameters
        ----------
        entity: Union[:class:`discord.Guild`, :class:`discord.User`, :class:`discord.abc.GuildChannel`]
            the entity to block globally.
        when: :class:`utils.ShortTime`
            the time to block the entity. Must be a short time.
        """
        args: List[Union[str, discord.Guild, discord.User, discord.abc.GuildChannel]] = [entity]
        if when:
            args.append(f" for {human_timedelta(when.dt)}")
            dt = when.dt
        else:
            args.append('')
            dt = None
        blacklisted: bool = False
        if isinstance(entity, discord.Guild):
            blacklisted = await self.bot.blacklist.add_guild(entity, end_time=dt)
        elif isinstance(entity, discord.User):
            blacklisted = await self.bot.blacklist.add_user(entity, end_time=dt)
        elif isinstance(entity, discord.abc.GuildChannel):
            blacklisted = await self.bot.blacklist.add_channel(entity, end_time=dt)
        etype = str(type(entity).__name__).split('.')[-1]
        await ctx.send(ctx.tick(blacklisted, ('added {}{}.' if blacklisted else '{} already blacklisted{}.').format(*args)))

    @blacklist.command(name='remove', aliases=['rm'])
    async def blacklist_remove(
        self, ctx: DuckContext, entity: Union[discord.Guild, discord.User, discord.abc.GuildChannel]
    ) -> None:
        """|coro|

        Removes an entity from the global blacklist.

        Parameters
        ----------
        entity: Union[:class:`discord.Guild`, :class:`discord.User`, :class:`discord.abc.GuildChannel`]
            the entity to remove from the global blacklist.
        """
        removed: bool = False
        if isinstance(entity, discord.Guild):
            removed = await self.bot.blacklist.remove_guild(entity)
        elif isinstance(entity, discord.User):
            removed = await self.bot.blacklist.remove_user(entity)
        elif isinstance(entity, discord.abc.GuildChannel):
            removed = await self.bot.blacklist.remove_channel(entity)
        etype = str(type(entity).__name__).split('.')[-1]
        await ctx.send(ctx.tick(removed, '{} removed' if removed else '{} not blacklisted').format(etype))

    @blacklist.command(name='local')
    async def blacklist_local(
        self,
        ctx: DuckContext,
        guild: Optional[discord.Guild],
        user: Union[discord.Member, discord.User],
        when: Optional[ShortTime] = None,
    ) -> None:
        """|coro|

        Adds an entity to the local blacklist.

        Parameters
        ----------
        guild: Optional[:class:`discord.Guild`]
            the guild to add the entity to.
        user: Union[:class:`discord.Member`, :class:`discord.User`]
            the user to add to the local blacklist.
        when: :class:`utils.ShortTime`
            the time to block the entity. Must be a short time.
        """
        dt = when.dt if when else None
        if isinstance(user, discord.User) and not guild:
            await ctx.send('Please specify a guild or mention a member not a user.')
            return
        if isinstance(user, discord.Member):
            guild = guild or user.guild

        success = await self.bot.blacklist.add_user(user, guild, dt)
        etype = str(type(user).__name__).split('.')[-1]
        await ctx.send(
            ctx.tick(success, 'Added {} for guild {}.' if success else '{} already blacklisted in {}.').format(
                etype, mdr(guild)
            )
        )

    @blacklist.command(name='list', aliases=['ls'])
    async def blacklist_list(self, ctx: DuckContext, page: int = 1) -> None:
        """|coro|
        Gets a list of all blocked users in a channel.
        If no channel is specified, it will show the
        blocked users for all the chnannels in the server.

        Parameters
        ----------
        page: :class:`int`
            The page number to show.
        """
        guild = ctx.guild
        if guild is None:
            return

        if page < 1:
            page = 1

        result = await self.bot.pool.fetch(
            "SELECT blacklist_type, entity_id, guild_id, created_at " "FROM blacklist ORDER BY created_at DESC OFFSET $1",
            (page - 1) * 10,
        )
        count = await self.bot.pool.fetchval("SELECT COUNT(*) FROM blacklist")

        rows: List[Optional[str]] = [await self.format_entry(row) for row in result]

        if not rows:
            await ctx.send(ctx.tick(False, 'no entries'))
            return

        formatted = '```\n' + '\n'.join(rows) + '\n```'  # type: ignore
        pages = math.ceil(count / 10)

        message = (
            f"📋 **|** Blacklisted entities - Showing `{len(result)}/{count}` entries - Page `{page}/{pages}`:\n{formatted}"
        )
        await ctx.send(message)

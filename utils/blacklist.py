import typing

import asyncpg
import discord

from typing import (
    TYPE_CHECKING,
    DefaultDict,
    Set,
    Tuple,
    Optional,
    Literal,
    Any,
)

from collections import defaultdict
from datetime import datetime
from discord.ext.commands import Context

if TYPE_CHECKING:
    from bot import DuckBot
else:
    # I don't know why mad, chai pls fix
    from discord.ext.commands import Bot as DuckBot

from utils import EntityBlacklisted


__all__: Tuple[str, ...] = (
    "DuckBlacklistManager",
)


class FakeChannel:
    """ A fake channel to pass to the remove_channel method.

    Parameters
    ----------
    id: :class:`int`
        The channel id.
    guild_id: :class:`int`

    Attributes
    ----------
    id: :class:`int`
        The channel id.
    guild: :class:`discord.Object`
        An object representing the guild.
    """

    __slots__: Tuple[str, ...] = ('id', 'guild')

    # noinspection PyShadowingBuiltins
    def __init__(self, id: int, guild_id: int):
        self.id = id
        self.guild = discord.Object(id=guild_id)


class DuckBlacklistManager:
    """
    A helper class to handle blacklisting for the bot.

    Parameters
    ----------
    bot: :class:`DuckBot`
        The bot instance.

    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance.
    _global_blacklisted_users: :class:`set`
        A set of blacklisted user ids.
    _guild_blacklisted_users: DefaultDict[:class:`int`, Set[:class:`int`]]
        A dict of guild ids to blacklisted user ids.
    _blacklisted_channels: DefaultDict[:class:`int`, Set[:class:`int`]]
        A dict of guild ids to blacklisted channel ids.
    _blacklisted_guilds: :class:`set`
        A set of blacklisted guild ids.

    """
    __slots__: Tuple[str, ...] = (
        "bot",
        "_global_blacklisted_users",
        "_blacklisted_channels",
        "_blacklisted_guilds",
        "_guild_blacklisted_users",
    )

    def __init__(self, bot: DuckBot, add_check: bool = True):
        self.bot: DuckBot = bot

        self.bot.add_listener(
            self._temp_blacklist_end_event,
            'on_blacklist_timer_complete'
        )

        if add_check:
            self.bot.add_check(self.check_context, call_once=True)

        # Caches
        self._blacklisted_guilds: Set[int] = set()
        self._global_blacklisted_users: Set[int] = set()
        self._guild_blacklisted_users: DefaultDict[int, Set[int]] = defaultdict(set)
        self._blacklisted_channels: DefaultDict[int, Set[int]] = defaultdict(set)

    def __del__(self):
        self.bot.remove_listener(
            self._temp_blacklist_end_event,
            'on_blacklist_timer_complete'
        )
        self.bot.remove_check(self.check_context, call_once=True)

    async def build_cache(self, conn: asyncpg.Connection) -> None:
        """|coro|
        Builds the blacklist cache

        Parameters
        ----------
        conn: :class:`asyncpg.Pool`
            A connection to the database.
        """
        data = await conn.fetch("SELECT * FROM blacklist")
        for row in data:
            if row["blacklist_type"] == "guild":
                self._blacklisted_guilds.add(row["entity_id"])
            elif row["blacklist_type"] == "user":
                if not row["guild_id"]:
                    self._global_blacklisted_users.add(row["entity_id"])
                else:
                    self._guild_blacklisted_users[row["guild_id"]].add(row["entity_id"])
            elif row["blacklist_type"] == "channel":
                self._blacklisted_channels[row["guild_id"]].add(row["entity_id"])

    async def _temp_blacklist_end_event(
            self,
            *,
            blacklist_type: Literal['user', 'guild', 'channel'],
            entity_id: int,
            guild_id: Optional[int] = None
    ) -> None:
        """|coro|
        The event that is called when a temporary blacklist ends.
        This will be added to the bot when this call is instantiated.
        It will be registered under `on_blacklist_timer_complete`.

        Parameters
        ----------
        blacklist_type : Literal['user', 'guild', 'channel']
            The type of blacklist that is ending.
        entity_id : int
            The ID of the entity that is ending the blacklist.
        guild_id : Optional[int]
            The ID of the guild that the entity is in.
        """
        if blacklist_type == 'user':
            if not guild_id:  # will be 0 (truthy false)
                await self.remove_user(discord.Object(id=entity_id))  # type: ignore
            else:
                await self.remove_user(discord.Object(id=entity_id), discord.Object(id=guild_id))  # type: ignore
        elif blacklist_type == 'guild':
            await self.remove_guild(discord.Object(id=entity_id))  # type: ignore
        elif blacklist_type == 'channel':
            await self.remove_channel(FakeChannel(id=entity_id, guild_id=guild_id))  # type: ignore

    async def check_context(self, ctx: Context) -> bool:
        """Checks if this context is valid and nothing is blacklisted.

        Returns
        -------
        bool
            ``True`` if the user is blacklisted.

        Raises
        ------
        :class:`EntityBlacklisted`
            If the action can't be executed in this context.
        """
        if await self.bot.is_owner(ctx.author):
            # Just in case someone does the dumb.
            return True

        # Check each of the blacklists
        self.check_user(ctx.author, should_raise=True)
        self.check_channel(ctx.channel, should_raise=True)
        self.check_guild(ctx.guild, should_raise=True)
        return True

    async def add_user(self,
                       user: typing.Union[discord.User, discord.Member],
                       guild: Optional[discord.Guild] = None,
                       end_time: Optional[datetime] = None) -> bool:
        """|coro|

        Adds a user to the blacklist.

        Parameters
        ----------
        user: Union[:class:`discord.User`, :class:`discord.Member`]
            The user to blacklist.
        guild: Optional[:class:`discord.Guild`]
            The guild to blacklist the user in.
            If none is passed the user is blacklisted globally.
        end_time: Optional[:class:`datetime`]
            The time when the user will be removed from the blacklist.

        Returns
        -------
        bool
            Whether the user was added successfully or not.
        """
        # First we add the user to the cache
        if guild is None:
            self._global_blacklisted_users.add(user.id)
        else:
            self._guild_blacklisted_users[guild.id].add(user.id)

        if end_time is not None:  # Then, if the block is temporary, we create a new timer

            # We first delete all existing timers
            await self.bot.pool.fetch(
                """DELETE FROM timers
                       WHERE event = 'blacklist'
                       AND (extra->'kwargs'->'blacklist_type')::TEXT = 'user'
                       AND (extra->'kwargs'->'entity_id')::BIGINT = $1 
                       AND (extra->'kwargs'->'guild_id')::BIGINT = $2""",
                user.id, guild.id if guild else 0)

            # Then, we create a new timer.
            await self.bot.create_timer(
                end_time,
                "blacklist",
                blacklist_type='user',
                entity_id=user.id,
                guild_id=guild.id if guild else 0
            )

            # Lastly we add the user to the blacklist.
            return await self.try_query("""
                INSERT INTO blacklist (blacklist_type, entity_id, guild_id) VALUES ('user', $1, $2)
                ON CONFLICT (blacklist_type, entity_id) DO UPDATE SET created_at = NOW()
            """, user.id, guild.id if guild else 0)

        else:  # If the block is not temporary, we just add the user to the blacklist.
            query = "INSERT INTO blacklist (blacklist_type, entity_id, guild_id) VALUES ('user', $1, $2)"
            return await self.try_query(query, user.id, guild.id if guild else 0)

    async def remove_user(self, user: discord.User, guild: typing.Optional[discord.Guild] = None) -> bool:
        """|coro|

        Removes a user from the blacklist.

        Parameters
        ----------
        user: :class:`discord.User`
            The user to remove from the blacklist.
        guild: Optional[:class:`discord.Guild`]
            The guild to remove the user from
            If none is passed the user is un-blacklisted globally.


        Returns
        -------
        bool
            Whether the user was removed successfully or not.
        """
        # First we remove the user from the cache
        if not guild:
            self._global_blacklisted_users.discard(user.id)
        else:
            self._guild_blacklisted_users[guild.id].discard(user.id)

        # Then, we discard all timers that are associated with the user
        await self.bot.pool.fetch(
            """DELETE FROM timers
                   WHERE event = 'blacklist'
                   AND (extra->'kwargs'->'blacklist_type')::TEXT = 'user'
                   AND (extra->'kwargs'->'entity_id')::BIGINT = $1
                   AND (extra->'kwargs'->'guild_id')::BIGINT = $2""",
            user.id, guild.id if guild else 0)

        # Then we remove the user from the blacklist.
        query = "DELETE FROM blacklist WHERE entity_id = $1 AND guild_id = $2 AND blacklist_type = 'user' RETURNING *"
        return not not (await self.bot.pool.fetch(query, user.id, guild.id if guild else 0))

    def check_user(self, user: typing.Union[discord.User, discord.Member], should_raise: Optional[bool] = False) -> bool:
        """Checks if a user or member is blacklisted.

        Parameters
        ----------
        user: :class:`discord.User` or :class:`discord.Member`
            The user or member to check.
        should_raise: Optional[:class:`bool`]
            Weather we should raise an error i

        Returns
        -------
        bool
            Whether the user is blacklisted or not.

        Raises
        ------
        :class:`EntityBlacklisted`
            Raised if the user or member is blacklisted and should_raise is True.
        """
        if user.id in self._global_blacklisted_users:
            if should_raise:
                raise EntityBlacklisted(user)
            return True

        if isinstance(user, discord.Member) and user.guild is not None:
            if user.id in self._guild_blacklisted_users[user.guild.id]:
                if should_raise:
                    raise EntityBlacklisted(user)
                return True
        return False

    async def add_channel(self, channel: discord.abc.GuildChannel, end_time: Optional[datetime] = None) -> bool:
        """|coro|

        Adds a channel to the blacklist.

        Parameters
        ----------
        channel: :class:`discord.abc.GuildChannel`
            The channel to add to the blacklist.
        end_time: Optional[:class:`datetime`]
            The time when the channel will be removed from the blacklist.

        Returns
        -------
        bool
            Whether the channel was added successfully or not.
        """
        # First we add the channel to the cache
        self._blacklisted_channels[channel.guild.id].add(channel.id)

        if end_time is not None:  # Then, if the block is temporary, we create a new timer

            # We first delete all existing timers
            await self.bot.pool.execute(
                """DELETE FROM timers
                       WHERE event = 'blacklist'
                       AND (extra->'kwargs'->'blacklist_type')::TEXT = 'channel'
                       AND (extra->'kwargs'->'entity_id')::BIGINT = $1
                       AND (extra->'kwargs'->'guild_id')::BIGINT = $2""",
                channel.id, channel.guild.id)

            # Then we make a new one
            await self.bot.create_timer(
                end_time,
                "blacklist",
                blacklist_type='channel',
                entity_id=channel.id,
                guild_id=channel.guild.id,
            )

            # Lastly we add the channel to the blacklist.
            return await self.try_query("""
                INSERT INTO blacklist (blacklist_type, entity_id, guild_id) VALUES ('channel', $1, $2)
                ON CONFLICT (blacklist_type, entity_id) DO UPDATE SET created_at = NOW()
            """, channel.id, channel.guild.id)

        else:  # If the block is not temporary, we just add the guild to the blacklist.
            query = "INSERT INTO blacklist (blacklist_type, entity_id, guild_id) VALUES ('channel', $1, $2)"
            return await self.try_query(query, channel.id, channel.guild.id)

    async def remove_channel(self, channel: discord.abc.GuildChannel) -> bool:
        """|coro|

        Removes a channel from the blacklist.

        Parameters
        ----------
        channel: :class:`discord.abc.GuildChannel`
            The channel to remove from the blacklist.

        Returns
        -------
        bool
            Whether the channel was removed successfully or not.
        """
        # First we remove the channel from the cache
        self._blacklisted_channels[channel.guild.id].discard(channel.id)

        # Then, we discard all existing timers
        await self.bot.pool.fetch(
            """DELETE FROM timers
                   WHERE event = 'blacklist'
                   AND (extra->'kwargs'->'blacklist_type')::TEXT = 'channel'
                   AND (extra->'kwargs'->'entity_id')::BIGINT = $1
                   AND (extra->'kwargs'->'guild_id')::BIGINT = $2""",
            channel.id, channel.guild.id)

        # Then we remove the channel from the blacklist.
        query = """DELETE FROM blacklist 
                       WHERE entity_id = $1 
                       AND guild_id = $2 
                       AND blacklist_type = 'channel' 
                   RETURNING *"""

        return not not (await self.bot.pool.fetch(query, channel.id, channel.guild.id))

    def check_channel(self, channel: discord.abc.GuildChannel, should_raise: bool = False) -> bool:
        """Checks if a channel is blacklisted.

        Parameters
        ----------
        channel: :class:`discord.abc.GuildChannel`
            The channel to check.
        should_raise: bool
            Whether to raise an error if the channel is blacklisted or not.

        Returns
        -------
        bool
            Whether the channel is blacklisted or not.

        Raises
        ------
        :class:`EntityBlacklisted`
            Raised if the channel is blacklisted and should_raise is True.
        """
        if not should_raise:
            return channel.id in self._blacklisted_channels[channel.guild.id]
        if channel.id in self._blacklisted_channels[channel.guild.id]:
            raise EntityBlacklisted(channel)
        return False

    async def add_guild(self, guild: discord.Guild, end_time: Optional[datetime] = None) -> bool:
        """|coro|

        Adds a guild to the blacklist.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild to add to the blacklist.
        end_time: Optional[:class:`datetime`]

        Returns
        -------
        bool
            Whether the guild was added successfully or not.
        """
        # First we add the guild to the cache
        self._blacklisted_guilds.add(guild.id)

        if end_time is not None:  # Then, if the block is temporary, we create a new timer
            await self.bot.pool.fetch(
                """DELETE FROM timers
                       WHERE event = 'blacklist'
                       AND (extra->'kwargs'->'blacklist_type')::TEXT = 'guild'
                       AND (extra->'kwargs'->'entity_id')::BIGINT = $1""",
                guild.id)

            # Then, we create a new timer.
            await self.bot.create_timer(
                end_time,
                "blacklist",
                blacklist_type='guild',
                entity_id=guild.id,
            )

            # Lastly we add the guild to the blacklist.
            return await self.try_query("""
                INSERT INTO blacklist (blacklist_type, entity_id) VALUES ('guild', $1)
                ON CONFLICT (blacklist_type, entity_id) DO UPDATE SET created_at = NOW()
            """, guild.id)

        else:  # If the block is not temporary, we just add the guild to the blacklist.
            query = "INSERT INTO blacklist (blacklist_type, entity_id) VALUES ('guild', $1)"
            return await self.try_query(query, guild.id)

    async def remove_guild(self, guild: discord.Guild) -> bool:
        """|coro|

        Removes a guild from the blacklist.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild to remove from the blacklist.

        Returns
        -------
        bool
            Whether the guild was removed successfully or not.
        """
        # First we remove the guild from the cache
        self._blacklisted_guilds.discard(guild.id)

        # Then, we discard all existing timers
        await self.bot.pool.fetch(
            """DELETE FROM timers
                   WHERE event = 'blacklist'
                   AND (extra->'kwargs'->'blacklist_type')::TEXT = 'guild'
                   AND (extra->'kwargs'->'entity_id')::BIGINT = $1""",
            guild.id)

        # Then we remove the guild from the blacklist
        query = """DELETE FROM blacklist 
                       WHERE entity_id = $1 
                       AND blacklist_type = 'guild' 
                   RETURNING *"""
        return not not (await self.bot.pool.fetch(query, guild.id))

    def check_guild(self, guild: discord.Guild, should_raise: bool = False) -> bool:
        """Checks if a guild is blacklisted.

        Parameters
        ----------
        guild: :class: `discord.Guild`
            The guild to check.
        should_raise: bool
            Whether to raise an error if the guild is blacklisted or not.

        Returns
        -------
        bool
            Whether the guild is blacklisted or not.

        Raises
        ------
        :class:`EntityBlacklisted`
            Raised if the guild is blacklisted and should_raise is True.
        """
        if not should_raise:
            return guild.id in self._blacklisted_guilds
        if guild.id in self._blacklisted_guilds:
            raise EntityBlacklisted(guild)
        return False

    async def try_query(self, query: str, *args: Any) -> bool:
        try:
            await self.bot.pool.execute(query, *args)
            return True
        except asyncpg.UniqueViolationError:
            return False

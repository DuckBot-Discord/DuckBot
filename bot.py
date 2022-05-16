from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import functools
import logging
import random
import re
import sys
import time
from collections import defaultdict
from json import dump, load
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    DefaultDict,
    Dict,
    Generator,
    Generic,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    Mapping,
)

import asyncpg
import cachetools
import discord
from discord import app_commands
from discord.ext import commands

from utils import (
    DuckBlacklistManager,
    DuckContext,
    DuckCog,
    DuckExceptionManager,
    TimerManager,
    col,
    constants,
    human_join,
    human_timedelta,
    IPCBase,
)
from utils.bases.errors import *

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    import datetime

    from aiohttp import ClientSession
    from asyncpg import Connection, Pool
    from asyncpg.transaction import Transaction

    from cogs.owner.eval import Eval

DBT = TypeVar("DBT", bound="DuckBot")
DCT = TypeVar("DCT", bound="DuckContext")
T = TypeVar("T")
P = ParamSpec("P")

log = logging.getLogger("DuckBot.main")

initial_extensions: Tuple[str, ...] = (
    # Helpers
    "utils.jishaku",
    "utils.bases.context",
    "utils.command_errors",
    "utils.interactions.command_errors",
    "utils.help",
    "utils.bases.ipc",
    # Cogs
    "cogs.guild_config",
    "cogs.meta",
    "cogs.moderation",
    "cogs.owner",
    "cogs.information",
    "cogs.tags",
)


class SyncResult(NamedTuple):
    synced: bool
    commands: List[app_commands.AppCommand]


def _wrap_extension(func: Callable[P, Awaitable[T]]) -> Callable[P, Coroutine[Any, Any, Optional[T]]]:
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> Optional[T]:
        fmt_args = 'on ext "{}"{}'.format(args[1], f" with kwargs {kwargs}" if kwargs else "")
        start = time.monotonic()

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            log.warning(f"Failed to load extension in {(time.monotonic() - start)*1000:.2f}ms {fmt_args}", exc_info=exc)
            raise

        fmt = f"{func.__name__} took {(time.monotonic() - start)*1000:.2f}ms {fmt_args}"
        log.info(fmt)

        return result

    return wrapped


class DbTempContextManager(Generic[DBT]):
    """A class to handle a short term pool connection.

    .. code-block:: python3

        async with DbTempContextManager(bot, 'postgresql://user:password@localhost/database') as pool:
            async with pool.acquire() as conn:
                await conn.execute('SELECT * FROM table')

    Attributes
    ----------
    bot: Type[:class:`DuckBot`]
        A class reference to DuckBot.
    uri: :class:`str`
        The URI to connect to the database with.
    """

    __slots__: Tuple[str, ...] = ("bot", "uri", "_pool")

    def __init__(self, bot: Type[DBT], uri: str) -> None:
        self.bot: Type[DBT] = bot
        self.uri: str = uri
        self._pool: Optional[asyncpg.Pool] = None

    async def __aenter__(self) -> asyncpg.Pool:
        self._pool = pool = await self.bot.setup_pool(uri=self.uri)
        return pool

    async def __aexit__(self, *args) -> None:
        if self._pool:
            await self._pool.close()


class DbContextManager(Generic[DBT]):
    """A simple context manager used to manage database connections.

    .. note::

        Please note this was created instead of using `contextlib.asynccontextmanager` because
        I plan to add additional functionality to this class in the future.

    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance.
    timeout: :class:`float`
        The timeout for acquiring a connection.
    """

    __slots__: Tuple[str, ...] = ("bot", "timeout", "_pool", "_conn", "_tr")

    def __init__(self, bot: DBT, *, timeout: float = 10.0) -> None:
        self.bot: DBT = bot
        self.timeout: float = timeout
        self._pool: asyncpg.Pool = bot.pool
        self._conn: Optional[Connection] = None
        self._tr: Optional[Transaction] = None

    async def acquire(self) -> Connection:
        return await self.__aenter__()

    async def release(self) -> None:
        return await self.__aexit__(None, None, None)

    async def __aenter__(self) -> Connection:
        self._conn = conn = await self._pool.acquire(timeout=self.timeout)
        self._tr = conn.transaction()
        await self._tr.start()
        return conn

    async def __aexit__(self, exc_type, exc, tb):
        if exc and self._tr:
            await self._tr.rollback()

        elif not exc and self._tr:
            await self._tr.commit()

        if self._conn is not None:
            await self._pool.release(self._conn)  # type: ignore


class DuckHelper(TimerManager):
    def __init__(self, *, bot: DuckBot) -> None:
        super().__init__(bot=bot)

    @staticmethod
    def chunker(item: Union[str, Sequence[T]], *, size: int = 2000) -> Generator[Union[str, Sequence[T]], None, None]:
        """Split a string into chunks of a given size.

        Parameters
        ----------
        item: :class:`str`
            The string to split.
        size: :class:`int`
            The size of each chunk. Defaults to 2000.
        """
        for i in range(0, len(item), size):
            yield item[i : i + size]

    def validate_locale(self, locale: str | discord.Locale | None, default: str = "en_us") -> str:
        """Validate a locale.

        Parameters
        ----------
        locale: :class:`str`
            The locale to validate.

        Returns
        -------
        :class:`bool`
            Whether or not the locale is valid.
        """
        locale = str(locale).lower().replace("-", "_")
        if locale not in self.bot.allowed_locales:
            locale = self.validate_locale(default)
        return locale

    async def translate(
        self,
        translation_id: int,
        /,
        *args: Any,
        locale: str | discord.Locale | None,
        db: asyncpg.Pool | Connection | None = None,
    ) -> str:
        """|coro|
        Handles translating a translation ID.

        Parameters
        ----------
        translation_id: :class:`int`
            The translation ID to translate.
        args: :class:`Any`
            The arguments to pass to the translation.
        locale: Optional[:class:`str` | :class:`~discord.Locale`]
            The locale to use for the translation.
        connection: Optional[:class:`~asyncpg.Connection` | :class:`~asyncpg.Pool`]
            The connection to use for the transaction.
        """
        connection = db or self.bot.pool
        locale = self.validate_locale(locale)
        translations = await connection.fetchrow("SELECT * FROM translations WHERE tr_id = $1", translation_id)
        if not translations:
            raise RuntimeError(f"Translation ID {translation_id} does not exist")

        translation = translations[locale] or translations["en_us"]
        return translation.format(*args)


class DuckBot(commands.AutoShardedBot, DuckHelper):
    if TYPE_CHECKING:
        user: discord.ClientUser
        _eval_cog: Eval
        command_prefix: Set[str]
        cogs: Mapping[str, DuckCog]

    def __init__(self, *, session: ClientSession, pool: Pool, **kwargs) -> None:
        intents = discord.Intents.all()
        intents.typing = False

        super().__init__(
            command_prefix={
                "dbb.",
            },
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=intents,
            activity=discord.Streaming(name="db.help", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            strip_after_prefix=True,
            chunk_guilds_at_startup=False,
            max_messages=4000,
        )
        self.pool: Pool = pool
        self.session: ClientSession = session
        self._context_cls: Type[commands.Context] = commands.Context
        self.prefix_cache: DefaultDict[int, Set[str]] = defaultdict(set)
        self.messages: cachetools.TTLCache[str, discord.Message] = cachetools.TTLCache(
            maxsize=1000, ttl=300.0
        )  # {repr(ctx): message(from ctx.send) }
        self.error_webhook_url: Optional[str] = kwargs.get("error_wh")
        self._start_time: Optional[datetime.datetime] = None
        self.listener_connection: Optional[asyncpg.Connection] = None  # type: ignore
        self.allowed_locales: Set[str] = {"en_us", "es_es", "it"}

        self.blacklist: DuckBlacklistManager = DuckBlacklistManager(self)
        self.exceptions: DuckExceptionManager = DuckExceptionManager(self)
        self.thread_pool: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

        self.constants = constants
        self.tree.error(self.on_tree_error)

        self.views: Set[discord.ui.View] = set()
        self._auto_spam_count: DefaultDict[int, int] = defaultdict(int)
        self.global_mapping = commands.CooldownMapping.from_cooldown(10, 12, commands.BucketType.user)
        self.ipc: Optional[IPCBase] = None

    async def setup_hook(self) -> None:
        failed = False
        for extension in initial_extensions:
            try:
                result = await self.load_extension(extension)
            except Exception as e:
                failed = True
                await self.exceptions.add_error(error=e)
            else:
                failed = failed or not result

        self.tree.copy_global_to(guild=discord.Object(id=774561547930304536))

        await self.populate_cache()
        await self.create_db_listeners()

        super(DuckHelper, self).__init__(bot=self)

        async def sync_with_logging():
            log.info(f"%sSyncing commands to discord...", col(6))
            guild = discord.Object(id=774561547930304536)
            try:
                result = await self.try_syncing(guild=guild)
            except Exception as e:
                log.error(
                    "%sFailed to sync commands with guild %s",
                    col(6),
                    guild.id,
                    exc_info=e,
                )
            else:
                if result.synced is True:
                    log.info(
                        "%sSuccessfully synced %s commands to guild %s",
                        col(6),
                        len(result.commands),
                        guild.id,
                    )
                else:
                    log.info("%sCommands for guild %s were already synced", col(6), guild.id)

        if not failed:
            self.create_task(sync_with_logging())
        else:
            log.info("Not syncing commands. One or more cogs failed to load.")

    @classmethod
    def temporary_pool(cls: Type[DBT], *, uri: str) -> DbTempContextManager[DBT]:
        """:class:`DbTempContextManager` A context manager that creates a
        temporary connection pool.

        Parameters
        ----------
        uri: :class:`str`
            The URI to connect to the database with.
        """
        return DbTempContextManager(cls, uri)

    @classmethod
    async def setup_pool(cls: Type[DBT], *, uri: str, **kwargs) -> asyncpg.Pool:
        """:meth: `asyncpg.create_pool` with some extra functionality.

        Parameters
        ----------
        uri: :class:`str`
            The Postgres connection URI.
        **kwargs:
            Extra keyword arguments to pass to :meth:`asyncpg.create_pool`.
        """  # copy_doc for create_pool maybe?

        def _encode_jsonb(value):
            # noinspection PyProtectedMember
            return discord.utils._to_json(value)

        def _decode_jsonb(value):
            # noinspection PyProtectedMember
            return discord.utils._from_json(value)

        old_init = kwargs.pop("init", None)

        async def init(con):
            await con.set_type_codec(
                "jsonb",
                schema="pg_catalog",
                encoder=_encode_jsonb,
                decoder=_decode_jsonb,
                format="text",
            )
            if old_init is not None:
                await old_init(con)

        pool = await asyncpg.create_pool(uri, init=init, **kwargs)
        log.info(f"{col(2)}Successfully created connection pool.")
        assert pool is not None, "Pool is None"
        return pool

    async def populate_cache(self) -> None:
        """|coro|

        Populates all cache that comes from the database. Please note if commands are
        processed before this data is complete, some guilds may not have custom prefixes.
        """
        async with self.safe_connection() as conn:
            data = await conn.fetch("SELECT guild_id, prefixes FROM guilds")
            for guild_id, prefixes in data:
                self.prefix_cache[guild_id] = set(prefixes)
            await self.blacklist.build_cache(conn)

    async def create_db_listeners(self) -> None:
        """|coro|

        Registers listeners for database events.
        """
        self.listener_connection: asyncpg.Connection = await self.pool.acquire()  # type: ignore

        async def _delete_prefixes_event(conn, pid, channel, payload):
            payload = discord.utils._from_json(payload)  # noqa
            with contextlib.suppress(Exception):
                del self.prefix_cache[payload["guild_id"]]

        async def _create_or_update_event(conn, pid, channel, payload):
            payload = discord.utils._from_json(payload)  # noqa
            self.prefix_cache[payload["guild_id"]] = set(payload["prefixes"])

        await self.listener_connection.add_listener("delete_prefixes", _delete_prefixes_event)
        await self.listener_connection.add_listener("update_prefixes", _create_or_update_event)

    async def dump_translations(self, filename: str) -> None:
        log.info("%sDumping translations to %s", col(5), f"{filename!r}")
        translations = await self.pool.fetch("SELECT * FROM translations ORDER BY tr_id")
        log.info(
            "%sDumping %s translations to locales %s%s",
            col(5),
            len(translations),
            col(3),
            human_join(
                list(self.allowed_locales),
                final=f"{col(5)}and{col(3)}",
                delim=f"{col(5)}, {col(3)}",
            ),
        )
        payload: Dict[str, Any] = dict(
            locales=list(self.allowed_locales),
            last_updated=discord.utils.utcnow().isoformat(),
        )
        for translation in translations:
            data = dict(translation)
            del data["tr_id"]
            payload[translation["tr_id"]] = data
        with open(filename, "w+") as f:
            dump(payload, f, indent=4)

    async def load_translations(self, filename: str) -> None:
        async with self.safe_connection() as conn:
            log.info("%sLoading translations from %s", col(5), f"{filename!r}")
            with open(filename, "r") as f:
                payload = load(f)
            log.info(
                "%sLoading %s translations from locales %s%s",
                col(5),
                len(payload) - 2,
                col(3),
                human_join(
                    payload["locales"],
                    final=f"{col(5)}and{col(3)}",
                    delim=f"{col(5)}, {col(3)}",
                ),
            )
            for tr_id, data in payload.items():
                if not tr_id.isdigit():
                    continue
                log.debug("%sLoading translation %s", col(3), tr_id)
                for locale, translation in data.items():
                    if locale not in self.allowed_locales and locale != "note":
                        raise RuntimeError(f"Invalid locale {locale!r}")
                    await conn.execute(
                        f"""
                        INSERT INTO translations (tr_id, {locale}) VALUES ($1, $2) 
                        ON CONFLICT (tr_id) DO UPDATE SET {locale} = $2
                    """,
                        int(tr_id),
                        translation,
                    )
            log.info("%sSuccessfully loaded %s translations", col(5), len(payload) - 2)

    @property
    def start_time(self) -> datetime.datetime:
        """:class:`datetime.datetime`: The time the bot was started."""
        result = self._start_time
        if not result:
            raise DuckBotNotStarted("The bot has not hit on-ready yet.")

        return result

    @discord.utils.cached_property
    def mention_regex(self) -> re.Pattern:
        """:class:`re.Pattern`: A regex pattern that matches the bot's mention.

        Raises
        ------
        AttributeError
            The bot has not hit on-ready yet.
        """
        return re.compile(rf"<@!?{self.user.id}>")

    @discord.utils.cached_property
    def invite_url(self) -> str:
        """:class:`str`: The invite URL for the bot.

        Raises
        ------
        DuckBotNotStarted
            The bot has not hit on-ready yet.
        """
        if not self.is_ready():
            raise DuckBotNotStarted("The bot has not hit on-ready yet.")

        return discord.utils.oauth_url(
            self.user.id,
            permissions=discord.Permissions(8),
            scopes=("bot", "applications.commands"),
        )

    @discord.utils.cached_property
    def uptime_timestamp(self) -> str:
        """:class:`str`: The uptime of the bot in a human-readable Discord timestamp format.

        Raises
        ------
        DuckBotNotStarted
            The bot has not hit on-ready yet.
        """
        if not self.is_ready():
            raise DuckBotNotStarted("The bot has not hit on-ready yet.")

        return discord.utils.format_dt(self.start_time)

    @discord.utils.cached_property
    def color(self) -> discord.Colour:
        """:class:`~discord.Color`: The vanity color of the bot."""
        return discord.Colour(0xF4D58C)

    @discord.utils.cached_property
    def colour(self) -> discord.Colour:
        """:class:`~discord.Colour`: The vanity colour of the bot."""
        return discord.Colour(0xF4D58C)

    @property
    def human_uptime(self) -> str:
        """:class:`str`: The uptime of the bot in a human-readable format.

        Raises
        ------
        DuckBotNotStarted
            The bot has not hit on-ready yet.
        """
        return human_timedelta(self.start_time)

    @property
    def done_emoji(self) -> discord.PartialEmoji:
        """:class:`~discord.PartialEmoji`: The emoji used to denote a command has finished processing."""
        return discord.PartialEmoji.from_str(random.choice(self.constants.DONE))

    @_wrap_extension
    @discord.utils.copy_doc(commands.Bot.load_extension)
    async def load_extension(self, name: str, *, package: Optional[str] = None) -> bool:
        try:
            await super().load_extension(name, package=package)
            return True
        except:
            raise

    @_wrap_extension
    @discord.utils.copy_doc(commands.Bot.unload_extension)
    async def unload_extension(self, name: str, *, package: Optional[str] = None) -> bool:
        try:
            await super().unload_extension(name, package=package)
            return True
        except:
            raise

    @_wrap_extension
    @discord.utils.copy_doc(commands.Bot.reload_extension)
    async def reload_extension(self, name: str, *, package: Optional[str] = None) -> bool:
        try:
            await super().reload_extension(name, package=package)
            return True
        except:
            raise

    def safe_connection(self, *, timeout: float = 10.0) -> DbContextManager:
        """A context manager that will acquire a connection from the bot's pool.

        This will neatly manage the connection and release it back to the pool when the context is exited.

        .. code-block:: python3

            async with bot.safe_connection(timeout=10) as conn:
                await conn.execute('SELECT * FROM table')
        """
        return DbContextManager(self, timeout=timeout)

    async def get_prefix(self, message: discord.Message, raw: bool = False) -> List[str]:
        """|coro|

        Returns the prefixes for the given message.
        if raw is True, returns the prefixes without the bots mention.

        Parameters
        ----------
        message: :class:`~discord.Message`
            The message to get the prefix of.
        raw: :class:`bool`
            Whether to return the raw prefixes or not.
        """
        meth = commands.when_mentioned_or if raw is False else lambda *pres: lambda _, __: list(pres)

        cached_prefixes = self.prefix_cache.get((message.guild and message.guild.id), None)  # type: ignore
        if cached_prefixes is not None:
            base = set(cached_prefixes)
        else:
            base = self.command_prefix

        # Note you have a type error here because of `self.command_prefix`.
        # This is because command_prefix is type hinted internally as both an iterable
        # of strings and a coroutine. The coroutine aspect is affecting L-430. I can fix it,
        # but it's not the neatest thing, it's up to you :P
        return meth(*base)(self, message)

    async def get_context(self, message: discord.Message, *, cls: Type[DCT] = None) -> Union[DuckContext, commands.Context]:
        """|coro|

        Used to get the invocation context from the message.

        Parameters
        ----------
        message: :class:`~discord.Message`
            The message to get the prefix of.
        cls: Type[:class:`DuckContext`]
            The class to use for the context.
        """
        new_cls = cls or self._context_cls
        return await super().get_context(message, cls=new_cls)

    async def on_connect(self):
        """|coro|

        Called when the bot connects to the gateway.
        """
        log.info(f"{col(2)}Logged in as {self.user}! ({self.user.id})")

    async def on_shard_connect(self, shard_id: int):
        """|coro|

        Called when one of the shards connects to the gateway.
        """
        log.info(f"{col(2)}Shard ID {shard_id} connected!")

    async def on_disconnect(self):
        """|coro|

        Called when the client has disconnected from Discord,
        or a connection attempt to Discord has failed.
        """
        log.info(f"{col(2)}Unexpectedly lost conection to Discord!")

    async def on_shard_disconnect(self, shard_id: int):
        """|coro|

        Called when the a shard has disconnected from Discord,
        or a connection attempt to Discord has failed.
        """
        log.info(f"{col(2)}Shard ID {shard_id} unexpectedly lost conection to Discord!")

    async def on_ready(self):
        """|coro|

        Called when the internal cache of the bot is ready, and the bot is
        connected to the gateway.
        """
        log.info(f"{col(2)}All guilds are chunked and ready to go!")
        if not self._start_time:
            self._start_time = discord.utils.utcnow()

    async def on_shard_ready(self, shard_id: int):
        """|coro|

        Called when one of the bot's shards is ready.
        """
        log.info(f"{col(2)}Shard ID {shard_id} is now ready!")

    async def on_resumed(self):
        """|coro|

        Called when the gateway resumed it's connection to discord.
        """
        log.info(f"{col(2)}Resumed connection to the gateway.")

    async def on_shard_resumed(self, shard_id: int):
        """|coro|

        Called when one of the bot's shards resumed it's connection to discord.
        """
        log.info(f"{col(2)}Shard ID {shard_id} resumed connection to the gateway.")

    async def on_message(self, message: discord.Message) -> Optional[discord.Message]:
        """|coro|

        Called every time a message is received by the bot. Used to check if the message
        has mentioned the bot, and if it has return a simple response.

        Returns
        -------
        Optional[:class:`~discord.Message`]
            The message that was created for replying to the user.
        """
        if self.mention_regex.fullmatch(message.content):
            prefixes = await self.get_prefix(message, raw=True)
            return await message.reply(
                f"My prefixes here are `{'`, `'.join(prefixes[0:10])}`\n"
                f"For a list of commands do`{prefixes[0]}help` 💞"[0:2000]
            )

        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """|coro|

        Called every time a message is edited.

        Parameters
        ----------
        before: :class:`~discord.Message`
            The message before it was edited.
        after: :class:`~discord.Message`
            The message after it was edited.
        """
        await self.process_commands(after)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """|coro|

        Called every time a message is deleted.

        Parameters
        ----------
        message: :class:`~discord.Message`
            The message that was deleted.
        """
        _repr = f'<utils.DuckContext bound to message ({payload.channel_id}-{payload.message_id})>'
        if _repr in self.messages:
            message = self.messages[_repr]
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            del self.messages[_repr]

    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """|coro|

        Called when an error is raised, and it's not from a command.

        Parameters
        ----------
        event: :class:`str`
            The name of the event that raised the exception.
        args: :class:`Any`
            The positional arguments for the event that raised the exception.
        kwargs: :class:`Any`
            The keyword arguments for the event that raised the exception.
        """
        _, error, _ = sys.exc_info()
        if not error:
            raise

        await self.exceptions.add_error(error=error)  # type: ignore
        return await super().on_error(event, *args, **kwargs)

    async def on_tree_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        command = interaction.command
        if command and getattr(command, "on_error", None):
            return

        if self.extra_events.get("on_app_command_error"):
            return interaction.client.dispatch("app_command_error", interaction, command, error)

        raise error from None

    def wrap(self, func: Callable[..., T], *args, **kwargs) -> Awaitable[T]:
        """Wrap a blocking function to be not blocking.

        Parameters
        ----------
        func: Callable[..., :class:`T`]
            The function to wrap.
        *args
            The arguments to pass to the function.
        **kwargs
            The keyword arguments to pass to the function.

        Returns
        -------
        Awaitable[T]
            The wrapped function you can await.
        """
        return self.loop.run_in_executor(self.thread_pool, functools.partial(func, *args, **kwargs))

    def create_task(self, coro: Coroutine[T, Any, Any], *, name: Optional[str] = None) -> asyncio.Task[T]:
        """Create a task from a coroutine object.

        Parameters
        ----------
        coro: :class:`~asyncio.Coroutine`
            The coroutine to create the task from.
        name: Optional[:class:`str`]
            The name of the task.

        Returns
        -------
        :class:`~asyncio.Task`
            The task that was created.
        """
        return self.loop.create_task(coro, name=name)

    # This is overridden, so we don't get so many annoying type errors when passing
    # a Member into is_owner  ## Nah chai it's your shitty type checker smh!
    @discord.utils.copy_doc(commands.Bot.is_owner)
    async def is_owner(self, user: Union[discord.User, discord.Member]) -> bool:
        return await super().is_owner(user)

    async def start(self, token: str, *, reconnect: bool = True, verbose: bool = True) -> None:
        """|coro|

        Starts the bot.

        Parameters
        ----------
        token: :class:`str`
            The authentication token. Do not prefix this token with
            anything as the library will do it for you.
        reconnect: :class:`bool`
            If we should attempt reconnecting, either due to internet
            failure or a specific failure on Discord's part. Certain
            disconnects that lead to bad state will not be handled (such as
            invalid sharding payloads or bad tokens).
        verbose: :class:`bool`
            If we should log debug events. Set this to ``False`` if you want
            to reduce the verbosity of the bot when logging mode is set to
            DEBUG. Defaults to ``True``.

        """
        if verbose is False:
            _gw_log = logging.getLogger("discord.gateway")
            _gw_log.disabled = True

            _cl_log = logging.getLogger("discord.client")
            _cl_log.disabled = True

            _ht_log = logging.getLogger("discord.http")
            _ht_log.disabled = True

            _ds_log = logging.getLogger("discord.state")
            _ds_log.disabled = True

        await super().start(token, reconnect=reconnect)

    async def close(self) -> None:
        """|coro|

        Closes the websocket connection and stops the event loop.

        """
        try:
            try:
                await self.cleanup_views()
            except Exception as e:
                log.error("Could not wait for view cleanups", exc_info=e)
            try:
                if self.listener_connection:
                    log.info("Closing listener connection...")
                    await self.listener_connection.close()
            except Exception as e:
                log.error(f"Failed to close listener connection", exc_info=e)
        finally:
            await super().close()

    async def cleanup_views(self, *, timeout: float = 5.0) -> None:
        """Cleans up the views of the bot."""
        future = await asyncio.gather(*[v.on_timeout() for v in self.views], return_exceptions=True)
        for item in future:
            if isinstance(item, Exception):
                log.debug("A view failed to clean up", exc_info=item)

    @staticmethod
    async def get_or_fetch_member(guild: discord.Guild, user: Union[discord.User, int]) -> Optional[discord.Member]:
        """|coro|

        Used to get a member from a guild. If the member was not found, the function
        will return nothing.

        Parameters
        ----------
        guild: :class:`~discord.Guild`
            The guild to get the member from.
        user: Union[:class:`~discord.User`, :class:`int`]
            The user to get the member from.

        Returns
        -------
        Optional[:class:`~discord.Member`]
            The member that was requested.
        """
        uid = user.id if isinstance(user, discord.User) else user
        try:
            return guild.get_member(uid) or await guild.fetch_member(uid)
        except discord.HTTPException:
            return None

    async def get_or_fetch_user(self, user_id: int) -> Optional[discord.User]:
        """|coro|

        Used to get a member from a guild. If the member was not found, the function
        will return nothing.

        Parameters
        ----------
        user_id: :class:`int`
            The user ID to fetch

        Returns
        -------
        Optional[:class:`~discord.User`]
            The member that was requested.
        """
        try:
            return self.get_user(user_id) or await self.fetch_user(user_id)
        except discord.HTTPException:
            return None

    async def on_command(self, ctx: DuckContext):
        """|coro|

        Called when a command is invoked.
        Handles automatic blacklisting of users that are abusing the bot.

        Parameters
        ----------
        ctx: DuckContext
            The context of the command.
        """
        assert ctx.command is not None

        try:
            bucket = self.global_mapping.get_bucket(ctx.message)
            current = ctx.message.created_at.timestamp()
            retry_after = bucket.update_rate_limit(current)
            author_id = ctx.author.id
            if retry_after and not await self.is_owner(ctx.author):
                self._auto_spam_count[author_id] += 1
                if self._auto_spam_count[author_id] >= 5:
                    await self._auto_blacklist_add(ctx.author)
                    del self._auto_spam_count[author_id]
                    await self._log_rl_excess(ctx, ctx.message, retry_after, auto_block=True)
                else:
                    await self._log_rl_excess(ctx, ctx.message, retry_after)
                return
            else:
                self._auto_spam_count.pop(author_id, None)
        finally:
            await self.pool.execute(
                "INSERT INTO commands (guild_id, user_id, command, timestamp) VALUES ($1, $2, $3, $4)",
                (ctx.guild and ctx.guild.id),
                ctx.author.id,
                ctx.command.qualified_name,
                ctx.message.created_at,
            )

    async def _log_rl_excess(self, ctx, message, retry_after, *, auto_block=False):
        """|coro|

        Logs a rate limit excess

        Parameters
        ----------
        ctx: DuckContext
            The context of the command.
        message: discord.Message
            The message that triggered the rate limit.
        retry_after: float
            The amount of time the user had to wait.
        auto_block: bool
            Whether the user was automatically blocked.
        """
        guild_name = getattr(ctx.guild, "name", "No Guild (DMs)")
        guild_id = getattr(ctx.guild, "id", None)
        fmt = "User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs"
        logging.warning(fmt, message.author, message.author.id, guild_name, guild_id, retry_after)
        if not auto_block:
            return

        await self.bot.wait_until_ready()
        embed = discord.Embed(title="Auto-blocked Member", colour=0xDDA453)
        embed.add_field(
            name="Member",
            value=f"{message.author} (ID: {message.author.id})",
            inline=False,
        )
        embed.add_field(name="Guild Info", value=f"{guild_name} (ID: {guild_id})", inline=False)
        embed.add_field(
            name="Channel Info",
            value=f"{message.channel} (ID: {message.channel.id}",
            inline=False,
        )
        embed.timestamp = discord.utils.utcnow()
        channel: discord.abc.Messageable = self.bot.get_channel(904797860841812050)  # type: ignore

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass
        except AttributeError as e:
            await self.exceptions.add_error(error=e)

    async def _auto_blacklist_add(self, user: Union[discord.User, discord.Member]):
        """|coro|

        Adds a user to the auto-blacklist.

        Parameters
        ----------
        user: :class:`discord.User`
            The user to add to the blacklist.
        """

        query = """
            INSERT INTO commands (user_id, command) VALUES ($1, $2)
            RETURNING (SELECT COUNT(*) FROM commands WHERE user_id = $1 AND command = $2)
        """
        amount = await self.pool.fetchval(query, user.id, f"AUTO-BOT-BAN")
        if amount >= 5:
            await self.blacklist.add_user(
                user,
                end_time=discord.utils.utcnow() + datetime.timedelta(minutes=1 * amount),
            )
        else:
            await self.blacklist.add_user(user)

    async def try_syncing(self, *, guild: discord.abc.Snowflake | None = None) -> SyncResult:
        """|coro|

        Tries to sync the command tree.

        Parameters
        ----------
        guild: discord.abc.Snowflake | None
            The guild to sync the command tree for.
        """
        # safeguard. Need the app id.
        await self.wait_until_ready()

        guild_id = guild.id if guild else 0
        all_cmds = self.bot.tree._get_all_commands(guild=guild)  # noqa F401  # private method kekw.
        payloads = [(guild_id, cmd.to_dict()) for cmd in all_cmds]

        databased = await self.pool.fetch("SELECT payload FROM auto_sync WHERE guild_id = $1", guild_id)
        saved_payloads = [d["payload"] for d in databased]

        not_synced = [p for _, p in payloads if p not in saved_payloads] + [
            p for p in saved_payloads if p not in [p for _, p in payloads]
        ]

        if not_synced:
            await self.pool.execute("DELETE FROM auto_sync WHERE guild_id = $1", guild_id)
            await self.pool.executemany("INSERT INTO auto_sync (guild_id, payload) VALUES ($1, $2)", payloads)

            synced = await self.bot.tree.sync(guild=guild)
            return SyncResult(commands=synced, synced=True)

        else:
            return SyncResult(commands=[], synced=False)

from __future__ import annotations

import re
import logging
import discord
import asyncpg
import functools
import asyncio
import concurrent.futures
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    TypeVar,
    Type,
    Generic,
    Tuple,
    Callable,
    Awaitable,
    Coroutine,
    Any
)

from discord.ext import commands
from collections import defaultdict

from utils.context import DuckContext
from utils.helpers import col
from utils.time import human_timedelta
from utils.errors import *

if TYPE_CHECKING:
    from asyncpg import Pool
    from aiohttp import ClientSession
    
DBT = TypeVar('DBT', bound='DuckBot')
DCT = TypeVar('DCT', bound='DuckContext')
T = TypeVar('T')


fmt = f'{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)

log = logging.getLogger('DuckBot.main')

initial_extensions: Tuple[str, ...] = (
    '',
)

class DbTempContextManager(Generic[DBT]):
    __slots__: Tuple[str, ...] = (
        'bot',
        'uri',
        '_pool'
    )
    
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
    
    __slots__: Tuple[str, ...] = (
        'bot',
        'timeout',
        '_pool',
        '_conn'
    )
    
    def __init__(self, bot: DBT, *, timeout: float = 10.0) -> None:
        self.bot: DBT = bot
        self.timeout: float = timeout
        self._pool: asyncpg.Pool = bot.pool
        self._conn: Optional[asyncpg.Connection] = None
    
    async def __aenter__(self) -> asyncpg.Connection:
        self._conn = conn = await self._pool.acquire(timeout=self.timeout)
        return conn
    
    async def __aexit__(self, *args):
        if self._conn:
            await self._pool.release(self._conn)


class DuckBot(commands.Bot):
    if TYPE_CHECKING:
        # We do this to make sure we dont get annoying 
        # type checker errors. Most of the time user isnt going to be 
        # None, so this is just a convenience thing.
        user: discord.ClientUser
    
    def __init__(self, *, session: ClientSession, pool: Pool) -> None:
        intents = discord.Intents.all()
        intents.typing = False  # noqa
        
        super().__init__(
            command_prefix={'dbb.',},
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=intents,
            activity=discord.Streaming(name="db.help", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            strip_after_prefix=True,
            chunk_guilds_at_startup=False
        )
        self.prefix_cache = defaultdict(set)
        self.session: ClientSession = session
        self.pool: Pool = pool
        self.thread_pool: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
        
    @classmethod
    def temporary_pool(cls: Type[DBT], *, uri: str) -> DbTempContextManager[DBT]:
        return DbTempContextManager(cls, uri)
        
    @classmethod
    async def setup_pool(cls: Type[DBT], *, uri: str, **kwargs) -> asyncpg.Pool: 
        def _encode_jsonb(value):
            return discord.utils._to_json(value)

        def _decode_jsonb(value):
            return discord.utils._from_json(value)
        
        old_init = kwargs.pop('init', None)
        
        async def init(con):
            await con.set_type_codec('jsonb', schema='pg_catalog', encoder=_encode_jsonb, decoder=_decode_jsonb, format='text')
            if old_init is not None:
                await old_init(con)
                
        pool = await asyncpg.create_pool(uri, init=init, **kwargs)
        return pool
        
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
            raise DuckBotNotStarted('The bot has not hit on-ready yet.')
        
        return discord.utils.oauth_url(self.user.id, permissions=discord.Permissions(8), scopes=('bot', 'applications.commands'))
    
    @discord.utils.cached_property
    def timestamp_uptime(self) -> str:
        """:class:`str`: The uptime of the bot in a human readable Discord timestamp format.
        
        Raises
        ------
        DuckBotNotStarted
            The bot has not hit on-ready yet.
        """
        if not self.is_ready():
            raise DuckBotNotStarted('The bot has not hit on-ready yet.')
        
        return discord.utils.format_dt(self.start_time)
    
    @property
    def human_uptime(self) -> str:
        """:class:`str`: The uptime of the bot in a human readable format.
        
        Raises
        ------
        DuckBotNotStarted
            The bot has not hit on-ready yet.
        """
        if not self.is_ready():
            raise DuckBotNotStarted('The bot has not hit on-ready yet.')
        
        return human_timedelta(self.start_time)
    
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

        if message.guild:
            if not (prefixes := self.prefix_cache.get(message.guild.id)):
                for prefix in self.command_prefix:
                    self.prefix_cache[message.guild.id].add(prefix)
                prefixes = self.command_prefix
        else:
            prefixes = self.command_prefix

        return meth(*prefixes)(self, message)

    async def get_context(self, message: discord.Message, *, cls: Type[DCT] = DuckContext) -> DuckContext:
        """|coro|
        
        Used to get the invocation context from the message.
        
        Parameters
        ----------
        message: :class:`~discord.Message`
            The message to get the prefix of.
        cls: Type[:class:`DuckContext`]
            The class to use for the context.
        """
        return await super().get_context(message, cls=cls)

    async def on_connect(self):
        """|coro|
        
        Called when the bot connects to the gateway. Used to log to console
        some basic information about the bot.
        """
        log.info(f'{col(2)}Logged in as {self.user}! ({self.user.id})')

    async def on_ready(self):
        """|coro|
        
        Called when the internal cache of the bot is ready, and the bot is
        connected to the gateway.
        """
        log.info(f'{col(2)}All guilds are chunked and ready to go!')
        self.start_time = discord.utils.utcnow()

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
                f"For a list of commands do`{prefixes[0]}help` 💞"[0:2000])
            
        await self.process_commands(message)

    def wrap(self, func: Callable[..., T], *args, **kwargs) -> Awaitable[T]:
        """Wrap a blocking function to be not blocking.
        
        Parameters
        ----------
        Callable
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

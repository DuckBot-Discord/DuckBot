from __future__ import annotations

import re
import logging
import discord
import asyncpg
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    TypeVar,
    Type,
    Generic
)
from discord.ext import commands
from collections import defaultdict

from cogs.utils.context import DuckContext
from cogs.utils.helpers import col

if TYPE_CHECKING:
    from asyncpg import Pool
    from aiohttp import ClientSession

DBT = TypeVar('DBT', bound='DuckBot')
DCT = TypeVar('DCT', bound='DuckContext')


fmt = f'{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)

log = logging.getLogger('DuckBot.main')


class DbTempContextManager(Generic[DBT]):
    def __init__(self, chai: Type[DBT], uri: str) -> None:
        self.bot: Type[DBT] = chai
        self.uri: str = uri
        self._pool: Optional[asyncpg.Pool] = None
    
    async def __aenter__(self) -> asyncpg.Pool:
        self._pool = pool = await self.bot.setup_pool(uri=self.uri)
        return pool
    
    async def __aexit__(self, *args) -> None:
        if self._pool:
            await self._pool.close()

class DuckBot(commands.Bot):
    def __init__(self, *, session: ClientSession, pool: Pool) -> None:
        intents = discord.Intents.all()
        intents.typing = False  # noqa
        
        super().__init__(
            command_prefix={'dbb.', 'Dbb.', 'DBB.'},
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=intents
        )
        self.prefix_cache = defaultdict(set)
        self.session: ClientSession = session
        self.pool: Pool = pool
        
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
            prefixes = self.prefix_cache.get(message.guild.id) or self.command_prefix
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

    async def on_message(self, message: discord.Message) -> Optional[discord.Message]:
        """|coro|
        
        Called every time a message is received by the bot. Used to check if the message
        has mentioned the bot, and if it has return a simple response.
        
        Returns
        -------
        Optional[:class:`~discord.Message`]
            The message that was created for replying to the user.
        """
        if self.mention_regex.fullmatch(rf"<@!?{self.user.id}>", message.content):
            prefixes = await self.get_prefix(message, raw=True)
            return await message.reply(
                f"My prefixes here are `{'`, `'.join(prefixes[0:10])}`\n"
                f"For a list of commands do`{prefixes[0]}help` 💞"[0:2000])
            
        await self.process_commands(message)

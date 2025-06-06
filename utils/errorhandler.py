from __future__ import annotations

import asyncio
import datetime
import os
import traceback
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import Tuple, Optional, Dict, List, Generator, Any, TYPE_CHECKING, Type

import discord

from utils.bases.context import DuckContext
from utils.bases.errors import DuckBotException, SilentCommandError, log
from utils.types.exception import DuckTraceback, _DuckTracebackOptional

if TYPE_CHECKING:
    from bot import DuckBot


__all__: Tuple[str, ...] = ('DuckExceptionManager', 'HandleHTTPException')


class DuckExceptionManager:
    """A simple exception handler that sends all exceptions to a error
    Webhook and then logs them to the console.

    This class handles cooldowns with a simple lock, so you don't have to worry about
    rate limiting your webhook and getting banned :).

    .. note::

        If some code is raising MANY errors VERY fast and you're not there to fix it,
        this will take care of things for you.

    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance.
    cooldown: :class:`datetime.timedelta`
        The cooldown between sending errors. This defaults to 5 seconds.
    errors: Dict[str, Dict[str, Any]]
        A mapping of tracebacks to their error information.
    code_blocker: :class:`str`
        The code blocker used to format Discord codeblocks.
    error_webhook: :class:`discord.Webhook`
        The error webhook used to send errors.
    """

    __slots__: Tuple[str, ...] = ('bot', 'cooldown', '_lock', '_most_recent', 'errors', 'code_blocker', 'error_webhook')

    def __init__(self, bot: DuckBot, *, cooldown: datetime.timedelta = datetime.timedelta(seconds=5)) -> None:
        if not bot.error_webhook_url:
            raise DuckBotException('No error webhook set in .env!')

        self.bot: DuckBot = bot
        self.cooldown: datetime.timedelta = cooldown

        self._lock: asyncio.Lock = asyncio.Lock()
        self._most_recent: Optional[datetime.datetime] = None

        self.errors: Dict[str, List[DuckTraceback]] = {}
        self.code_blocker: str = '```py\n{}```'
        self.error_webhook: discord.Webhook = discord.Webhook.from_url(
            bot.error_webhook_url, session=bot.session, bot_token=bot.http.token
        )

    def _yield_code_chunks(self, iterable: str, *, chunksize: int = 2000) -> Generator[str, None, None]:
        cbs = len(self.code_blocker) - 2  # code blocker size

        for i in range(0, len(iterable), chunksize - cbs):
            yield self.code_blocker.format(iterable[i : i + chunksize - cbs])

    async def release_error(self, traceback: str, packet: DuckTraceback) -> None:
        """Releases an error to the webhook and logs it to the console. It is not recommended
        to call this yourself, call :meth:`add_error` instead.

        Parameters
        ----------
        traceback: :class:`str`
            The traceback of the error.
        packet: :class:`dict`
            The additional information about the error.
        """
        log.error('Releasing error to log', exc_info=None)

        if self.error_webhook.is_partial():
            self.error_webhook = await self.error_webhook.fetch()

        fmt = {
            'time': discord.utils.format_dt(packet['time']),
        }
        if author := packet.get('author'):
            fmt['author'] = f'<@{author}>'

        # This is a bit of a hack,  but I do it here so guild_id
        # can be optional, and I wont get type errors.
        guild_id = packet.get('guild')
        guild = self.bot._connection._get_guild(guild_id)
        if guild:
            fmt['guild'] = f'{guild.name} ({guild.id})'
        else:
            log.warning('Ignoring error packet with unknown guild id %s', guild_id)

        if guild:
            channel_id = packet.get('channel')
            if channel_id and (channel := guild.get_channel(channel_id)):
                fmt['channel'] = f'{channel.name} - {channel.mention} - ({channel.id})'

            # Let's try and upgrade the author
            author_id = packet.get('author')
            if author_id:
                author = guild.get_member(author_id) or self.bot.get_user(author_id)
                if author:
                    fmt['author'] = f'{str(author)} - {author.mention} ({author.id})'

        if not fmt.get('author') and (author_id := packet.get('author')):
            fmt['author'] = f'<Unknown User> - <@{author_id}> ({author_id})'

        if command := packet.get('command'):
            fmt['command'] = command.qualified_name
            display = f'in command "{command.qualified_name}"'
        elif display := packet.get('display'):
            ...
        else:
            display = f'no command (in DuckBot)'

        embed = discord.Embed(title=f'An error has occurred in {display}', timestamp=packet['time'])
        embed.add_field(
            name='Metadata',
            value='\n'.join([f'**{k.title()}**: {v}' for k, v in fmt.items()]),
        )

        kwargs: Dict[str, Any] = {}
        if self.bot.user:
            kwargs['username'] = self.bot.user.display_name
            kwargs['avatar_url'] = self.bot.user.display_avatar.url

            embed.set_author(name=str(self.bot.user), icon_url=self.bot.user.display_avatar.url)

        webhook = self.error_webhook
        if webhook.is_partial():
            self.error_webhook = webhook = await self.error_webhook.fetch()

        code_chunks = list(self._yield_code_chunks(traceback))

        embed.description = code_chunks.pop(0)
        await webhook.send(embed=embed, **kwargs)

        embeds: List[discord.Embed] = []
        for entry in code_chunks:
            embed = discord.Embed(description=entry)
            if self.bot.user:
                embed.set_author(name=str(self.bot.user), icon_url=self.bot.user.display_avatar.url)

            embeds.append(embed)

            if len(embeds) == 10:
                await webhook.send(embeds=embeds, **kwargs)
                embeds = []

        if embeds:
            await webhook.send(embeds=embeds, **kwargs)

    async def add_error(
        self, *, error: BaseException, ctx: Optional[DuckContext] = None, display: Optional[str] = None
    ) -> None:
        """Add an error to the error manager. This will handle all cooldowns and internal cache management
        for you. This is the recommended way to add errors.

        Parameters
        ----------
        error: :class:`BaseException`
            The error to add.
        ctx: Optional[:class:`DuckContext`]
            The invocation context of the error, if any.
        display: Optional[:class:`str`]
            Overwritten display text. Defaults to the command name, or "no command"
        """
        log.info('Adding error "%s" to log.', str(error))

        packet: DuckTraceback = {'time': (ctx and ctx.message.created_at) or discord.utils.utcnow(), 'exception': error}

        if ctx is not None:
            addons: _DuckTracebackOptional = {
                'command': ctx.command,
                'author': ctx.author.id,
                'guild': (ctx.guild and ctx.guild.id) or None,
                'channel': ctx.channel.id,
            }
            if display:
                addons['display'] = display
            packet.update(addons)  # type: ignore

        traceback_string = ''.join(traceback.format_exception(type(error), error, error.__traceback__)).replace(
            os.getcwd(), 'CWD'
        )
        current = self.errors.get(traceback_string)

        if current:
            self.errors[traceback_string].append(packet)
        else:
            self.errors[traceback_string] = [packet]

        async with self._lock:
            # I want all other errors to be released after this one, which is why
            # lock is here. If you have code that calls MANY errors VERY fast,
            # this will ratelimit the webhook. We don't want that lmfao.

            if not self._most_recent:
                self._most_recent = discord.utils.utcnow()
                await self.release_error(traceback_string, packet)
            else:
                time_between = packet['time'] - self._most_recent

                if time_between > self.cooldown:
                    self._most_recent = discord.utils.utcnow()
                    return await self.release_error(traceback_string, packet)
                else:  # We have to wait
                    log.debug('Waiting %s seconds to release error', time_between.total_seconds())
                    await asyncio.sleep(time_between.total_seconds())

                    self._most_recent = discord.utils.utcnow()
                    return await self.release_error(traceback_string, packet)


class HandleHTTPException(AbstractAsyncContextManager, AbstractContextManager):
    """
    A context manager that handles HTTP exceptions for them to be
    delivered to a destination channel without needing to create
    an embed and send every time.

    This is useful for handling errors that are not critical, but
    still need to be reported to the user.

    Parameters
    ----------
    destination: :class:`discord.abc.Messageable`
        The destination channel to send the error to.
    title: Optional[:class:`str`]
        The title of the embed. Defaults to ``'An unexpected error occurred!'``.

    Attributes
    ----------
    destination: :class:`discord.abc.Messageable`
        The destination channel to send the error to.
    message: Optional[:class:`str`]
        The string to put the embed title in.

    Raises
    ------
    `SilentCommandError`
        Error raised if an HTTPException is encountered. This
        error is specifically ignored by the command error handler.
    """

    __slots__ = ('destination', 'message')

    def __init__(self, destination: discord.abc.Messageable, *, title: Optional[str] = None):
        self.destination = destination
        self.message = title

    def __enter__(self):
        return self

    async def __aenter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> bool:
        log.warning(
            'Context manager HandleHTTPException was used with `with` statement.'
            '\nThis can be somewhat unreliable as it uses create_task, '
            'please use `async with` syntax instead.'
        )

        if exc_val is not None and isinstance(exc_val, discord.HTTPException) and exc_type is not None:
            embed = discord.Embed(
                title=self.message or 'An unexpected error occurred!',
                description=f'{exc_type.__name__}: {exc_val.text}',
                colour=discord.Colour.red(),
            )

            loop = asyncio.get_event_loop()
            loop.create_task(self.destination.send(embed=embed))
            raise SilentCommandError
        return False

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> bool:
        if exc_val is not None and isinstance(exc_val, discord.HTTPException) and exc_type:
            embed = discord.Embed(
                title=self.message or 'An unexpected error occurred!',
                description=f'{exc_type.__name__}: {exc_val.text}',
                colour=discord.Colour.red(),
            )

            await self.destination.send(embed=embed)
            raise SilentCommandError

        return False

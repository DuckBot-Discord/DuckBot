from __future__ import annotations

import datetime
import asyncio
import asyncpg
import logging
from typing import (
    Optional, 
    TYPE_CHECKING,
    Tuple,
    Dict,
    Any
)

import discord
from discord.ext import commands

from . import time
from .context import DuckContext
from .errors import TimerNotFound

if TYPE_CHECKING:
    from bot import DuckBot
    from asyncpg import Record, Connection

log = logging.getLogger('DuckBot.utils.timer')

    
class Timer:
    """Represents a Timer within the database.
    
    .. container:: operations

        .. describe:: x == y

            Determines if the Timer is equal to another Timer.
        
        .. describe:: x != y

            Determines if the Timer is not equal to another Timer.
        
        .. describe:: hash(x)

            Returns the hash of the Timer.
        
        .. describe:: repr(x)

            Returns the string representation of the Timer.
    
    Attributes
    ----------
    args: List[Any]
        A list of arguments to pass to the :meth:`TimerManager.create_timer` method.
    kwargs: Dict[Any, Any]
        A dictionary of keyword arguments to pass to the :meth:`TimerManager.create_timer` method.
    precise: :class:`bool`
        Whether or not to dispatch the timer listener with the timer's args and kwargs. If ``False``, only
        the timer will be passed to the listener.
    event: :class:`str`
        The event to trigger when the timer expires. The listener can be formatted as so: ``on_{timer.event}_timer_complete``
    created_at: :class:`datetime.datetime`
        The time the timer was created.
    expires: :class:`datetime.datetime`
        The time the timer expires.
    """
    __slots__: Tuple[str, ...] = (
        'args', 
        'kwargs', 
        'precise',
        'event', 
        'id', 
        'created_at',
        'expires', 
        '_cs_event_name'
    )

    def __init__(self, *, record: Record):
        self.id = record['id']

        extra = record['extra']
        self.args = extra.get('args', [])
        self.kwargs = extra.get('kwargs', {})
        self.precise: bool = record['precise']
        
        self.event = record['event']
        self.created_at = record['created']
        self.expires = record['expires']

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Timer):
            return False
        
        return self.id == other.id
    
    def __ne__(self, _o: object) -> bool:
        return not self.__eq__(_o)

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __repr__(self) -> str:
        return f'<Timer created={self.created_at} expires={self.expires} event={self.event}>'

    @property
    def human_delta(self):
        return time.human_timedelta(self.expires)
    
    @discord.utils.cached_slot_property('_cs_event_name')
    def event_name(self) -> str:
        """:class:`str`: Returns the timer's event name."""
        return f'{self.event}_timer_complete'


class TimerManager:
    """A class used to create and manage timers.
    
    Please note this can be inherited in a cog to allow for easy
    timer management.
    
    Attributes
    ----------
    bot: :class:`~.DuckBot` 
        The bot instance.
    """
    __slots__: Tuple[str, ...] = (
        'name',
        'bot', 
        '_have_data',
        '_current_timer', 
        '_task',
        '_cs_display_emoji',
    )
    
    def __init__(self, *, bot: DuckBot):
        self.bot: DuckBot = bot
        
        self._have_data = asyncio.Event()
        self._current_timer = None
        self._task = bot.loop.create_task(self.dispatch_timers())
    
    @discord.utils.cached_slot_property('_cs_display_emoji')
    def display_emoji(self) -> discord.PartialEmoji:
        """:class:`discord.PartialEmoji`: The emoji to display when a timer is dispatched."""
        return discord.PartialEmoji(name='\N{ALARM CLOCK}')
    
    def cog_unload(self):
        """Called when the cog is unloaded to cancel the current running task."""
        self._task.cancel()
        
    async def cog_command_error(self, ctx: DuckContext, error: Exception) -> discord.Message:
        """|coro|
        
        Called when the cog encounters an error. This will only be called if the class is 
        inherited in a cog. Otherwise, it will do nothing.
        
        Parameters
        ----------
        ctx: :class:`~.DuckContext`
            The invocation context.
        error: :class:`Exception`
            The error that was encountered.
        
        Returns
        -------
        :class:`discord.Message`
            The message that was sent.
        """
        
        if isinstance(error, commands.BadArgument):
            return await ctx.send(error)
        if isinstance(error, commands.TooManyArguments):
            return await ctx.send(f'You called the {(ctx.command and ctx.command.name) or ""} command with too many arguments.')
        
        # This is a new error, let's release it to the logger and let the user know what happened.
        await self.bot.exceptions.add_error(error=error, ctx=ctx)
        
        embed = discord.Embed(
            title='Oh no!',
            description=f'I ran into a new error while trying to execute this command.'
        )
        embed.add_field(name='No worries!', value='I\'ve contacted our developers and they\'ll be looking into it.')
        return await ctx.send(embed=embed)
            
    async def get_active_timer(self, *, connection: Optional[Connection] = None, days: int = 7) -> Optional[Timer]:
        """|coro|
        
        Called to get the most current active timer in the database. This timer is expired and should be dispatched.
        
        Parameters
        ----------
        connection: Optional[:class:`asyncpg.Connection`]
            The connection to use.
        days: :class:`int`
            The number of days to look back.
            
        Returns
        -------
        Optional[:class:`Timer`]
            The timer that is expired and should be dispatched.
        """
        query = f"SELECT * FROM timers WHERE expires IS NOT NULL AND expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1;"
        if connection:
            record = await connection.fetchrow(query, datetime.timedelta(days=days), False)
        else:
            async with self.bot.safe_connection() as conn:
                record = await conn.fetchrow(query, datetime.timedelta(days=days), False)

        return Timer(record=record) if record else None
    
    async def wait_for_active_timers(self, *, days: int = 7) -> Optional[Timer]:
        """|coro|
        
        Waity for a timer that has expired. This will wait until a timer is expired and should be dispatched.
        
        Parameters
        ----------
        days: :class:`int`
            The number of days to look back.
            
        Returns
        -------
        :class:`Timer`
            The timer that is expired and should be dispatched.
        """
        # Please note the return value in the doc is different than the one in the function.
        # This function actually only returns a Timer but pyright doesn't like typehinting that.
        
        async with self.bot.safe_connection() as con:
            timer = await self.get_active_timer(connection=con, days=days)
            if timer is not None:
                log.debug('Recieved active timer: %s', timer)
                self._have_data.set()
                return timer

            self._have_data.clear()
            self._current_timer = None
            await self._have_data.wait()
            return await self.get_active_timer(connection=con, days=days)
        
    def call_timer(self, timer: Timer) -> None:
        """Call an expired timer to dispatch it.
        
        Parameters
        ----------
        timer: :class:`Timer`
            The timer to dispatch.
        """
        log.debug('Dispatching timer %s', timer)
        if timer.precise:
            self.bot.dispatch(timer.event_name, *timer.args, **timer.kwargs)
        else:
            self.bot.dispatch(timer.event_name, timer)
    
    async def dispatch_timers(self) -> None:
        """|coro|
        
        The main dispatch loop. This will wait for a timer to expire and dispatch it.
        Please note if you use this class, you need to cancel the task when you're done 
        with it.
        """
        try:
            while not self.bot.is_closed():
                # can only asyncio.sleep for up to ~48 days reliably
                # so we're gonna cap it off at 40 days
                # see: http://bugs.python.org/issue20493
                timer = self._current_timer = await self.wait_for_active_timers(days=40)
                if timer is None: # To make type checker happy
                    continue
                
                now = datetime.datetime.utcnow()

                if timer.expires >= now: 
                    to_sleep = (timer.expires - now).total_seconds() 
                    await asyncio.sleep(to_sleep)

                self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError): 
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())
        
    async def create_timer(
        self, 
        when: datetime.datetime,
        event: str = 'timer',
        *args, 
        now: Optional[datetime.datetime] = None,
        precise: bool = True,
        **kwargs
    ) -> Timer:
        """|coro|
        
        Used to create a timer in the database and dispatch it.
        
        Parameters
        ----------
        when: :class:`datetime.datetime`
            When the timer should expire and be dispatched.
        event: :class:`str`
            The event to trigger when the timer expires. The listener can be formatted as so: ``on_{timer.event}_timer_complete``
        *args: List[Any]
            A list of arguments to be passed to :class:`Timer.args`. please note all items in this list
            must be JSON serializable.
        precise: :class:`bool`
            Whether or not to dispatch the timer listener with the timer's args and kwargs. If ``False``, only
            the timer will be passed to the listener. Defaults to ``True``.
        **kwargs: Dict[:class:`str`, Any]
            A dictionary of keyword arguments to be passed to :class:`Timer.kwargs`. Please note each element
            in this dictionary must be JSON serializable.
        """
        now = now or discord.utils.utcnow()
            
        # Remove timezone information since the database does not deal with it
        if not when:
            when = datetime.datetime(year=3000, month=1, day=1)
        
        when = when.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        now = now.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        delta = (when - now).total_seconds()

        async with self.bot.safe_connection() as conn:
            row = await conn.fetchrow(
                f"""INSERT INTO timers(
                        event,
                        created,
                        expires,
                        extra,
                        precise
                    )
                    VALUES(
                        $1,
                        $2,
                        $3,
                        $4,
                        $5
                    )
                    RETURNING *;
                """, 
                event,
                now,
                when,
                {'args': args, 'kwargs': kwargs},
                precise,
            )
            
        # only set the data check if it can be waited on
        if delta <= (86400 * 40): # 40 days
            self._have_data.set()

        # check if this timer is earlier than our currently run timer
        if self._current_timer and when < self._current_timer.expires:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())
        
        timer = Timer(record=row)
        return timer
    
    async def get_timer(self, id: int) -> Timer:
        """|coro|
        
        Used to get a timer from it's ID.
        
        Parameters
        ----------
        id: :class:`int`
            The ID of the timer to get.
        
        Returns
        -------
        :class:`Timer`
            The timer that was fetched.
            
        Raises
        ------
        TimerNotFound
            A timer with that ID does not exist.
        """
        async with self.bot.safe_connection() as conn:
            data = await conn.fetchrow(f'SELECT * FROM timers WHERE id = $1', id)
        
        if not data:
            raise TimerNotFound(id)
        
        return Timer(record=data)
    
    async def delete_timer(self, id: int) -> None:
        """|coro|
        
        Delete a timer using it's ID.
        
        Parameters
        ----------
        id: :class:`int`
            The ID of the timer to delete.
            
        Raises
        ------
        TimerNotFound
            A timer with that ID does not exist, so there is nothing
            to delete.
        """
        async with self.bot.safe_connection() as conn:
            data = await conn.fetchrow(f'SELECT * FROM timers WHERE id = $1', id)
        
            if not data:
                raise TimerNotFound(id)
            
            await conn.execute(f'DELETE FROM timers WHERE id = $1', id)
from __future__ import annotations

import asyncio
import time as time_lib
from typing import (
    TYPE_CHECKING,
    Dict,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Callable,
    Awaitable,
    Union,
)
try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

import discord
from discord.ext import commands

from .errors import *
from .context import *
from .errorhandler import *

if TYPE_CHECKING:
    from bot import DuckBot

T = TypeVar('T')
P = ParamSpec('P')
BET = TypeVar('BET', bound='discord.guild.BanEntry')

def add_logging(func: Callable[P, Union[Awaitable[T], T]]) -> Callable[P, Union[Awaitable[T], T]]:
    """
    Used to add logging to a coroutine or function.
    
    .. code-block:: python3
        >>> async def foo(a: int, b: int) -> int:
        >>>     return a + b
        
        >>> logger = add_logging(foo)
        >>> result = await logger(1, 2)
        >>> print(result)
        3
        
        >>> def foo(a: int, b: int) -> int:
        >>>     return a + b
        
        >>> logger = add_logging(foo)
        >>> result = logger(1, 2)
        >>> print(result)
        3
    """
    async def _async_wrapped(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
        start = time_lib.time()
        result = await func(*args, **kwargs)  # type: ignore
        print(f'{func.__name__} took {time_lib.time() - start:.2f} seconds')
        
        return result # type: ignore
    
    def _sync_wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time_lib.time()
        result = func(*args, **kwargs)
        print(f'{func.__name__} took {time_lib.time() - start:.2f} seconds')
        
        return result # type: ignore
    
    return _async_wrapped if asyncio.iscoroutinefunction(func) else _sync_wrapped # type: ignore


async def can_execute_action(
    ctx: DuckContext, 
    target: Union[discord.Member, discord.User],
    *,
    fail_if_not_upgrade: bool = True,
) -> Optional[bool]:
    """|coro|
    
    A wrapped predicate to check if the action can be executed.
    
    Parameters
    ----------
    ctx: :class:`commands.Context`
        The context of the command.
    
    Returns
    -------
    Optional[:class:`bool`]
        Whether the action can be executed.
        
    Raises
    ------
    HierarchyException
        The action cannot be executed due to role hierarchy.
    ActionNotExecutable
        The action cannot be executed due to other reasons.
    commands.NoPrivateMessage
        This command cannot be used in private messages.
    """
    guild = ctx.guild
    if guild is None or not isinstance(ctx.author, discord.Member):
        raise commands.NoPrivateMessage('This command cannot be used in private messages.')
    
    if isinstance(target, discord.User):
        upgraded = await ctx.bot.get_or_fetch_member(guild, target)
        if upgraded is None:
            if fail_if_not_upgrade:
                return
        else:
            target = upgraded
            
    if isinstance(target, discord.Member):
        if guild.me.top_role <= target.top_role:
            raise HierarchyException(target)
        if ctx.author.top_role <= target.top_role:
            raise HierarchyException(target, author_error=True) 
        
    if ctx.author == target:
        raise ActionNotExecutable('You cannot execute this action on yourself!')
    if guild.owner == target:
        raise ActionNotExecutable('I cannot execute any action on the server owner!')
    if guild.owner == ctx.author:
        return 


def safe_reason(author: Union[discord.Member, discord.User], reason: str, *, length: int = 512) -> str:
    base = f'Action by {author} ({author.id}) for: '
    
    length_limit = length - len(base)
    if len(reason) > length_limit:
        reason = reason[:length_limit-3] + '...'
        
    return base + reason


class DuckCog(commands.Cog):
    """The base class for all DuckBot cogs.
    
    Attributes
    ----------
    bot: DuckBot
        The bot instance.
    """
    if TYPE_CHECKING:
        emoji: Optional[str]
        brief: Optional[str]
    
    __slots__: Tuple[str, ...] = (
        'bot',
    )

    def __init_subclass__(cls: Type[DuckCog], **kwargs) -> None:
        """
        This is called when a subclass is created.
        Its purpose is to add parameters to the cog
        that will later be used in the help command.
        """
        cls.emoji = kwargs.pop('emoji', None)
        cls.brief = kwargs.pop('brief', None)
        return super().__init_subclass__(**kwargs)
     
    def __init__(self, bot: DuckBot) -> None:
        self.bot: DuckBot = bot


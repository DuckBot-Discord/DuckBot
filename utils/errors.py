from __future__ import annotations

import logging
from typing import (
    Tuple,
)

import discord


log = logging.getLogger('Duckbot.utils.errors')

# NOTE: Add me back later when all exceptions have been made
#__all__: Tuple[str, ...] = (
#    'DuckBotException',
#    'DuckBotNotStarted',
#)


class DuckBotException(discord.ClientException):
    """The base exception for DuckBot. All other exceptions should inherit from this."""
    __slots__: Tuple[str, ...] = ()


class DuckBotNotStarted(DuckBotException):
    """An exeption that gets raised when a method tries to use :attr:`Duckbot.user` before
    DuckBot is ready.
    """
    __slots__: Tuple[str, ...] = ()
    
    
class HierarchyException(DuckBotException):
    """Raised when DuckBot is requested to perform an operation on a member
    that is higher than them in the guild hierarchy.
    """
    __slots__: Tuple[str, ...] = (
        'member',
    )
    
    def __init__(self, member: discord.Member) -> None:
        self.member: discord.Member = member
        super().__init__(f'{member}\'s top role, {member.top_role.mention} is higher than mine. I can not do this operation.')


class TimerError(DuckBotException):
    """The base for all timer base exceptions. Every Timer based error should inherit
    from this.
    """
    __slots__: Tuple[str, ...] = ()

class TimerNotFound(TimerError):
    """Raised when trying to fetch a timer that does not exist."""
    __slots__: Tuple[str, ...] = (
        'id',
    )
    
    def __init__(self, id: int) -> None:
        self.id: int = id
        super().__init__(f'Timer with ID {id} not found.')
    
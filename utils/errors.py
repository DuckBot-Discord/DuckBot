from __future__ import annotations

import logging
from typing import (
    Tuple,
)

import discord


log = logging.getLogger('Duckbot.utils.errors')

__all__: Tuple[str, ...] = (
    'DuckBotException',
    'DuckBotNotStarted',
)


class DuckBotException(discord.ClientException):
    """The base exception for DuckBot. All other exceptions should inherit from this."""
    __slots__: Tuple[str, ...] = ()


class DuckBotNotStarted(DuckBotException):
    """An exeption that gets raised when a method tries to use :attr:`Duckbot.user` before
    DuckBot is ready.
    """
    __slots__: Tuple[str, ...] = ()


class TimerError(DuckBotException):
    """The base for all timer base exceptions. Every Timer based error should inherit
    from this.
    """


class TimerNotFound(TimerError):
    """Raised when trying to fetch a timer that does not exist."""
    __slots__: Tuple[str, ...] = (
        'id',
    )
    
    def __init__(self, id: int) -> None:
        self.id: int = id
        super().__init__(f'Timer with ID {id} not found.')
    
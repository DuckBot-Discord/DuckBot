from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Tuple,
)

import discord

if TYPE_CHECKING:
    pass

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

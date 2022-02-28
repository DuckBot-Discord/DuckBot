from __future__ import annotations

from typing import Tuple

from discord import ClientException

__all__: Tuple[str, ...] = (
    'DuckBotException',
    'DuckBotNotStarted',
)


class DuckBotException(ClientException):
    """The base exception for DuckBot. All other exceptions should inherit from this."""
    __slots__: Tuple[str, ...] = ()


class DuckBotNotStarted(DuckBotException):
    """An exeption that gets raised when a method tries to use :attr:`Duckbot.user` before
    DuckBot is ready.
    """
    __slots__: Tuple[str, ...] = ()

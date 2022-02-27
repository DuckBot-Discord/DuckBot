from __future__ import annotations

from typing import Tuple

from discord import ClientException

__all__: Tuple[str, ...] = (
    'DuckBotException',
    'DuckBotNotStarted',
)

class DuckBotException(ClientException):
    pass


class DuckBotNotStarted(DuckBotException):
    pass

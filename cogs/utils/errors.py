from __future__ import annotations

from typing import Tuple

from discord import ClientException

__all__: Tuple[str, ...] = (
    'DuckBotException',
)

class DuckBotException(ClientException):
    pass

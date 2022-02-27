from __future__ import annotations

from typing import Callable, Tuple, Optional

from discord.ext import commands

__all__: Tuple[str, ...] = (
    'DuckContext',
    'tick',
)

def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
    lookup = {
        True: '✅',
        False: '❌',
        None: '❔',
    }
    emoji = lookup.get(opt, '❌')
    if label is not None:
        return f'{emoji}: {label}'
    
    return emoji


class DuckContext(commands.Context):
    __slots__: Tuple[str, ...] = (
        'tick',
    )
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tick: Callable[[Optional[bool], Optional[str]], str] = tick
    
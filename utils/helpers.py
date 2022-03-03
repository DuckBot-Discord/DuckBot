import typing
from typing import Tuple

__all__: Tuple[str, ...] = (
    'col',
)

import discord.utils


def col(color=None, /, *, fmt=0, bg=False) -> str:
    """
    Returns the ascii color escape string for the given number.

    :param color: The color number.
    :param fmt: The format number.
    :param bg: Whether to return as a background color
    """
    base = "\u001b["
    if fmt != 0:
        base += "{fmt};"
    if color is None:
        base += "{color}m"
        color = 0
    else:
        if bg is True:
            base += "4{color}m"
        else:
            base += "3{color}m"
    return base.format(fmt=fmt, color=color)

def mdr(entity: typing.Any) -> str:
    """Returns the string of an object with discord markdown removed.

    Parameters
    ----------
    entity: Any
        The object to remove markdown from.

    Returns
    -------
    str
        The string of the object with markdown removed.
    """
    return discord.utils.remove_markdown(str(entity))

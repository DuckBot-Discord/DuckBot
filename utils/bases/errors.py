from __future__ import annotations

import logging
import typing
from typing import Tuple, Type

import discord
from discord.ext.commands import BadArgument, CheckFailure, CommandError

from utils.types import DiscordMedium

log = logging.getLogger('Duckbot.utils.errors')

__all__: Tuple[str, ...] = (
    'DuckBotException',
    'DuckNotFound',
    'DuckBotCommandError',
    'DuckBotNotStarted',
    'HierarchyException',
    'ActionNotExecutable',
    'TimerError',
    'TimerNotFound',
    'MuteException',
    'MemberNotMuted',
    'MemberAlreadyMuted',
    'NoMutedRole',
    'SilentCommandError',
    'EntityBlacklisted',
)


class DuckBotException(discord.ClientException):
    """The base exception for DuckBot. All other exceptions should inherit from this."""

    __slots__: Tuple[str, ...] = ()


class DuckNotFound(DuckBotException):
    """An Exception raised when DuckBot couuld not be found."""

    __slots__: Tuple[str, ...] = ()


class DuckBotCommandError(CommandError, DuckBotException):
    """The base exception for DuckBot command errors."""

    __slots__: Tuple[str, ...] = ()


class DuckBotNotStarted(DuckBotException):
    """An exeption that gets raised when a method tries to use :attr:`Duckbot.user` before
    DuckBot is ready.
    """

    __slots__: Tuple[str, ...] = ()


class HierarchyException(DuckBotCommandError):
    """Raised when DuckBot is requested to perform an operation on a member
    that is higher than them in the guild hierarchy.
    """

    __slots__: Tuple[str, ...] = (
        'target',
        'author_error',
    )

    def __init__(self, target: discord.Member | discord.Role, *, author_error: bool = False) -> None:
        self.target: discord.Member | discord.Role = target
        self.author_error: bool = author_error
        if isinstance(target, discord.Member):
            if author_error is False:
                super().__init__(f'**{target}**\'s top role is higher than mine. I can\'t do that.')
            else:
                super().__init__(f'**{target}**\'s top role is higher than your top role. You can\'t do that.')
        else:
            if author_error:
                super().__init__(f'Role **{target}** is higher than your top role. You can\'t do that.')
            else:
                super().__init__(f'Role **{target}** is higher than my top role. I can\'t do that.')


class ActionNotExecutable(DuckBotCommandError):
    def __init__(self, message):
        super().__init__(f'{message}')


class TimerError(DuckBotException):
    """The base for all timer base exceptions. Every Timer based error should inherit
    from this.
    """

    __slots__: Tuple[str, ...] = ()


class TimerNotFound(TimerError):
    """Raised when trying to fetch a timer that does not exist."""

    __slots__: Tuple[str, ...] = ('id',)

    def __init__(self, id: int) -> None:
        self.id: int = id
        super().__init__(f'Timer with ID {id} not found.')


class MuteException(DuckBotCommandError):
    """Raised whenever an operation related to a mute fails."""

    pass


class MemberNotMuted(MuteException):
    """Raised when trying to unmute a member that is not muted."""

    __slots__: Tuple[str, ...] = ('member',)

    def __init__(self, member: discord.Member) -> None:
        self.member: discord.Member = member
        super().__init__(f'{member} is not muted.')


class MemberAlreadyMuted(MuteException):
    """Raised when trying to mute a member that is already muted."""

    __slots__: Tuple[str, ...] = ('member',)

    def __init__(self, member: discord.Member) -> None:
        self.member: discord.Member = member
        super().__init__(f'{member} is already muted.')


class NoMutedRole(MuteException):
    """Raised when a guild does not have a muted role."""

    __slots__: Tuple[str, ...] = tuple()

    def __init__(self) -> None:
        super().__init__('This server doesn\'t have a mute role configured. Run `db.muterole` for more info.')


class SilentCommandError(DuckBotCommandError):
    """This exception will be purposely ignored by the error handler
    and will not be logged. Handy for stopping something that can't
    be stopped with a simple ``return`` statement.
    """

    __slots__: Tuple[str, ...] = ()


class EntityBlacklisted(CheckFailure, DuckBotCommandError):
    """Raised when an entity is blacklisted."""

    __slots__: Tuple[str, ...] = ('entity',)

    def __init__(
        self,
        entity: typing.Union[
            discord.User,
            discord.Member,
            discord.Guild,
            discord.abc.GuildChannel,
        ],
    ) -> None:
        self.entity = entity
        super().__init__(f'{entity} is blacklisted.')


class PartialMatchFailed(DuckBotCommandError, BadArgument):
    """Raised when the PartiallyMatch converter fails"""

    def __init__(self, argument: str, types: Tuple[Type[DiscordMedium]]):
        self.argument = argument
        self.converters = types

        types_as_str = ", ".join(_type.__name__ for _type in types)

        super().__init__(f'Could not find "{argument}" as: {types_as_str}')

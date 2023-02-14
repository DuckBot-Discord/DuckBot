from __future__ import annotations

import re
from typing import (
    List,
    Optional,
    Type,
    Union,
    Tuple,
    Dict,
    TypeVar,
    TypeVarTuple,
    Generic,
)

import discord
from discord.ext import commands
from discord.ext.commands import FlagConverter as DCFlagConverter, Flag, MissingFlagArgument

from .helpers import can_execute_action
from utils.bases.context import DuckContext
from .errorhandler import HandleHTTPException

__all__: Tuple[str, ...] = (
    'TargetVerifier',
    'BanEntryConverter',
    'UntilFlag',
    'FlagConverter',
    'ChannelVerifier',
    'VerifiedUser',
    'VerifiedMember',
)


FCT = TypeVar('FCT', bound='DCFlagConverter')

TTuple = TypeVarTuple('TTuple')
T = TypeVar('T')


class ChannelVerifier:
    def check_channel(self, channel: discord.abc.GuildChannel | discord.Thread) -> bool:
        raise NotImplementedError


class TargetVerifier(Generic[*TTuple]):
    """Used to verify a traget is permitted to perform
    an action upon another target.

    In this use case, the target is being checked by
    :attr:`DuckBot.author` for an operation.

    .. code-block:: python3

        @commands.command()
        async def ban(self, ctx: DuckContext, member: TargetVerifier[discord.Member, discord.User], *, reason: str = '...'):
            await member.ban(reason=reason)
    """

    __slots__: Tuple[str, ...] = ('target', 'fail_if_not_upgrade', '_targets', '_converter')

    def __class_getitem__(cls, types: Tuple[*TTuple]):
        if isinstance(types, tuple):
            return cls(*types)
        else:
            return cls(types)

    def __init__(self, *targets: *TTuple) -> None:
        self._targets = targets
        if len(targets) > 2:
            self._converter = targets[0]
        else:
            print(targets)
            self._converter = Union[targets]  # type: ignore

    async def convert(self, ctx: DuckContext, argument: str):
        """|coro|

        The main convert method of the converter. This will use the types given to transform the argument
        to the given type, then verify that the target is permitted to perform the action.

        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context of the command.
        argument: :class:`str`
            The argument to convert.

        Returns
        -------
        Union[discord.Member, discord.User]
            The converted target as specifying when defining the converter.
        """
        target = await commands.run_converters(
            ctx, converter=self._converter, argument=argument, param=ctx.current_parameter
        )
        print(self._converter is Union)
        await can_execute_action(ctx, target, should_upgrade=self._converter is Union)
        self.target = target
        return target


# Including `commands.Converter` is faster on discord backend iirc
class BanEntryConverter(discord.guild.BanEntry):
    """
    A converter for :class:`BanEntry`.

    .. container:: operations

        .. describe:: repr(x)

            Returns the string representation of the converter.

        .. describe:: str(x)

            Returns a formatted string of the converter showing the
            user who was banned and their ID. Formatted as ``'{0.user} ({0.user.id})'.format(self)``
    """

    @classmethod
    async def convert(cls: Type[BanEntryConverter], ctx: DuckContext, argument: str) -> discord.guild.BanEntry:
        """|coro|

        The main convert method of the converter. This will use the types given to transform the argument
        to a :class:`~disord.guild.BanEntry`.

        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context of the command.
        argument: :class:`str`
            The argument to convert.

        Returns
        -------
        :class:`~discord.guild.BanEntry`
            The converted target as specifying when defining the converter.
        """
        await ctx.typing()

        guild = ctx.guild
        if guild is None:
            raise commands.NoPrivateMessage('This command cannot be used in private messages.')

        # this isn't really necessary, but it's just in case an error occurs while
        # fetching the bans, like Missing Permissions. Shouldn't happen though.
        async with HandleHTTPException(ctx):
            if argument.isdigit():
                member_id = int(argument, base=10)
                try:
                    entry = await guild.fetch_ban(discord.Object(id=member_id))
                except discord.NotFound:
                    raise commands.BadArgument('This member has not been banned before.') from None
                else:
                    return cls(user=entry.user, reason=entry.reason)

            _find_entitiy = lambda u: str(u.user).lower() == argument.lower() or str(u.user.name).lower() == argument.lower()

            # we search by username now.
            ban_list = [b async for b in guild.bans(limit=None)]
            entity = discord.utils.find(_find_entitiy, ban_list)

            if entity is None:
                raise commands.BadArgument('This member has not been banned before.')

            return cls(user=entity.user, reason=entity.reason)

    def __repr__(self) -> str:
        return '<BanEntryConverter user={0.user} ({0.user.id}) reason={0.reason}>'

    def __str__(self) -> str:
        return '{0.user} ({0.user.id})'.format(self)


class UntilFlag(Generic[T, FCT]):
    """A converter that will convert until a flag is reached.
    **Example**
    .. code-block:: python3
        from typing import Optional
        from discord.ext import commands
        class SendFlags(commands.commands.FlagConverter, prefix='--', delimiter=' '):
            channel: Optional[discord.TextChannel] = None
            reply: Optional[discord.Message] = None
        @commands.command()
        async def send(self, ctx: HideoutContext, *, text: UntilFlag[SendFlags]):
            '''Send a message to a channel.'''
            channel = text.flags.channel or ctx.channel
            await channel.send(text.value)
    Attributes
    ----------
    value: :class:`str`
        The value of the converter.
    flags: :class:`commands.FlagConverter`
        The resolved flags.
    """

    def __init__(self, value: T, converter: Type[T], flags: FCT) -> None:
        # fmt: off
        self.value = value
        self.flags = flags

        if hasattr(converter, '__metadata__'):
            # Annotated[X, Y] can access Y via __metadata__
            converter = converter.__metadata__[0]

        self._converter = converter
        self._regex: re.Pattern[str] = self.flags.__commands_flag_regex__  # pyright: reportUnknownMemberType=false, reportGeneralTypeIssues=false
        self._start: str = (self.flags.__commands_flag_prefix__)  # pyright: reportUnknownMemberType=false, reportGeneralTypeIssues=false

    def __class_getitem__(cls, item: Tuple[Type[T], Type[commands.FlagConverter]]) -> UntilFlag[T, FCT]:
        converter, flags = item
        return cls(value='...', flags=flags(), converter=converter)

    def validate_value(self, argument: str) -> bool:
        """Used to validate the parsed value without flags.
        Defaults to checking if the argument is a valid string.
        If overridden, this method should return a boolean or raise an error.
        Can be a coroutine
        Parameters
        ----------
        argument: :class:`str`
            The argument to validate.
        Returns
        -------
        :class:`str`
            Whether or not the argument is valid.
        Raises
        ------
        :class:`commands.BadArgument`
            No value was given
        """
        stripped = argument.strip()
        if not stripped or stripped.startswith(self._start):
            raise commands.BadArgument(f'No body has been specified before the flags.')
        return True

    async def convert(self, ctx: DuckContext, argument: str) -> UntilFlag[T, FCT]:
        """|coro|
        The main convert method of the converter. This will take the given flag converter and
        use it to delimit the flags from the value.
        Parameters
        ----------
        ctx: :class:`HideoutContext`
            The context of the command.
        argument: :class:`str`
            The argument to convert.
        Returns
        -------
        :class:`UntilFlag`
            The converted argument.
        """
        value = self._regex.split(argument, maxsplit=1)[0]
        converted_value: T = await commands.run_converters(ctx, self._converter, value, ctx.current_parameter)
        commands.core
        print(f"converted is ", converted_value)
        if not await discord.utils.maybe_coroutine(self.validate_value, argument):
            raise commands.BadArgument('Failed to validate argument preceding flags.')
        flags = await self.flags.convert(ctx, argument=argument[len(value) :])
        return UntilFlag(value=converted_value, flags=flags, converter=self._converter)


class FlagConverter(DCFlagConverter):
    """A commands.FlagConverter but that supports Boolean flags with empty body."""

    @classmethod
    def parse_flags(cls, argument: str) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        flags = cls.__commands_flags__
        aliases = cls.__commands_flag_aliases__
        last_position = 0
        last_flag: Optional[Flag] = None

        case_insensitive = cls.__commands_flag_case_insensitive__
        for match in cls.__commands_flag_regex__.finditer(argument):
            begin, end = match.span(0)
            key = match.group('flag')
            if case_insensitive:
                key = key.casefold()

            if key in aliases:
                key = aliases[key]

            flag = flags.get(key)
            if last_position and last_flag is not None:
                value = argument[last_position : begin - 1].lstrip()
                if not value:
                    if not flag or flag.annotation is not bool:
                        raise MissingFlagArgument(last_flag)
                    else:
                        value = 'True'

                try:
                    values = result[last_flag.name]
                except KeyError:
                    result[last_flag.name] = [value]
                else:
                    values.append(value)

            last_position = end
            last_flag = flag

        # Add the remaining string to the last available flag
        if last_position and last_flag is not None:
            value = argument[last_position:].strip()
            if not value:
                if not last_flag or last_flag.annotation is not bool:
                    raise MissingFlagArgument(last_flag)
                else:
                    value = 'True'

            try:
                values = result[last_flag.name]
            except KeyError:
                result[last_flag.name] = [value]
            else:
                values.append(value)

        # Verification of values will come at a later stage
        return result


VerifiedMember = commands.param(converter=TargetVerifier[discord.Member])
VerifiedUser = commands.param(converter=TargetVerifier[discord.Member, discord.User])

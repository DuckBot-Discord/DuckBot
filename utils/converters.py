from __future__ import annotations

import re
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    TypeVarTuple,
    Union,
)

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Flag
from discord.ext.commands import FlagConverter as DCFlagConverter
from discord.ext.commands import MissingFlagArgument
from discord.ext.commands.core import unwrap_function

from utils.bases.errors import PartialMatchFailed
from utils.types import DiscordMedium

from .errorhandler import HandleHTTPException
from .helpers import can_execute_action

if TYPE_CHECKING:
    from bot import DuckBot
    from utils.bases.context import DuckContext

__all__: Tuple[str, ...] = (
    'TargetVerifier',
    'BanEntryConverter',
    'UntilFlag',
    'FlagConverter',
    'ChannelVerifier',
    'PartiallyMatch',
    'VerifiedUser',
    'VerifiedMember',
    'VerifiedRole',
    'DefaultRole',
    'require',
)

FCT = TypeVar('FCT', bound='DCFlagConverter')

TTuple = TypeVarTuple('TTuple')
T = TypeVar('T')


class MissingPermissionsIn(commands.BadArgument):
    def __init__(self, channel: discord.abc.GuildChannel | discord.Thread, missing: list[str], bot: bool = False) -> None:
        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(', '.join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'require {fmt} permission(s) in {channel.mention}.'
        super().__init__(['You ', 'I '][bot] + message)


class ChannelVerifier:
    """Used to verify a channel is permitted to perform an action upon another target.
    You are not meant to create this class yourself, instead use the :func:`require`.

    You can also prefix permissions with ``bot_`` to check bot permissions instead.

    .. code-block:: python3

        @commands.command()
        async def lock(self, ctx: DuckContext, channel: discord.TextChannel = require(manage_messages=True, bot_manage_roles=True)):
            ...
    """

    def __init__(self, **perms: bool) -> None:
        user_perms = {p: v for p, v in perms.items() if not p.startswith('bot_')}
        user_invalid: set[str] = set(user_perms) - set(discord.Permissions.VALID_FLAGS)
        if user_invalid:
            raise TypeError(f"Invalid permission(s): {', '.join(user_invalid)}")

        bot_perms: dict[str, bool] = {p.removeprefix('bot_'): v for p, v in perms.items() if p.startswith('bot_')}
        bot_invalid: set[str] = set(bot_perms) - set(discord.Permissions.VALID_FLAGS)
        if bot_invalid:
            bot_invalid = {f'bot_{p}' for p in bot_invalid}
            raise TypeError(f"Invalid permission(s): {', '.join(bot_invalid)}")

        self.permissions = user_perms
        self.bot_permissions = bot_perms

    def check_channel(self, ctx: DuckContext, channel: discord.abc.GuildChannel | discord.Thread):
        if not isinstance(ctx.author, discord.Member):
            raise commands.BadArgument(f'Could not verify permissions for you in {channel.mention}.')
        user_permissions = channel.permissions_for(ctx.author)
        missing = [perm for perm, value in self.permissions.items() if getattr(user_permissions, perm) != value]
        if missing:
            raise MissingPermissionsIn(channel, missing)

        bot_permissions = channel.permissions_for(ctx.guild.me)
        bot_missing = [perm for perm, value in self.bot_permissions.items() if getattr(bot_permissions, perm) != value]
        if bot_missing:
            raise MissingPermissionsIn(channel, missing, bot=True)
        return True

    def get_parameter_annotation(self, ctx: DuckContext):
        if not ctx.command:
            raise AttributeError(f'In {type(self).__name__}, something went very wrong! ctx.command was None')

        if not ctx.current_parameter:
            raise AttributeError(f'In {type(self).__name__}, something went very wrong! ctx.current_parameter was None')

        ann: Any = discord.abc.GuildChannel

        unwrap = unwrap_function(ctx.command.callback)
        for k, v in ctx.command.callback.__annotations__.items():
            if k == ctx.current_parameter.name:
                ann = discord.utils.evaluate_annotation(v, unwrap.__globals__, {}, {})

        return ann

    async def convert(self, ctx: DuckContext, argument: str) -> discord.abc.GuildChannel | discord.Thread:
        """This takes the annotation of the command, and then converts and verifies the channel.

        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context of the command.
        argument: :class:`str`
            The argument to convert.

        Returns
        -------
        Union[discord.abc.GuildChannel, discord.Thread]
            The converted target as specied when defining the converter.
        """
        if not ctx.current_parameter:
            raise AttributeError(f'In {type(self).__name__}, something went very wrong! ctx.current_parameter was None')

        ann = self.get_parameter_annotation(ctx)

        target: discord.abc.GuildChannel | discord.Thread = await commands.run_converters(
            ctx, converter=ann, argument=argument, param=ctx.current_parameter
        )
        print('gotten target')
        self.check_channel(ctx, target)
        return target


def require(*, default: bool = True, **perms: bool):
    converter = ChannelVerifier(**perms)

    if default:

        def default_func(ctx: DuckContext):
            if not ctx.current_parameter:
                raise AttributeError('In require.default_func, something went very wrong! ctx.current_parameter was None')

            _type = converter.get_parameter_annotation(ctx)
            if not isinstance(ctx.channel, _type):
                raise commands.MissingRequiredArgument(ctx.current_parameter)
            converter.check_channel(ctx, ctx.channel)  # type: ignore
            return ctx.channel

        return commands.parameter(converter=converter, default=default_func)

    return commands.parameter(converter=converter)


if TYPE_CHECKING:
    TargetVerifier = Union
else:

    class TargetVerifier(app_commands.Transformer, Generic[*TTuple]):
        """Used to verify a target (either Role, Member or User)
        is manageable/actionable by the command invoker.

        Behaviour
        ---------
        - If the given generic is discord.Role, a hierarchy check
        will be executed against ctx.author and ctx.me.
        - If the given generic is discord.Member, it will do role
        hierarchy checks

        .. code-block:: python3

            @commands.command()
            async def ban(self, ctx: DuckContext, member: TargetVerifier[discord.Member, discord.User], *, reason: str = '...'):
                await member.ban(reason=reason)
        """

        __slots__: Tuple[str, ...] = ('target', '_targets', '_converter')

        def __class_getitem__(cls, types: Tuple[*TTuple]):
            if isinstance(types, tuple):
                return cls(*types)
            else:
                return cls(types)

        @discord.utils.cached_property
        def type(self):
            if set(self._targets).issubset({discord.User, discord.Member, discord.abc.User}):
                return discord.AppCommandOptionType.user
            elif set(self._targets).issubset({discord.Role}):
                return discord.AppCommandOptionType.role
            elif set(self._targets).issubset({discord.Role, discord.User, discord.Member, discord.abc.User}):
                return discord.AppCommandOptionType.mentionable
            else:
                raise RuntimeError("TargetVerifier[] can only take User, Member and Role")

        def __init__(self, *targets: *TTuple) -> None:
            self._targets = targets
            if len(targets) > 2:
                self._converter = targets[0]
            else:
                self._converter = Union[targets]
            self.type  # access this to validate params.

        async def transform(self, interaction: discord.Interaction[DuckBot], value: Any) -> Any:
            await can_execute_action(interaction, value, should_upgrade=self._converter is Union)
            self.target = value
            return value

        async def convert(self, ctx: DuckContext, argument: str):
            """The main convert method of the converter. This will use the types given to transform the argument
            to the given type, then verify that the target is permitted to perform the action.

            Parameters
            ----------
            ctx: :class:`DuckContext`
                The context of the command.
            argument: :class:`str`
                The argument to convert.

            Returns
            -------
            Union[discord.Member, discord.User, discord.Role]
                The converted target as specifying when defining the converter.
            """

            if not ctx.current_parameter:
                raise AttributeError(f'In {type(self).__name__}, something went very wrong! ctx.current_parameter was None')

            target = await commands.run_converters(
                ctx, converter=self._converter, argument=argument, param=ctx.current_parameter
            )

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
    async def convert(cls: Type[BanEntryConverter], ctx: DuckContext, argument: str):
        """The main convert method of the converter. This will use the types given to transform the argument
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
        async def send(self, ctx: HideoutContext, *, text: UntilFlag[str, SendFlags]):
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
            converter = converter.__metadata__[0]  # type: ignore

        self._converter = converter
        self._regex: re.Pattern[str] = self.flags.__commands_flag_regex__
        self._start: str = (self.flags.__commands_flag_prefix__)

    def __class_getitem__(cls, item: Tuple[Type[T], Type[commands.FlagConverter]]) -> UntilFlag[T, FCT]:
        converter, flags = item
        return cls(value='...', flags=flags(), converter=converter)  # type: ignore

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
        """The main convert method of the converter. This will take the given flag converter and
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
        if not ctx.current_parameter:
            raise AttributeError(f'In {type(self).__name__}, something went very wrong! ctx.current_parameter was None')

        value = self._regex.split(argument, maxsplit=1)[0]
        assert ctx.current_parameter
        converted_value: T = await commands.run_converters(ctx, self._converter, value, ctx.current_parameter)
        commands.core
        if not await discord.utils.maybe_coroutine(self.validate_value, argument):
            raise commands.BadArgument('Failed to validate argument preceding flags.')
        flags = await self.flags.convert(ctx, argument=argument[len(value) :])
        return UntilFlag(value=converted_value, flags=flags, converter=self._converter)


class FlagConverter(DCFlagConverter):
    """A commands.FlagConverter but that supports Boolean flags with empty body."""

    @classmethod
    def parse_flags(cls, argument: str, *, ignore_extra: bool = True) -> Dict[str, List[str]]:
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
                    if flag and flag.annotation is bool:
                        value = 'True'
                    else:
                        raise MissingFlagArgument(last_flag)

                name = last_flag.name.casefold() if case_insensitive else last_flag.name

                try:
                    values = result[name]
                except KeyError:
                    result[name] = [value]
                else:
                    values.append(value)

            last_position = end
            last_flag = flag

        # Get the remaining string, if applicable
        value = argument[last_position:].strip()

        # Add the remaining string to the last available flag
        if last_flag is not None:
            if not value:
                raise MissingFlagArgument(last_flag)

            name = last_flag.name.casefold() if case_insensitive else last_flag.name

            try:
                values = result[name]
            except KeyError:
                result[name] = [value]
            else:
                values.append(value)
        elif value and not ignore_extra:
            # If we're here then we passed extra arguments that aren't flags
            raise commands.TooManyArguments(f'Too many arguments passed to {cls.__name__}')

        # Verification of values will come at a later stage
        return result


if TYPE_CHECKING:
    PartiallyMatch = Union
else:

    class PartiallyMatch(commands.Converter, Generic[*TTuple]):
        def __init__(self, *types: *TTuple):
            super().__init__()

            self.types = types
            self.converter: type | UnionType | None = None

            if len(types) == 1:
                self.converter = types[0]  # type: ignore
            elif len(types) > 1:
                self.converter = Union[types]

        def __class_getitem__(cls, types: Tuple[*TTuple]):
            if isinstance(types, tuple):
                return cls(*types)

            return cls(types)

        def retrieve_media_container(self, ctx: DuckContext, _type: type):
            match _type:
                case discord.User:
                    return ctx.bot.users
                case discord.Member:
                    return ctx.guild.members
                case discord.Role:
                    return ctx.guild.roles
                case discord.TextChannel:
                    return ctx.guild.text_channels
                case discord.VoiceChannel:
                    return ctx.guild.voice_channels
                case discord.CategoryChannel:
                    return ctx.guild.categories
                case discord.Thread:
                    return ctx.guild.threads
                case discord.abc.GuildChannel:
                    return ctx.guild.channels
                case discord.ForumChannel:
                    return ctx.guild.forums
                case discord.StageChannel:
                    return ctx.guild.stage_channels
                case _:
                    return None

        def partially_match_medium(self, media_container: list[DiscordMedium], argument: str) -> DiscordMedium | None:
            case_insensitive_argument = argument.lower()

            for medium in media_container:
                case_insensitive_nickname: str = ''
                case_insensitive_name = medium.name.lower()
                argument_in_name = (
                    case_insensitive_name.startswith(case_insensitive_argument)
                    or case_insensitive_argument in case_insensitive_name
                )
                try:
                    nickname_found = medium.nick  # type: ignore
                except AttributeError:
                    nickname_found = False

                if nickname_found:
                    case_insensitive_nickname = nickname_found.lower()

                argument_in_nickname = nickname_found and (
                    case_insensitive_nickname.startswith(case_insensitive_argument)
                    or case_insensitive_argument in case_insensitive_nickname
                )

                if not (argument_in_name or argument_in_nickname):
                    continue

                return medium

            return None

        async def convert(self, ctx: DuckContext, argument: str) -> DiscordMedium:
            try:
                assert ctx.current_parameter
                converted_argument = await commands.run_converters(ctx, self.converter, argument, ctx.current_parameter)

                return converted_argument
            except (commands.BadArgument, commands.BadUnionArgument) as error:
                for _type in self.types:
                    media_container_found = self.retrieve_media_container(ctx, _type)  # type: ignore

                    if not media_container_found:
                        continue

                    partial_match_found = self.partially_match_medium(media_container_found, argument)  # type: ignore

                    if partial_match_found:
                        return partial_match_found

                new_error = PartialMatchFailed(argument, self.types)  # type: ignore

                raise new_error from error


def _default_role(ctx: DuckContext):
    return ctx.guild.default_role


VerifiedMember: TypeAlias = Annotated[discord.Member, TargetVerifier[discord.Member]]
VerifiedUser: TypeAlias = Annotated[discord.Member | discord.User, TargetVerifier[discord.Member, discord.User]]
VerifiedRole: TypeAlias = Annotated[discord.Role, TargetVerifier[discord.Role]]
DefaultRole = commands.param(converter=VerifiedRole, default=_default_role)

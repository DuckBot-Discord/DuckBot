from __future__ import annotations

import typing
from typing import (
    Type,
    Union,
    Tuple,
    Dict,
    TypeVar,
    overload,
    TYPE_CHECKING,
    Optional,
)

import discord
from discord.ext import commands
from discord.utils import MISSING
from discord.ext.commands.view import StringView

from .helpers import can_execute_action
from .context import DuckContext
from .errorhandler import HandleHTTPException
from .errors import DuckBotCommandError

if TYPE_CHECKING:
    from typing_extensions import Self


BET = TypeVar('BET', bound='discord.guild.BanEntry')
T = TypeVar('T')

__all__: Tuple[str, ...] = (
    'TargetVerifier',
    'BanEntryConverter',
    'ChannelVerifier',
    'MissingArguments',
    'DuplicateArgument',
    'UnorderedArguments',
)
    

class TargetVerifier(commands.Converter[T]):
    """Used to verify a traget is permitted to perform
    an action upon another target.
            
    In this use case, the target is being checked by 
    :attr:`DuckBot.author` for an operation.
    
    .. code-block:: python3
    
        @commands.command()
        async def ban(self, ctx: DuckContext, member: TargetVerifier(discord.Member, discord.User), *, reason: str = '...'):
            await member.ban(reason=reason)
    
    Attributes
    ----------
    fail_if_not_upgrade: :class:`bool`
        If ``True``, the command will fail if the target cannot be upgraded from
        a :class:`~discord.User` to a :class:`~discord.Member`. For more information,
        check out :meth:`can_execute_action`.
    """
    __slots__: Tuple[str, ...] = (
        '_targets',
        'fail_if_not_upgrade',
        '_cs_converter_mapping',
    )
    
    def __init__(self, *targets: Type[T], fail_if_not_upgrade: bool = True) -> None:
        self._targets: Tuple[Type[T]] = targets
        self.fail_if_not_upgrade: bool = fail_if_not_upgrade
        
    @discord.utils.cached_slot_property('_cs_converter_mapping')
    def converter_mapping(self) -> Dict[Type[T], Type[commands.Converter]]:
        """Dict[Type[T], Type[:class:`commands.Converter`]]: A mapping of converters to use for conversion."""
        return {
            discord.Member: commands.MemberConverter,
            discord.User: commands.UserConverter
        }
            
    async def convert(self, ctx: DuckContext, argument: str) -> Union[discord.Member, discord.User]:
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
        # We need to determine what we're trying to upgrade to.
        # To do that, let's check the targets attribute.
        target = None
        if len(self._targets) == 1:
            converter = self.converter_mapping[self._targets[0]]
            target = await converter().convert(ctx, argument)

        else:
            # We need to this manually. It's both discord.Member and discord.User
            if ctx.guild:
                try:
                    target = await commands.MemberConverter().convert(ctx, argument)
                except:
                    pass
            
            if not target:
                target = await commands.UserConverter().convert(ctx, argument)
        
        # Then check if the operation is legal
        await can_execute_action(ctx, target, fail_if_not_upgrade=self.fail_if_not_upgrade)
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
        await ctx.trigger_typing()
        
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
                    return cls(user=entry.user, reason=entry.reason)  # type: ignore
            
            _find_entitiy = lambda u: str(u.user).lower() == argument.lower() or str(u.user.name).lower() == argument.lower()
            
            # we search by username now.
            ban_list = await guild.bans()
            entity = discord.utils.find(_find_entitiy, ban_list)
            
            if entity is None:
                raise commands.BadArgument('This member has not been banned before.')
            
            return cls(user=entity.user, reason=entity.reason)  # type: ignore  # CHAI STOP REMOVING THIS >:(

    def __repr__(self) -> str:
        return '<BanEntryConverter user={0.user} ({0.user.id}) reason={0.reason}>'
    
    def __str__(self) -> str:
        return '{0.user} ({0.user.id})'.format(self)


# Lel so bad :weary:
class VerifyChannelMeta(type):

    @overload
    def __getitem__(cls, item: Type[discord.abc.GuildChannel]) -> TargetVerifier:
        ...

    @overload
    def __getitem__(cls, item: Type[Tuple[discord.abc.GuildChannel, ...]]) -> TargetVerifier:
        ...

    def __getitem__(cls, item) -> TargetVerifier:
        return cls(item)


class ChannelVerifier(metaclass=VerifyChannelMeta):
    """Used to verify if a channel is accessible.

    .. code-block:: python3

        @commands.command()
        async def send(self, ctx: DuckContext, channel: AccessibleChannel[discord.TextChannel, discord.VoiceChannel], *, text: str = '...'):
            await channel.send(text)
    """
    __slots__: Tuple[str, ...] = (
        '_targets',
        '_cs_converter_mapping',
    )

    def __init__(
            self,
            targets: Type[
                Union[
                    Union[discord.Member, discord.User],
                    Tuple[Union[discord.Member, discord.User], ...]
                ]
            ],
    ) -> None:
        self._targets = targets

    @discord.utils.cached_slot_property('_cs_converter_mapping')
    def converter_mapping(self) -> Dict[Type[discord.abc.GuildChannel], Type[commands.Converter]]:
        """Dict[Type[:class:`~discord.abc.GuildChannel`], Type[:class:`commands.Converter`]]: A mapping of converters to use for conversion."""
        return {
            discord.abc.GuildChannel: commands.GuildChannelConverter,
            discord.TextChannel: commands.TextChannelConverter,
            discord.VoiceChannel: commands.VoiceChannelConverter,
            discord.CategoryChannel: commands.CategoryChannelConverter,
            discord.StageChannel: commands.StageChannelConverter,
            discord.Thread: commands.ThreadConverter,
            discord.StoreChannel: commands.StoreChannelConverter,
        }

    async def convert(self, ctx: DuckContext, argument: str) -> typing.Optional[discord.abc.GuildChannel]:
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
        try:
            if issubclass(self._targets, discord.abc.GuildChannel):
                # We upgrade to a member or user based upon the guild in this case.
                converter = self.converter_mapping[self._targets]
            else:
                # Something goofed here
                raise RuntimeError(f'Invalid target type {self._targets} ({type(self._targets)})')
        except TypeError:
            # it's multiple arguments, we must manually convert and check.
            target = await commands.GuildChannelConverter().convert(ctx, argument)
            if not isinstance(target, self._targets):
                if self._targets[-1] is discord.Thread:
                    error = commands.ThreadNotFound
                else:
                    error = commands.ChannelNotFound
                raise error(argument)
        else:
            target = await converter().convert(ctx, argument)

        # Then check if the operation is legal
        verified = await discord.utils.maybe_coroutine(self.verify_target, ctx, target)
        if verified is True:
            return target
        elif verified is None:
            return None
        raise commands.BadArgument(f'You are missing the required permissions do that in #{target}')

    def verify_target(self, ctx: DuckContext, target: discord.abc.GuildChannel) -> bool:
        """
        Verify that the target is permitted to perform the action.
        This function must return a :class:`bool`, `None`, or raise
        an error. (It is recommended that this error be a subclass of
        :class:`commands.BadArgument` or :class:`commands.CommandError`)

        This function can be a coroutine.

        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context of the command.
        target: :class:`discord.abc.GuildChannel`
            The target to verify.

        Returns
        -------
        Optional[:class:`bool`]
            If this method returns True, the object will be returned.
            If this method returns None, it will return None.
            If this method returns False, it will raise an error.
        """
        raise NotImplementedError('Derived classes need to implement this.')


# Converter made by Stella#2000 (591135329117798400) from the d.py server :D
# I was going to make my own but this is actually good so why not use it? lol

class Argument:
    def __init__(self, *, name: str, type: Type[type]) -> None:
        self.name = name
        self.type = type


class DuplicateArgument(DuckBotCommandError):
    pass


class MissingArguments(DuckBotCommandError):
    def __init__(self, arguments) -> None:
        *every, last = map(lambda v: v.name, arguments)
        if every:
            message = f"{', '.join(every)} and {last}"
        else:
            message = last
        super().__init__(f"The following arguments are missing: {message}")


class _UnorderedArg(type):
    __commands_args__ = typing.ClassVar[typing.Dict[str, Argument]]

    def __new__(mcs, name, bases, attrs) -> Self:
        arguments = attrs.get("__annotations__", {})
        for key, anno in arguments.items():
            arguments[key] = Argument(name=key, type=anno)

        mcs.__commands_args__ = arguments
        return super().__new__(mcs, name, bases, attrs)


class UnorderedArguments(metaclass=_UnorderedArg):
    @staticmethod
    async def try_convert(cls: UnorderedArguments, ctx: DuckContext, argument: Argument, value: str) -> None:
        converted = await commands.run_converters(ctx, argument.type, value, ctx.current_parameter)
        name = argument.name
        if getattr(cls, name, MISSING) is not MISSING:
            raise DuplicateArgument(f'Conflicting values at {name!r}.')

        setattr(cls, name, converted)

    @classmethod
    async def convert(cls, ctx: DuckContext, argument: str) -> Self:
        view = StringView(argument)
        unordered = cls.__new__(cls)
        converters = cls.__commands_args__.copy()
        values = list(converters.values())

        while not view.eof:
            view.skip_ws()
            argument = view.get_quoted_word()
            to_remove = MISSING
            for converter in values:
                try:
                    await cls.try_convert(unordered, ctx, converter, argument)
                except DuplicateArgument as e:
                    raise e from None
                except commands.CommandError:
                    pass  # ignored
                else:
                    to_remove = converter
                    break

            if to_remove is MISSING:
                raise MissingArguments(values)

            values.remove(to_remove)

            if values and view.eof:
                raise MissingArguments(values)

            if not values and not view.eof:
                break

        return unordered


from __future__ import annotations

import re
from numpydoc.docscrape import NumpyDocString, Parameter
from typing import (
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Mapping,
    TypeVar,
    Any,
    Generic,
    Union,
)
from typing_extensions import ParamSpec, Self, Concatenate

import discord
from discord.ext import commands
from discord.ext.commands.core import hooked_wrapped_callback
from discord.ext.commands._types import CogT
from discord.ext.commands._types import ContextT, Coro
from discord.utils import MISSING

from .autocomplete import AutoComplete
from .context import DuckContext
from utils.time import human_join

T = TypeVar('T')
P = ParamSpec('P')

AutocompleteCallbackTypeReturn = Union[Iterable[Any], Awaitable[Iterable[Any]]]
RestrictedType = Union[Iterable[Any], Callable[[DuckContext], AutocompleteCallbackTypeReturn]]

AutocompleteCallbackType = Union[
    Callable[[CogT, ContextT, str], AutocompleteCallbackTypeReturn],
    Callable[[ContextT, str], AutocompleteCallbackTypeReturn],
]

NUMPY_ITEM_REGEX = re.compile(r'(?P<type>\:[a-z]{1,}\:)\`(?P<name>[a-z\.]{1,})\`', flags=re.IGNORECASE)
DOC_HEADER_REGEX = re.compile(r'\|coro\|', flags=re.IGNORECASE)


def _subber(match: re.Match) -> str:
    _, name = match.groups()
    return name


class CustomDocString(NumpyDocString):
    sections = {
        "Signature": "",
        "Summary": [""],
        "Extended Summary": [],
        "Parameters": [],
        "Notes": "",
        "Flags": [],
        "References": "",
        "Examples": "",
    }


@discord.utils.copy_doc(commands.Command)
class DuckCommand(commands.Command, Generic[CogT, P, T]):
    """Implements the front end DuckCommand functionality. This subclasses
    :class:`~commands.Command` to add some fun utility functions.

    Attributes
    ----------
    autocompletes: Dict[:class:`str`, :class:`AutoComplete`]
        A mapping of parameter name to autocomplete objects. This is so
        autocomplete can be added to the command.
    """

    def __init__(
        self,
        func: Union[
            Callable[Concatenate[CogT, ContextT, P], Coro[T]],
            Callable[Concatenate[ContextT, P], Coro[T]],
        ],
        /,
        **kwargs: Any,
    ) -> None:
        super().__init__(func, **kwargs)  # type: ignore
        self.ignored_exceptions: tuple[type[Exception]] = kwargs.get('ignored_exceptions', tuple())
        self.autocompletes: Dict[str, AutoComplete] = {}

    @property
    def help_mapping(self) -> Mapping[str, str]:
        """Parses the :class:`DuckCommand`'s help text into a mapping
        that can be used to generate a help embed or give the user more
        inforamtion about the command.

        Returns
        -------
            Mapping[:class:`str`, :class:`str`]
        """
        mapping = {}

        help_doc = self.help
        if not help_doc:
            return mapping

        help_doc = NUMPY_ITEM_REGEX.sub(_subber, help_doc)
        help_doc = DOC_HEADER_REGEX.sub('', help_doc).lstrip()

        processed = CustomDocString(help_doc)
        for name, value in processed.items():
            if not value or (isinstance(value, list) and not value[0]) or value == '':
                continue

            if isinstance(value, list) and isinstance(value[0], Parameter):
                fmt = []
                for item in value:
                    fmt.append('- `{0}`: {1}'.format(item.name, ' '.join(item.desc)))

                value = '\n'.join(fmt)
            elif isinstance(value, list):
                value = '\n'.join(value)

            mapping[name.lower()] = value

        def getter(pair):
            key = pair[0].lower()
            if key == 'summary':
                return 0
            elif key == 'extended summary':
                return 1
            else:
                return help_doc.lower().index(key)

        return dict(sorted(mapping.items(), key=getter))

    @property
    def help_embed(self) -> discord.Embed:
        """:class:`discord.Embed`: Creates a help embed for the command."""
        embed = discord.Embed(
            title=self.qualified_name,
        )

        for key, value in self.help_mapping.items():
            embed.add_field(name=key.title(), value=value, inline=False)

        embed.add_field(name='How to use', value=f'`db.{self.qualified_name} {self.signature}'.strip() + '`')

        if commands := getattr(self, 'commands', None):
            embed.add_field(
                name='Subcommands', value=human_join([f'`{c.name}`' for c in commands], final='and'), inline=False
            )

        if isinstance(self, DuckGroup):
            embed.set_footer(text=f'Select a subcommand to get more information about it.')

        return embed

    def _ensure_assignment_on_copy(self, other: Self) -> Self:
        other = super()._ensure_assignment_on_copy(other)
        other.autocompletes = self.autocompletes
        return other

    def add_autocomplete(
        self,
        /,
        *,
        callback: AutocompleteCallbackType,
        param: str,
    ) -> AutoComplete:
        """Adds an autocomplete callback to the command for a given parameter.

        Parameters
        ----------
        callback: Callable
            The callback to be used for the parameter. This should take
            only two parameters, `ctx` and `value`.
        param: :class:`str`
            The name of the parameter to add the autocomplete to.

        Returns
        -------
        :class:`AutoComplete`
            The autocomplete object that was created.

        Raises
        ------
        ValueError
            The parameter is already assigned an autocomplete, or
            the parameter is not in the list of parameters registered to the
            command.
        """
        if param in self.autocompletes:
            raise ValueError(f'{param} is already autocompleted')
        if param not in self.clean_params:
            raise ValueError(f'{param} is not a valid parameter')

        new = AutoComplete(callback, param)
        self.autocompletes[param] = new
        return new

    def autocomplete(self, param: str) -> Callable[[AutocompleteCallbackType], AutocompleteCallbackType]:
        """A decorator to register a callback as an autocomplete for a parameter.

        .. code-block:: python3

            @commands.command()
            async def foo(self, ctx: DuckContext, argument: str) -> None:
                return await ctx.send(f'You selected {argument!}')

            @foo.autocomplete('argument')
            async def foo_autocomplete(ctx: DuckContext, value: str) -> Iterable[str]:
                data: Tuple[str, ...] = await self.bot.get_some_data(ctx.guild.id)
                return data

        Parameters
        ----------
        param: :class:`str`
            The name of the parameter to add the autocomplete to.
        """

        def decorator(callback: AutocompleteCallbackType) -> AutocompleteCallbackType:
            self.add_autocomplete(callback=callback, param=param)
            return callback

        return decorator

    async def invoke(self, ctx: DuckContext, /) -> None:
        """|coro|

        An internal helper used to invoke the command under a given context. This should
        not be called by the user, but can be used if needed.

        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context to invoke the command under.
        """
        await self.prepare(ctx)

        original_args = ctx.args[: 2 if self.cog else 1 :]
        args = ctx.args[2 if self.cog else 1 :]

        kwargs = ctx.kwargs
        parameters = self.clean_params

        constricted_args = [ctx] if not self.cog else [self.cog, ctx]
        for index, (name, parameter) in enumerate(parameters.items()):
            if not (autocomplete := self.autocompletes.get(name)):
                continue

            # Let's find the current value based upon the parameter
            if parameter.kind is parameter.POSITIONAL_OR_KEYWORD:
                value = args[index]

                constricted_args.append(value)
                constricted = await discord.utils.maybe_coroutine(autocomplete.callback, *constricted_args)

                if value not in constricted:
                    try:
                        new_value = await autocomplete.prompt_correct_input(
                            ctx, parameter, value=value, constricted=constricted
                        )
                    except commands.CommandError as exc:
                        return await self.dispatch_error(ctx, exc)

                    args[index] = new_value
            elif parameter.kind is parameter.KEYWORD_ONLY:
                value = kwargs[name]

                constricted_args.append(value)
                constricted = await discord.utils.maybe_coroutine(autocomplete.callback, *constricted_args)

                if value not in constricted:
                    try:
                        new_value = await autocomplete.prompt_correct_input(
                            ctx, parameter, value=value, constricted=constricted
                        )
                    except commands.CommandError as exc:
                        return await self.dispatch_error(ctx, exc)

                    kwargs[name] = new_value
            else:
                continue

        ctx.args = original_args + args
        ctx.kwargs = kwargs

        # terminate the invoked_subcommand chain.
        # since we're in a regular command (and not a group) then
        # the invoked subcommand is None.
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        injected = hooked_wrapped_callback(self, ctx, self.callback)
        await injected(*ctx.args, **ctx.kwargs)


# Due to autocomplete, we can't directly inherit from `commands.Group`
# because calling super().invoke won't go to the correct method.
# I'm going to patch it like this for now and search for better
# optimizations later.
@discord.utils.copy_doc(commands.Group)
class DuckGroup(commands.GroupMixin[CogT], DuckCommand[CogT, P, T]):
    """The front end implementation of a group command.

    This intherits both :class:`DuckCommand` and :class:`~commands.GroupMixin` to add
    functionality of command management.
    """

    def __init__(self, *args: Any, **attrs: Any) -> None:
        self.invoke_without_command: bool = attrs.pop('invoke_without_command', False)
        super().__init__(*args, **attrs)

    def command(self, *args: Any, **kwargs: Any) -> Callable[..., DuckCommand]:
        """
        Register a function as a :class:`DuckCommand`.

        Parameters
        ----------
        name: Optional[:class:`str`]
            The name of the command, or ``None`` to use the function's name.
        description: Optional[:class:`str`]
            The description of the command, or ``None`` to use the function's docstring.
        brief: Optional[:class:`str`]
            The brief description of the command, or ``None`` to use the first line of the function's docstring.
        aliases: Optional[Iterable[:class:`str`]]
            The aliases of the command, or ``None`` to use the function's name.
        **attrs: Any
            The keyword arguments to pass to the :class:`DuckCommand`.
        """

        def wrapped(func) -> DuckCommand:
            kwargs.setdefault('parent', self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapped

    def group(self, *args: Any, **kwargs: Any) -> Callable[..., DuckGroup]:
        """
        Register a function as a :class:`DuckGroup`.

        Parameters
        ----------
        name: Optional[:class:`str`]
            The name of the command, or ``None`` to use the function's name.
        description: Optional[:class:`str`]
            The description of the command, or ``None`` to use the function's docstring.
        brief: Optional[:class:`str`]
            The brief description of the command, or ``None`` to use the first line of the function's docstring.
        aliases: Optional[Iterable[:class:`str`]]
            The aliases of the command, or ``None`` to use the function's name.
        **attrs: Any
            The keyword arguments to pass to the :class:`DuckGroup`.
        """

        def wrapped(func) -> DuckGroup:
            kwargs.setdefault('parent', self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapped

    @discord.utils.copy_doc(DuckCommand.invoke)
    async def invoke(self, ctx: DuckContext, /) -> None:
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        early_invoke = not self.invoke_without_command
        if early_invoke:
            await self.prepare(ctx)

        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()

        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)

        if early_invoke:
            injected = hooked_wrapped_callback(self, ctx, self.callback)
            await injected(*ctx.args, **ctx.kwargs)

        ctx.invoked_parents.append(ctx.invoked_with)  # type: ignore

        if trigger and ctx.invoked_subcommand:
            ctx.invoked_with = trigger
            await ctx.invoked_subcommand.invoke(ctx)
        elif not early_invoke:
            # undo the trigger parsing
            view.index = previous
            view.previous = previous
            await super().invoke(ctx)

    @discord.utils.copy_doc(DuckCommand.reinvoke)
    async def reinvoke(self, ctx: DuckContext, /, *, call_hooks: bool = False) -> None:
        ctx.invoked_subcommand = None
        early_invoke = not self.invoke_without_command
        if early_invoke:
            ctx.command = self
            await self._parse_arguments(ctx)

            if call_hooks:
                await self.call_before_hooks(ctx)

        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()

        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)

        if early_invoke:
            try:
                await self.callback(*ctx.args, **ctx.kwargs)
            except:
                ctx.command_failed = True
                raise
            finally:
                if call_hooks:
                    await self.call_after_hooks(ctx)

        ctx.invoked_parents.append(ctx.invoked_with)  # type: ignore

        if trigger and ctx.invoked_subcommand:
            ctx.invoked_with = trigger
            await ctx.invoked_subcommand.reinvoke(ctx, call_hooks=call_hooks)
        elif not early_invoke:
            # undo the trigger parsing
            view.index = previous
            view.previous = previous
            await super().reinvoke(ctx, call_hooks=call_hooks)


@discord.utils.copy_doc(commands.HybridCommand)
class DuckHybridCommand(commands.HybridCommand, DuckCommand):
    def autocomplete(self, name: str, slash: bool = True, message: bool = False):
        if slash is True:
            return commands.HybridCommand.autocomplete(self, name)
        elif message is True:
            return DuckCommand.autocomplete(self, name)


@discord.utils.copy_doc(commands.HybridGroup)
class DuckHybridGroup(commands.HybridGroup, DuckGroup):
    def autocomplete(self, name: str, slash: bool = True, message: bool = False):
        if slash is True:
            return commands.HybridGroup.autocomplete(self, name)
        elif message is True:
            return DuckGroup.autocomplete(self, name)

    def command(self, *args: Any, hybrid: bool = True, **kwargs: Any) -> Callable[..., DuckHybridCommand]:
        def wrapped(func) -> DuckHybridCommand:
            kwargs.setdefault('parent', self)
            result = command(*args, hybrid=True, with_app_command=hybrid, **kwargs)(func)
            self.add_command(result)  # type: ignore
            return result  # type: ignore

        return wrapped

    def group(self, *args: Any, hybrid: bool = True, **kwargs: Any) -> Callable[..., DuckHybridGroup]:

        def wrapped(func) -> DuckHybridGroup:
            kwargs.setdefault('parent', self)
            result = group(*args, hybrid=True, with_app_command=hybrid, **kwargs)(func)
            self.add_command(result)  # type: ignore
            return result  # type: ignore

        return wrapped


def command(
    name: str = MISSING,
    description: str = MISSING,
    brief: str = MISSING,
    aliases: Iterable[str] = MISSING,
    hybrid: bool = False,
    **attrs: Any,
) -> Callable[..., DuckCommand | DuckHybridCommand]:
    """
    Register a function as a :class:`DuckCommand`.

    Parameters
    ----------
    name: Optional[:class:`str`]
        The name of the command, or ``None`` to use the function's name.
    description: Optional[:class:`str`]
        The description of the command, or ``None`` to use the function's docstring.
    brief: Optional[:class:`str`]
        The brief description of the command, or ``None`` to use the first line of the function's docstring.
    aliases: Optional[Iterable[:class:`str`]]
        The aliases of the command, or ``None`` to use the function's name.
    **attrs: Any
        The keyword arguments to pass to the :class:`DuckCommand`.
    """
    cls = DuckCommand if hybrid is False else DuckHybridCommand

    def decorator(func) -> DuckCommand:
        if isinstance(func, DuckCommand):
            raise TypeError('Callback is already a command.')

        kwargs = {}
        kwargs.update(attrs)
        if name is not MISSING:
            kwargs['name'] = name
        if description is not MISSING:
            kwargs['description'] = description
        if brief is not MISSING:
            kwargs['brief'] = brief
        if aliases is not MISSING:
            kwargs['aliases'] = aliases

        return cls(func, **kwargs)

    return decorator


def group(
    name: str = MISSING,
    description: str = MISSING,
    brief: str = MISSING,
    aliases: Iterable[str] = MISSING,
    hybrid: bool = False,
    fallback: str | None = None,
    invoke_without_command: bool = True,
    **attrs: Any,
) -> Callable[..., DuckGroup | DuckHybridGroup]:
    """
    Register a function as a :class:`DuckGroup`.

    Parameters
    ----------
    name: Optional[:class:`str`]
        The name of the command, or ``None`` to use the function's name.
    description: Optional[:class:`str`]
        The description of the command, or ``None`` to use the function's docstring.
    brief: Optional[:class:`str`]
        The brief description of the command, or ``None`` to use the first line of the function's docstring.
    aliases: Optional[Iterable[:class:`str`]]
        The aliases of the command, or ``None`` to use the function's name.
    **attrs: Any
        The keyword arguments to pass to the :class:`DuckCommand`.
    """
    cls = DuckGroup if hybrid is False else DuckHybridGroup

    def decorator(func) -> DuckGroup:
        if isinstance(func, DuckGroup):
            raise TypeError('Callback is already a command.')

        kwargs: Dict[str, Any] = {'invoke_without_command': invoke_without_command}
        kwargs.update(attrs)
        if name is not MISSING:
            kwargs['name'] = name
        if description is not MISSING:
            kwargs['description'] = description
        if brief is not MISSING:
            kwargs['brief'] = brief
        if aliases is not MISSING:
            kwargs['aliases'] = aliases
        if fallback is not None:
            if hybrid is False:
                raise TypeError('Fallback is only allowed for hybrid commands.')
            kwargs['fallback'] = fallback

        return cls(func, **kwargs)

    return decorator

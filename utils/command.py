from __future__ import annotations

import re
from numpydoc.docscrape import (
    NumpyDocString as process_doc,
    Parameter
)
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Concatenate,
    Dict,
    Iterable,
    List,
    Mapping,
    TypeVar,
    Any,
    Generic,
    TypeVar,
    Union,
)
from typing_extensions import ParamSpec, Self

import discord
from discord.ext import commands
from discord.ext.commands.core import CogT, hooked_wrapped_callback
from discord.ext.commands._types import ContextT, Coro
from discord.utils import MISSING

from .autocomplete import AutoComplete
from .context import DuckContext
from .time import human_join

if TYPE_CHECKING:
    from bot import DuckBot

T = TypeVar('T')
P = ParamSpec('P')
RestrictedType = Union[Iterable[Any], Callable[[DuckContext], Union[Iterable[Any], Awaitable[Iterable[Any]]]]]

NUMPY_ITEM_REGEX = re.compile(r'(?P<type>\:[a-z]{1,}\:)\`(?P<name>[a-z\.]{1,})\`', flags=re.IGNORECASE)

def _subber(match: re.Match) -> str:
    _, name = match.groups()
    return name


@discord.utils.copy_doc(commands.Command)
class DuckCommand(commands.Command, Generic[P, T]):

    def __init__(
		self,
		func: Union[
			Callable[Concatenate[CogT, ContextT, P], Coro[T]],
			Callable[Concatenate[ContextT, P], Coro[T]],
		],
		/,
		**kwargs: Any
    ) -> None:
        super().__init__(func, **kwargs)
        self.autocompletes: Dict[str, AutoComplete] = {}
        
    @property
    def help_mapping(self) -> Mapping[str, List[str]]:
        mapping = {}
        
        help_doc = command.help
        if not help_doc:
            return mapping
        
        NUMPY_ITEM_REGEX.sub(_subber, help_doc)
        
        processed = process_doc(help_doc)
        for name, value in processed._parsed_data.items():
            if not value or (isinstance(value, list) and not value[0]) or value == '':
                continue
            
            if isinstance(value, list) and isinstance(value[0], Parameter):
                fmt = []
                for item in value:
                    fmt.append('`{0}`: {1}'.format(item.name, ' '.join(item.desc)))
                
                value = '\n\n'.join(fmt)
            elif isinstance(value, list):            
                value = ' '.join(value)
            
            mapping[name.lower()] = value
        
        return mapping
    
    @property
    def help_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=group.qualified_name,
            description=group.help,
        )
        
        for key, value in self.help_mapping.items():
            embed.add_field(name=key.title(), value=value)
        
        embed.add_field(name='How to use', value=f'`db.{self.qualified_name} {self.signature}'.strip() + '`')
        
        if (commands := getattr(self, 'commands', None)):
            embed.add_field(name='Subcommands', value=human_join([f'`{c.name}`' for c in commands], final='and'), inline=False)
        embed.set_footer(text=f'Select a subcommand to get more information about it.')
        
        return embed
        
    def _ensure_assignment_on_copy(self, other: Self) -> Self:
        other = super()._ensure_assignment_on_copy(other)
        other.autocompletes = self.autocompletes
        return other

    def add_autocomplete(
		self,
		func: Callable[..., Any],
		param_name: str,
    ) -> AutoComplete:
        if param_name in self.autocompletes:
            raise ValueError(f'{param_name} is already autocompleted')
        if param_name not in self.clean_params:
            raise ValueError(f'{param_name} is not a valid parameter')

        new = AutoComplete(func, param_name)
        self.autocompletes[param_name] = new
        return new

    def autocomplete(self, param_name: str):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_autocomplete(func, param_name)
            return func

        return decorator

    async def invoke(self, ctx: DuckContext[DuckBot], /) -> None:
        await self.prepare(ctx)

        original_args = ctx.args[:2 if self.cog else 1:]
        args = ctx.args[2 if self.cog else 1:]

        kwargs = ctx.kwargs
        parameters = self.clean_params

        constricted_args = [ctx] if not self.cog else [self.cog, ctx]
        for index, (name, parameter) in enumerate(parameters.items()):
            if not (autocomplete := self.autocompletes.get(name)):
                continue

            # type: ignore # fuck you pyright
            constricted = await discord.utils.maybe_coroutine(autocomplete.callback, *constricted_args)

            # Let's find the current value based upon the parameter
            if parameter.kind is parameter.POSITIONAL_OR_KEYWORD:
                value = args[index]

                if value not in constricted:
                    try:
                        new_value = await autocomplete.prompt_correct_input(ctx, parameter, value=value, constricted=constricted)
                    except commands.CommandError as exc:
                        return await self.dispatch_error(ctx, exc)

                    args[index] = new_value
            elif parameter.kind is parameter.KEYWORD_ONLY:
                value = kwargs[name]

                if value not in constricted:
                    try:
                        new_value = await autocomplete.prompt_correct_input(ctx, parameter, value=value, constricted=constricted)
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
        await injected(*ctx.args, **ctx.kwargs)  # type: ignore


@discord.utils.copy_doc(commands.Group)
class DuckGroup(commands.GroupMixin, DuckCommand): # NOTE: some typehints are lost here, eventually add them back
    def __init__(self, *args: Any, **attrs: Any) -> None:
        self.invoke_without_command: bool = attrs.pop('invoke_without_command', False)
        super().__init__(*args, **attrs)
    
    def command(self, *args, **kwargs) -> Callable[..., DuckCommand]:
        def wrapped(func) -> DuckCommand:
            kwargs.setdefault('parent', self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapped

    def group(self, *args, **kwargs) -> Callable[..., DuckGroup]:
        def wrapped(func) -> DuckGroup:
            kwargs.setdefault('parent', self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapped


def command(
	name: str = MISSING,
	description: str = MISSING,
	brief: str = MISSING,
	aliases: Iterable[str] = MISSING,
	**attrs: Any
) -> Callable[..., DuckCommand]:
    cls = DuckCommand

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
	**attrs: Any
) -> Callable[..., DuckGroup]:
    cls = DuckGroup

    def decorator(func) -> DuckGroup:
        if isinstance(func, DuckGroup):
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

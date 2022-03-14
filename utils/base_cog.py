from __future__ import annotations

import inspect

from typing import (
    TYPE_CHECKING,
    Optional,
    Type,
    Tuple,
    Dict,
    List,
    Any,
    Union
)

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

from discord.ext import commands
from discord import app_commands

from .errors import *
from .command import DuckCommand

if TYPE_CHECKING:
    from typing_extensions import Self
    from bot import DuckBot

__all__: Tuple[str, ...] = (
    'DuckCog',
)

_BaseCommand = DuckCommand

class DuckCogMeta(type):
    """A metaclass for defining a cog.
    Note that you should probably not use this directly. It is exposed
    purely for documentation purposes along with making custom metaclasses to intermix
    with other metaclasses such as the :class:`abc.ABCMeta` metaclass.
    For example, to create an abstract cog mixin class, the following would be done.
    .. code-block:: python3
        import abc
        class CogABCMeta(commands.CogMeta, abc.ABCMeta):
            pass
        class SomeMixin(metaclass=abc.ABCMeta):
            pass
        class SomeCogMixin(SomeMixin, commands.Cog, metaclass=CogABCMeta):
            pass
    .. note::
        When passing an attribute of a metaclass that is documented below, note
        that you must pass it as a keyword-only argument to the class creation
        like the following example:
        .. code-block:: python3
            class MyCog(commands.Cog, name='My Cog'):
                pass
    Attributes
    -----------
    name: :class:`str`
        The cog name. By default, it is the name of the class with no modification.
    description: :class:`str`
        The cog description. By default, it is the cleaned docstring of the class.
        .. versionadded:: 1.6
    command_attrs: :class:`dict`
        A list of attributes to apply to every command inside this cog. The dictionary
        is passed into the :class:`Command` options at ``__init__``.
        If you specify attributes inside the command attribute in the class, it will
        override the one specified inside this attribute. For example:
        .. code-block:: python3
            class MyCog(commands.Cog, command_attrs=dict(hidden=True)):
                @commands.command()
                async def foo(self, ctx):
                    pass # hidden -> True
                @commands.command(hidden=False)
                async def bar(self, ctx):
                    pass # hidden -> False
    """

    __cog_name__: str
    __cog_settings__: Dict[str, Any]
    __cog_commands__: List[DuckCommand]
    __cog_is_app_commands_group__: bool
    __cog_app_commands__: List[Union[app_commands.Group, app_commands.Command[Any, ..., Any]]]
    __cog_listeners__: List[Tuple[str, str]]

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        name, bases, attrs = args
        attrs['__cog_name__'] = kwargs.get('name', name)
        attrs['__cog_settings__'] = kwargs.pop('command_attrs', {})
        attrs['__cog_is_app_commands_group__'] = is_parent = app_commands.Group in bases

        description = kwargs.get('description', None)
        if description is None:
            description = inspect.cleandoc(attrs.get('__doc__', ''))
        attrs['__cog_description__'] = description

        if is_parent:
            attrs['__discord_app_commands_skip_init_binding__'] = True
            # This is hacky, but it signals the Group not to process this info.
            # It's overridden later.
            attrs['__discord_app_commands_group_children__'] = True
        else:
            # Remove the extraneous keyword arguments we're using
            kwargs.pop('name', None)
            kwargs.pop('description', None)

        commands = {}
        cog_app_commands = {}
        listeners = {}
        no_bot_cog = 'Commands or listeners must not start with cog_ or bot_ (in method {0.__name__}.{1})'

        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in commands:
                    del commands[elem]
                if elem in listeners:
                    del listeners[elem]

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if isinstance(value, _BaseCommand):
                    if is_static_method:
                        raise TypeError(f'Command in method {base}.{elem!r} must not be staticmethod.')
                    if elem.startswith(('cog_', 'bot_')):
                        raise TypeError(no_bot_cog.format(base, elem))
                    commands[elem] = value
                elif isinstance(value, (app_commands.Group, app_commands.Command)) and value.parent is None:
                    cog_app_commands[elem] = value
                elif inspect.iscoroutinefunction(value):
                    try:
                        getattr(value, '__cog_listener__')
                    except AttributeError:
                        continue
                    else:
                        if elem.startswith(('cog_', 'bot_')):
                            raise TypeError(no_bot_cog.format(base, elem))
                        listeners[elem] = value

        new_cls.__cog_commands__ = list(commands.values())  # this will be copied in Cog.__new__
        new_cls.__cog_app_commands__ = list(cog_app_commands.values())

        if is_parent:
            # Prefill the app commands for the Group as well..
            # The type checker doesn't like runtime attribute modification and this one's
            # optional so it can't be cheesed.
            new_cls.__discord_app_commands_group_children__ = new_cls.__cog_app_commands__  # type: ignore

        listeners_as_list = []
        for listener in listeners.values():
            for listener_name in listener.__cog_listener_names__:
                # I use __name__ instead of just storing the value so I can inject
                # the self attribute when the time comes to add them to the bot
                listeners_as_list.append((listener_name, listener.__name__))

        new_cls.__cog_listeners__ = listeners_as_list
        return new_cls

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args)

    @classmethod
    def qualified_name(cls) -> str:
        return cls.__cog_name__

class DuckCog(commands.Cog):
    """The base class for all DuckBot cogs.

    Attributes
    ----------
    bot: DuckBot
        The bot instance.
    """
    if TYPE_CHECKING:
        emoji: Optional[str]
        brief: Optional[str]

    #__metaclass__: DuckCogMeta = DuckCogMeta

    __slots__: Tuple[str, ...] = (
        'bot',
    )

    def __init_subclass__(cls: Type[DuckCog], **kwargs) -> None:
        """
        This is called when a subclass is created.
        Its purpose is to add parameters to the cog
        that will later be used in the help command.
        """
        cls.emoji = kwargs.pop('emoji', None)
        cls.brief = kwargs.pop('brief', None)
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: DuckBot) -> None:
        self.bot: DuckBot = bot

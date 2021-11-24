from __future__ import annotations

import asyncio
import inspect
import json
from collections import defaultdict

import discord, discord.channel, discord.http, discord.state
from discord.ext import commands
from discord.utils import MISSING

from typing import Coroutine, TypeVar, Union, get_args, get_origin, overload, Generic, TYPE_CHECKING

BotT = TypeVar("BotT", bound='Bot')
CtxT = TypeVar("CtxT", bound='Context')
CogT = TypeVar("CogT", bound='ApplicationCog')
NumT = Union[int, float]

__all__ = ['describe', 'SlashCommand', 'ApplicationCog', 'Range', 'Context', 'Bot', 'slash_command', 'message_command',
           'user_command']

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, ClassVar
    from typing_extensions import Concatenate, ParamSpec

    CmdP = ParamSpec("CmdP")
    CmdT = Callable[[Concatenate[CogT, CtxT, CmdP]], Awaitable[Any]]
    MsgCmdT = Callable[[CogT, CtxT, discord.Message], Awaitable[Any]]
    UsrCmdT = Callable[[CogT, CtxT, discord.Member], Awaitable[Any]]
    CtxMnT = Union[MsgCmdT, UsrCmdT]

    RngT = TypeVar("RngT", bound='Range')

command_type_map: dict[type[Any], int] = {
    str: 3,
    int: 4,
    bool: 5,
    discord.User: 6,
    discord.Member: 6,
    discord.TextChannel: 7,
    discord.VoiceChannel: 7,
    discord.CategoryChannel: 7,
    discord.Role: 8,
    float: 10
}

channel_filter: dict[type[discord.abc.GuildChannel], int] = {
    discord.TextChannel: 0,
    discord.VoiceChannel: 2,
    discord.CategoryChannel: 4
}


def describe(**kwargs: str) -> Callable[[SlashCommand | CmdT], SlashCommand | CmdT]:
    """
    Sets the description for the specified parameters of the slash command. Sample usage:
    ```python
    @slash_util.slash_command()
    @describe(channel="The channel to ping")
    async def mention(self, ctx: slash_util.Context, channel: discord.TextChannel):
        await ctx.send(f'{channel.mention}')
    ```
    If this decorator is not used, parameter descriptions will be set to "No description provided." instead."""

    def _inner(cmd: SlashCommand | CmdT) -> SlashCommand | CmdT:
        func = cmd.func if isinstance(cmd, SlashCommand) else cmd
        for name, desc in kwargs.items():
            try:
                func._param_desc_[name] = desc
            except AttributeError:
                func._param_desc_ = {name: desc}
        return cmd

    return _inner


def slash_command(**kwargs) -> Callable[[CmdT], SlashCommand]:
    """
    Defines a function as a slash-type application command.

    Parameters:
    - name: ``str``
    - - The display name of the command. If unspecified, will use the functions name.
    - guild_id: ``Optional[int]``
    - - The guild ID this command will belong to. If unspecified, the command will be uploaded globally.
    - description: ``str``
    - - The description of the command. If unspecified, will use the functions docstring, or "No description provided" otherwise.
    """

    def _inner(func: CmdT) -> SlashCommand:
        return SlashCommand(func, **kwargs)

    return _inner


def message_command(**kwargs) -> Callable[[MsgCmdT], MessageCommand]:
    """
    Defines a function as a message-type application command.

    Parameters:
    - name: ``str``
    - - The display name of the command. If unspecified, will use the functions name.
    - guild_id: ``Optional[int]``
    - - The guild ID this command will belong to. If unspecified, the command will be uploaded globally.
    """

    def _inner(func: MsgCmdT) -> MessageCommand:
        return MessageCommand(func, **kwargs)

    return _inner


def user_command(**kwargs) -> Callable[[UsrCmdT], UserCommand]:
    """
    Defines a function as a user-type application command.

    Parameters:
    - name: ``str``
    - - The display name of the command. If unspecified, will use the functions name.
    - guild_id: ``Optional[int]``
    - - The guild ID this command will belong to. If unspecified, the command will be uploaded globally.
    """

    def _inner(func: UsrCmdT) -> UserCommand:
        return UserCommand(func, **kwargs)

    return _inner


class _RangeMeta(type):
    @overload
    def __getitem__(cls: type[RngT], max: int) -> type[int]: ...

    @overload
    def __getitem__(cls: type[RngT], max: tuple[int, int]) -> type[int]: ...

    @overload
    def __getitem__(cls: type[RngT], max: float) -> type[float]: ...

    @overload
    def __getitem__(cls: type[RngT], max: tuple[float, float]) -> type[float]: ...

    def __getitem__(cls, max):
        if isinstance(max, tuple):
            return cls(*max)
        return cls(None, max)


class Range(metaclass=_RangeMeta):
    """
    Defines a minimum and maximum value for float or int values. The minimum value is optional.
    ```python
    async def number(self, ctx, num: slash_util.Range[0, 10], other_num: slash_util.Range[10]):
        ...
    ```"""

    def __init__(self, min: NumT | None, max: NumT):
        if min is not None and min >= max:
            raise ValueError("`min` value must be lower than `max`")
        self.min = min
        self.max = max


class Bot(commands.Bot):
    async def start(self, token: str) -> None:
        await self.login(token)
        await self.sync_commands()
        await self.connect()

    def get_application_command(self, name: str) -> Command | None:
        """
        Gets and returns an application command by the given name.

        Parameters:
        - name: ``str``
        - - The name of the command.

        Returns:
        - [Command](#deco-slash_commandkwargs)
        - - The relevant command object
        - ``None``
        - - No command by that name was found.
        """

        for c in self.cogs.values():
            if isinstance(c, ApplicationCog):
                c = c._commands.get(name)
                if c:
                    return c

    async def delete_all_commands(self, guild_id: int | None = None):
        """
        Deletes all commands on the specified guild, or all global commands if no guild id was given.

        Parameters:
        - guild_id: ``Optional[str]``
        - - The guild ID to delete from, or ``None`` to delete global commands.
        """
        path = f'/applications/{self.user.id}'
        if guild_id is not None:
            path += f'/guilds/{guild_id}'
        path += '/commands'

        route = discord.http.Route("GET", path)
        data = await self.http.request(route)

        for cmd in data:
            snow = cmd['id']
            await self.delete_command(snow, guild_id=guild_id)

    async def delete_command(self, id: int, *, guild_id: int | None = None):
        """
        Deletes a command with the specified ID. The ID is a snowflake, not the name of the command.

        Parameters:
        - id: ``int``
        - - The ID of the command to delete.
        - guild_id: ``Optional[str]``
        - - The guild ID to delete from, or ``None`` to delete a global command.
        """
        route = discord.http.Route('DELETE',
                                   f'/applications/{self.user.id}{f"/guilds/{guild_id}" if guild_id else ""}/commands/{id}')
        await self.http.request(route)

    async def sync_commands(self) -> None:
        """
        Uploads all commands from cogs found and syncs them with discord.
        Global commands will take up to an hour to update. Guild specific commands will update immediately.
        """
        if not self.user:
            raise RuntimeError("sync_commands must be called after `run`, `start` or `login`")

        for cog in self.cogs.values():
            if not isinstance(cog, ApplicationCog):
                continue

            for cmd in cog._commands.values():
                cmd.cog = cog
                route = f"/applications/{self.user.id}"

                if cmd.guild_id:
                    route += f"/guilds/{cmd.guild_id}"
                route += '/commands'

                body = cmd._build_command_payload()

                route = discord.http.Route('POST', route)
                await self.http.request(route, json=body)


class Context(Generic[BotT, CogT]):
    """
    The command interaction context.

    Attributes
    - bot: [``slash_util.Bot``](#class-botcommand_prefix-help_commanddefault-help-command-descriptionnone-options)
    - - Your bot object.
    - command: Union[[SlashCommand](#deco-slash_commandkwargs), [UserCommand](#deco-user_commandkwargs), [MessageCommand](deco-message_commandkwargs)]
    - - The command used with this interaction.
    - interaction: [``discord.Interaction``](https://discordpy.readthedocs.io/en/master/api.html#discord.Interaction)
    - - The interaction tied to this context."""

    def __init__(self, bot: BotT, command: Command[CogT], interaction: discord.Interaction):
        self.bot = bot
        self.command = command
        self.interaction = interaction
        self._responded = False

    @overload
    def send(self, content: str = MISSING, *, embed: discord.Embed = MISSING, ephemeral: bool = MISSING,
             tts: bool = MISSING, view: discord.ui.View = MISSING, file: discord.File = MISSING) -> Coroutine[
        Any, Any, Union[discord.InteractionMessage, discord.WebhookMessage]]: ...

    @overload
    def send(self, content: str = MISSING, *, embed: discord.Embed = MISSING, ephemeral: bool = MISSING,
             tts: bool = MISSING, view: discord.ui.View = MISSING, files: list[discord.File] = MISSING) -> Coroutine[
        Any, Any, Union[discord.InteractionMessage, discord.WebhookMessage]]: ...

    @overload
    def send(self, content: str = MISSING, *, embeds: list[discord.Embed] = MISSING, ephemeral: bool = MISSING,
             tts: bool = MISSING, view: discord.ui.View = MISSING, file: discord.File = MISSING) -> Coroutine[
        Any, Any, Union[discord.InteractionMessage, discord.WebhookMessage]]: ...

    @overload
    def send(self, content: str = MISSING, *, embeds: list[discord.Embed] = MISSING, ephemeral: bool = MISSING,
             tts: bool = MISSING, view: discord.ui.View = MISSING, files: list[discord.File] = MISSING) -> Coroutine[
        Any, Any, Union[discord.InteractionMessage, discord.WebhookMessage]]: ...

    async def send(self, content=MISSING, **kwargs) -> Union[discord.InteractionMessage, discord.WebhookMessage]:
        """
        Responds to the given interaction. If you have responded already, this will use the follow-up webhook instead.
        Parameters ``embed`` and ``embeds`` cannot be specified together.
        Parameters ``file`` and ``files`` cannot be specified together.

        Parameters:
        - content: ``str``
        - - The content of the message to respond with
        - embed: [``discord.Embed``](https://discordpy.readthedocs.io/en/master/api.html#discord.Embed)
        - - An embed to send with the message. Incompatible with ``embeds``.
        - embeds: ``List[``[``discord.Embed``](https://discordpy.readthedocs.io/en/master/api.html#discord.Embed)``]``
        - - A list of embeds to send with the message. Incompatible with ``embed``.
        - file: [``discord.File``](https://discordpy.readthedocs.io/en/master/api.html#discord.File)
        - - A file to send with the message. Incompatible with ``files``.
        - files: ``List[``[``discord.File``](https://discordpy.readthedocs.io/en/master/api.html#discord.File)``]``
        - - A list of files to send with the message. Incompatible with ``file``.
        - ephemeral: ``bool``
        - - Whether the message should be ephemeral (only visible to the interaction user).
        - tts: ``bool``
        - - Whether the message should be played via Text To Speech. Send TTS Messages permission is required.
        - view: [``discord.ui.View``](https://discordpy.readthedocs.io/en/master/api.html#discord.ui.View)
        - - Components to attach to the sent message.

        Returns
        - [``discord.InteractionMessage``](https://discordpy.readthedocs.io/en/master/api.html#discord.InteractionMessage) if this is the first time responding.
        - [``discord.WebhookMessage``](https://discordpy.readthedocs.io/en/master/api.html#discord.WebhookMessage) for consecutive responses.
        """
        if self._responded:
            return await self.interaction.followup.send(content, wait=True, **kwargs)

        await self.interaction.response.send_message(content or None, **kwargs)
        self._responded = True

        return await self.interaction.original_message()

    @property
    def cog(self) -> CogT:
        """The cog this command belongs to."""
        return self.command.cog

    @property
    def guild(self) -> discord.Guild:
        """The guild this interaction was executed in."""
        return self.interaction.guild

    @property
    def message(self) -> discord.Message:
        """The message that executed this interaction."""
        return self.interaction.message

    @property
    def channel(self) -> discord.interactions.InteractionChannel:
        """The channel the interaction was executed in."""
        return self.interaction.channel

    @property
    def author(self) -> discord.Member:
        """The user that executed this interaction."""
        return self.interaction.user


class Command(Generic[CogT]):
    cog: CogT
    func: Callable
    name: str
    guild_id: int | None

    def _build_command_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    async def invoke(self, context: Context[BotT, CogT], *args) -> None:
        await self.func(self.cog, context, *args)


class SlashCommand(Command[CogT]):
    def __init__(self, func: CmdT, **kwargs):
        self.func = func
        self.cog: CogT

        self.name: str = kwargs.get("name", func.__name__)

        self.description: str = kwargs.get("description") or func.__doc__ or "No description provided"

        self.guild_id: int | None = kwargs.get("guild_id")

        self.parameters = self._build_parameters()
        self._parameter_descriptions: dict[str, str] = defaultdict(lambda: "No description provided")

    def _build_parameters(self) -> dict[str, inspect.Parameter]:
        params = list(inspect.signature(self.func).parameters.values())
        try:
            params.pop(0)
        except IndexError:
            raise ValueError("expected argument `self` is missing")

        try:
            params.pop(0)
        except IndexError:
            raise ValueError("expected argument `context` is missing")

        return {p.name: p for p in params}

    def _build_descriptions(self):
        if not hasattr(self.func, '_param_desc_'):
            return

        for k, v in self.func._param_desc_.items():
            if k not in self.parameters:
                raise TypeError(f"@describe used to describe a non-existant parameter `{k}`")

            self._parameter_descriptions[k] = v

    def _build_command_payload(self):
        self._build_descriptions()

        payload = {
            "name": self.name,
            "description": self.description,
            "type": 1
        }

        params = self.parameters
        if params:
            options = []
            for name, param in params.items():
                ann = param.annotation

                if ann is param.empty:
                    raise TypeError(f"missing type annotation for parameter `{param.name}` for command `{self.name}`")

                if isinstance(ann, str):
                    ann = eval(ann)

                if isinstance(ann, Range):
                    real_t = type(ann.max)
                elif get_origin(ann) is Union:
                    args = get_args(ann)
                    real_t = args[0]
                else:
                    real_t = ann

                typ = command_type_map[real_t]
                option = {
                    'type': typ,
                    'name': name,
                    'description': self._parameter_descriptions[name]
                }
                if param.default is param.empty:
                    option['required'] = True

                if isinstance(ann, Range):
                    option['max_value'] = ann.max
                    option['min_value'] = ann.min

                elif get_origin(ann) is Union:
                    args = get_args(ann)

                    if not all(issubclass(k, discord.abc.GuildChannel) for k in args):
                        raise TypeError(f"Union parameter types only supported on *Channel types")

                    if len(args) != 3:
                        filtered = [channel_filter[i] for i in args]
                        option['channel_types'] = filtered

                elif issubclass(ann, discord.abc.GuildChannel):
                    option['channel_types'] = [channel_filter[ann]]

                options.append(option)
            options.sort(key=lambda f: not f.get('required'))
            payload['options'] = options
        return payload


class ContextMenuCommand(Command[CogT]):
    _type: ClassVar[int]

    def __init__(self, func: CtxMnT, **kwargs):
        self.func = func
        self.guild_id: int | None = kwargs.get('guild_id', None)
        self.name: str = kwargs.get('name', func.__name__)

    def _build_command_payload(self):
        payload = {
            'name': self.name,
            'type': self._type
        }
        if self.guild_id is not None:
            payload['guild_id'] = self.guild_id
        return payload


class MessageCommand(ContextMenuCommand[CogT]):
    _type = 3


class UserCommand(ContextMenuCommand[CogT]):
    _type = 2


class ApplicationCog(commands.Cog, Generic[BotT]):
    """
    The cog that must be used for application commands.

    Attributes:
    - bot: [``slash_util.Bot``](#class-botcommand_prefix-help_commanddefault-help-command-descriptionnone-options)
    - - The bot instance."""

    def __init__(self, bot: BotT):
        self.bot: BotT = bot
        self._commands: dict[str, Command] = {}

        slashes = inspect.getmembers(self, lambda c: isinstance(c, Command))
        for k, v in slashes:
            self._commands[v.name] = v

    def _get_resolved_data(self, interaction: discord.Interaction, data, state: discord.state.ConnectionState):
        if not data:
            return {}

        assert interaction.guild
        resolved = {}

        resolved_users = data.get('users')
        if resolved_users:
            resolved_members = data['members']
            for id, d in resolved_users.items():
                member_data = resolved_members[id]
                member_data['user'] = d
                member = discord.Member(data=member_data, guild=interaction.guild, state=state)
                resolved[int(id)] = member

        resolved_channels = data.get('channels')
        if resolved_channels:
            for id, d in resolved_channels.items():
                d['position'] = None
                cls, _ = discord.channel._guild_channel_factory(d['type'])
                channel = cls(state=state, guild=interaction.guild, data=d)
                resolved[int(id)] = channel

        resolved_messages = data.get('messages')
        if resolved_messages:
            for id, d in resolved_messages.items():
                msg = discord.Message(state=state, channel=interaction.channel, data=d)  # type: ignore
                resolved[int(id)] = msg

        return resolved

    @commands.Cog.listener("on_interaction")
    async def _internal_interaction_handler(self, interaction: discord.Interaction):
        if interaction.type is not discord.InteractionType.application_command:
            return

        name = interaction.data['name']  # type: ignore
        command = self._commands[name]
        state = self.bot._connection
        resolved_data = self._get_resolved_data(interaction, interaction.data.get('resolved'), state)  # type: ignore
        params = []

        if interaction.data['type'] == 1:  # type: ignore
            if 'options' in interaction.data:  # type: ignore
                for option in interaction.data['options']:  # type: ignore
                    value = option['value']  # type: ignore
                    if option['type'] in (6, 7, 8):
                        value = resolved_data[int(value)]

                    params.append(value)
        else:  # type: ignore
            params.append(resolved_data[int(interaction.data['target_id'])])  # type: ignore

        ctx = Context(self.bot, command, interaction)
        await command.invoke(ctx, *params)
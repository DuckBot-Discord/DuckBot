from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import subprocess
import time as time_lib
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Tuple, TypeVar, Union

import aiohttp
import discord
from discord.ext import commands

from utils.bases.context import DuckContext

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

from utils.bases.errors import *

if TYPE_CHECKING:
    from bot import DuckBot

T = TypeVar('T')
P = ParamSpec('P')
BET = TypeVar('BET', bound='discord.guild.BanEntry')

CDN_REGEX = re.compile(
    r'(https?://)?(media|cdn)\.discord(app)?\.(com|net)/attachments/'
    r'(?P<channel_id>[0-9]+)/(?P<message_id>[0-9]+)/(?P<filename>[\S]+)'
)
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+')

__all__: Tuple[str, ...] = (
    'col',
    'mdr',
    'cb',
    'safe_reason',
    'add_logging',
    'format_date',
    'can_execute_action',
    'DeleteButton',
    'URLObject',
    'Shell',
    'View',
)


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


def mdr(entity: Any) -> str:
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
    return discord.utils.remove_markdown(discord.utils.escape_mentions(str(entity)))


def cb(text: str, /, *, lang: str = 'py'):
    """Wraps a string into a code-block, and adds zero width
    characters to avoid the code block getting cut off.

    Parameters
    ----------
    text: str
        The text to wrap.
    lang: str
        The code language to use.

    Returns
    -------
    str
        The wrapped text.
    """
    text = text.replace('`', '\u200b`')
    return f'```{lang}\n{text}\n```'


def safe_reason(author: Union[discord.Member, discord.User], reason: str, *, length: int = 512) -> str:
    base = f'Action by {author} ({author.id}) for: '

    length_limit = length - len(base)
    if len(reason) > length_limit:
        reason = reason[: length_limit - 3] + '...'

    return base + reason


def format_date(date: datetime) -> str:
    """Formats a date to a string in the preferred way.

    Parameters
    ----------
    date: datetime.datetime
        The date to format.

    Returns
    -------
    str
        The formatted date.
    """
    return date.strftime("%b %d, %Y %H:%M %Z")


def add_logging(func: Callable[P, Union[Awaitable[T], T]]) -> Callable[P, Union[Awaitable[T], T]]:
    """
    Used to add logging to a coroutine or function.

    .. code-block:: python3
        >>> async def foo(a: int, b: int) -> int:
        >>>     return a + b

        >>> logger = add_logging(foo)
        >>> result = await logger(1, 2)
        >>> print(result)
        3

        >>> def foo(a: int, b: int) -> int:
        >>>     return a + b

        >>> logger = add_logging(foo)
        >>> result = logger(1, 2)
        >>> print(result)
        3
    """

    async def _async_wrapped(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
        start = time_lib.time()
        result = await func(*args, **kwargs)  # type: ignore
        print(f'{func.__name__} took {time_lib.time() - start:.2f} seconds')

        return result  # type: ignore

    def _sync_wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time_lib.time()
        result = func(*args, **kwargs)
        print(f'{func.__name__} took {time_lib.time() - start:.2f} seconds')

        return result  # type: ignore

    return _async_wrapped if asyncio.iscoroutinefunction(func) else _sync_wrapped  # type: ignore


async def can_execute_action(
    ctx: DuckContext,
    target: Union[discord.Member, discord.User],
    *,
    fail_if_not_upgrade: bool = True,
) -> Optional[bool]:
    """|coro|

    A wrapped predicate to check if the action can be executed.

    Parameters
    ----------
    ctx: :class:`commands.Context`
        The context of the command.
    target: Union[:class:`discord.Member`, :class:`discord.User`]
        The target of the action.
    fail_if_not_upgrade: :class:`bool`
        Whether to fail if the user can't be upgraded to a Member.

    Returns
    -------
    Optional[:class:`bool`]
        Whether the action can be executed.

    Raises
    ------
    HierarchyException
        The action cannot be executed due to role hierarchy.
    ActionNotExecutable
        The action cannot be executed due to other reasons.
    commands.NoPrivateMessage
        This command cannot be used in private messages.
    """
    guild = ctx.guild
    if guild is None or not isinstance(ctx.author, discord.Member):
        raise commands.NoPrivateMessage('This command cannot be used in private messages.')

    if isinstance(target, discord.User):
        upgraded = await ctx.bot.get_or_fetch_member(guild, target)
        if upgraded is None:
            if fail_if_not_upgrade:
                raise ActionNotExecutable('That user is not a member of this server.')
        else:
            target = upgraded

    if ctx.author == target:
        raise ActionNotExecutable('You cannot execute this action on yourself!')
    if guild.owner == target:
        raise ActionNotExecutable('I cannot execute any action on the server owner!')

    if isinstance(target, discord.Member):
        if guild.me.top_role <= target.top_role:
            raise HierarchyException(target)
        if guild.owner == ctx.author:
            return
        if ctx.author.top_role <= target.top_role:
            raise HierarchyException(target, author_error=True)


class DeleteButtonCallback(discord.ui.Button['DeleteButton']):
    """Internal."""

    async def callback(self, interaction: discord.Interaction) -> Any:
        try:
            if interaction.message:
                await interaction.message.delete()
        finally:
            if self.view:
                self.view.stop()


class DeleteButton(discord.ui.View):
    """
    A button that deletes the message.

    Parameters
    ----------
    message: :class:`discord.Message`
        The message to delete.
    author: :class:`discord.Member`
        The person who can interact with the button.
    style: :class:`discord.ButtonStyle`
        The style of the button. Defaults to red.
    label: :class:`str`
        The label of the button. Defaults to 'Delete'.
    emoji: :class:`str`
        The emoji of the button. Defaults to None.
    """

    def __init__(self, *args, **kwargs):
        self.bot: Optional[commands.Bot] = None
        self._message = kwargs.pop('message', None)
        self.author = kwargs.pop('author')
        self.delete_on_timeout = kwargs.pop('delete_on_timeout', True)

        super().__init__(timeout=kwargs.pop('timeout', 180))

        self.add_item(
            DeleteButtonCallback(
                style=kwargs.pop('style', discord.ButtonStyle.red),
                label=kwargs.pop('label', 'Delete'),
                emoji=kwargs.pop('emoji', None),
            )
        )
        if isinstance(self.bot, commands.Bot):
            self.bot.views.add(self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Checks if the user is the right one."""
        return interaction.user == self.author

    async def on_timeout(self) -> None:
        """Deletes the message on timeout."""
        if self.message:
            try:
                if self.delete_on_timeout:
                    await self.message.delete()
                else:
                    await self.message.edit(view=None)
            except discord.HTTPException:
                pass
        try:
            self.bot.views.remove(self)  # type: ignore
        except (AttributeError, ValueError, KeyError):
            pass

    def stop(self) -> None:
        """Stops the view."""
        try:
            self.bot.views.remove(self)  # type: ignore
        except (AttributeError, ValueError, KeyError):
            pass
        finally:
            super().stop()

    @property
    def message(self) -> Optional[discord.Message]:
        """The message to delete."""
        return self._message

    @message.setter
    def message(self, message: discord.Message) -> None:
        self._message = message
        try:
            # noinspection PyProtectedMember
            self.bot = message._state._get_client()  # type: ignore
        except Exception as e:
            logging.error(f'Failed to get client from message %s: %s', message, exc_info=e)

    @classmethod
    async def to_destination(cls, destination: discord.abc.Messageable | discord.Webhook, *args, **kwargs) -> 'DeleteButton':
        if kwargs.get('view', None):
            raise TypeError('Cannot pass a view to to_destination')

        view = cls(
            style=kwargs.pop('style', discord.ButtonStyle.red),
            label=kwargs.pop('label', 'Delete'),
            emoji=kwargs.pop('emoji', None),
            author=kwargs.pop('author'),
            timeout=kwargs.pop('timeout', 180),
            delete_on_timeout=kwargs.pop('delete_on_timeout', True),
        )
        message = await destination.send(*args, **kwargs, view=view)
        view.message = message

        if isinstance(view.bot, commands.Bot):
            try:
                view.bot.views.add(view)  # type: ignore
            except (AttributeError, ValueError):
                pass

        return view


class URLObject:
    """A class to represent a URL.

    Attributes
    ----------
    url: :class:`str`
        The URL.
    name: :class:`str`
        the filename of the URL.
    channel_id: :class:`int`
        The ID of the channel the URL is in.
    message_id: :class:`int`
        The ID of the message the URL is in.
    """

    if TYPE_CHECKING:
        url: str
        name: str
        channel_id: Optional[int]
        message_id: Optional[int]

    __slots__: Tuple[str, ...] = ('url', 'name', 'channel_id', 'message_id')

    def __init__(self, url: str, *, is_discord_url: bool = True):
        if is_discord_url is True:
            match = CDN_REGEX.fullmatch(url)
            if not match:
                return
            self.channel_id = int(match.group('channel_id'))
            self.message_id = int(match.group('message_id'))
            self.name = match.group('filename')
            self.url = url

        else:
            match = URL_REGEX.fullmatch(url)
            self.url = url
            self.name = url.split("/")[-1]
            self.channel_id = None
            self.message_id = None

    async def read(self, *, session: Optional[aiohttp.ClientSession] = None) -> bytes:
        """|coro|

        Retrieves the contents of the URL.

        Parameters
        ----------
        session : Optional[aiohttp.ClientSession]
            The session to use to retrieve the URL.
            If none is passed, it will a new one, then
            close it when done.
        """
        _session = session or aiohttp.ClientSession()
        try:
            async with _session.get(self.url) as resp:
                if resp.status == 200:
                    return await resp.read()
                elif resp.status == 404:
                    raise discord.NotFound(resp, 'asset not found')
                elif resp.status == 403:
                    raise discord.Forbidden(resp, 'cannot retrieve asset')
                else:
                    raise discord.HTTPException(resp, 'failed to get asset')
        finally:
            if not session:
                await _session.close()

    async def save(
        self,
        fp: Union[io.BufferedIOBase, os.PathLike[Any]],
        *,
        seek_begin: bool = True,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> int:
        """|coro|

        Saves the contents of the URL to a file-like
         object, or a buffer-like object.

        Parameters
        ----------
        fp : Union[io.BufferedIOBase, os.PathLike[Any]]
            The file-like object to save the contents to.
        seek_begin : bool
            Whether to seek to the beginning of the file
            after saving.
        session : Optional[aiohttp.ClientSession]
            The session to use to retrieve the URL.
            If none is passed, it will a new one, then
            close it when done.

        Returns
        -------
        int
            The number of bytes written.
        """
        data = await self.read(session=session)
        if isinstance(fp, io.BufferedIOBase):
            written = fp.write(data)
            if seek_begin:
                fp.seek(0)
            return written
        else:
            with open(fp, 'wb') as f:
                return f.write(data)

    @property
    def spoiler(self):
        """Weather this file is a discord spoiler"""
        return self.name.startswith("SPOILER_")

    async def to_file(self, *, session: aiohttp.ClientSession):
        """|coro|

        Returns a discord.File object from the URL.

        Parameters
        ----------
        session : Optional[aiohttp.ClientSession]
            The session to use to retrieve the URL.

        Returns
        -------
        discord.File
            The file object.
        """
        return discord.File(io.BytesIO(await self.read(session=session)), self.name, spoiler=False)


@dataclass()
class ShellOutput:
    stdout: str
    stderr: str


class ShellRunner:
    def __init__(self, command: str, output: ShellOutput) -> None:
        self.output: ShellOutput = output
        self.command: str = command

    async def execute(self) -> None:
        process = await asyncio.create_subprocess_shell(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        self.output.stdout = stdout.decode()
        self.output.stderr = stderr.decode()

    async def asoutput(self) -> ShellOutput:
        await self.execute()
        return self.output

    async def astuple(self) -> Tuple[str, str]:
        await self.execute()
        return self.output.stdout, self.output.stderr

    def __await__(self):
        return self.asoutput().__await__()


class Shell:
    def __init__(self, command: str) -> None:
        self._command = command
        self._output: ShellOutput = ShellOutput("", "")

    def run(self) -> ShellRunner:
        return ShellRunner(self._command, self._output)

    @property
    def stdout(self) -> str:
        return self._output.stdout

    @property
    def stderr(self) -> str:
        return self._output.stderr

    @property
    def command(self) -> str:
        return self._command

    @command.setter
    def command(self, command: str) -> None:
        self._command = command
        self._output.stdout = ""
        self._output.stderr = ""


class View(discord.ui.View):
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any]) -> None:
        bot: DuckBot = interaction.client  # type: ignore
        await bot.exceptions.add_error(error=error)
        if interaction.response.is_done():
            await interaction.followup.send(f"Sorry! something went wrong....", ephemeral=True)
        else:
            await interaction.response.send_message(f"Sorry! something went wrong....", ephemeral=True)

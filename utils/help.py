from __future__ import annotations

import logging
from fuzzywuzzy import process
from functools import partial
import cachetools
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Generator,
    List,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    Union,
    Callable,
)

import discord
from discord.ext import commands

from .constants import SERVERS_ICON, GITHUB
from .errors import DuckNotFound, DuckBotNotStarted
from .time import human_join
from .context import DuckContext
from .command import DuckCommand, DuckGroup

from bot import DuckBot

if TYPE_CHECKING:
    from .base_cog import DuckCog

    class _Parentable(Protocol):
        parent: Union[_Parentable, DuckBot]
        bot: Optional[DuckBot]

    ParentType = Union[DuckBot, _Parentable, discord.ui.View]


QUESTION_MARK = "\N{BLACK QUESTION MARK ORNAMENT}"
HOME = "\N{HOUSE BUILDING}"
NON_MARKDOWN_INFORMATION_SOURCE = "\N{INFORMATION SOURCE}"

InteractionCheckCallback = Callable[
    [discord.ui.View, discord.Interaction], Awaitable[bool]
]

log = logging.getLogger("Duckbot.utils.help")


def _backup_command_embed(command: commands.Command) -> discord.Embed:
    """A method called when the command requested isn't of type DuckCommand"""
    embed = discord.Embed(
        title=command.qualified_name,
        description=command.help,
    )

    embed.add_field(
        name="How to use",
        value=f"`db.{command.qualified_name} {command.signature}".strip() + "`",
    )

    if subcommands := getattr(command, "commands", None):
        embed.add_field(
            name="Subcommands",
            value=human_join([f"`{c.name}`" for c in subcommands], final="and"),
            inline=False,
        )

    if isinstance(command, commands.Group):
        embed.set_footer(text=f"Select a subcommand to get more information about it.")

    return embed


def _find_bot(parentable: ParentType) -> DuckBot:
    """A helper function used to find the bot in the parent chain"""
    base = parentable

    if isinstance(parentable, DuckBot):
        return parentable
    if db := getattr(parentable, "bot", None):
        return db

    while hasattr(parentable, "parent"):
        if isinstance(parentable, DuckBot):
            return parentable

        if db := getattr(parentable, "bot", None):
            return db

        parentable = parentable.parent  # type: ignore # Can not use isinstance for DuckBot so we have to ignore this

    raise DuckNotFound(
        f"Could not find DuckBot from base parentable {base}, {repr(base)}."
    )


def _walk_through_parents(parentable: ParentType) -> Generator[ParentType, None, None]:
    """Used to walk through the parent chain of a parentable object"""
    if isinstance(parentable, DuckBot):
        print("parent is duckbot")
        yield from []

    while hasattr(parentable, "parent"):
        yield parentable
        parentable = getattr(parentable, "parent")


@cachetools.cached(cache=cachetools.TTLCache(maxsize=500, ttl=30))
def _find_author_from_parent(
    parentable: ParentType,
) -> Optional[Union[discord.Member, discord.User]]:
    """Used to find the author of the help command from the parent chain"""
    author: Optional[Union[discord.Member, discord.User]] = None

    if maybe_author := getattr(parentable, "author", None):
        author = maybe_author

    if not author and (context := getattr(parentable, "context", None)):
        author = context.author

    if not author:
        for parent in _walk_through_parents(parentable):
            if maybe_author := getattr(parent, "author", None):
                author = maybe_author
                break
            if context := getattr(parent, "context", None):
                author = context.author
                break

    return author


async def _interaction_check(
    view: discord.ui.View, interaction: discord.Interaction
) -> Optional[bool]:
    """An internal helper used to check if the interaction is valid."""
    # Let's find the original author of the help command
    author = _find_author_from_parent(view)  # type: ignore
    if not author:
        raise ValueError("Could not find author from parentable.")

    if interaction.user != author:
        return await interaction.response.send_message(
            "You do not have permission to use this help command!", ephemeral=True
        )

    return True


class Stop(discord.ui.Button):
    """A button used to stop the help command.

    Attributes
    ----------
    parent: :class:`discord.ui.View`
        The parent view of the help command.
    """

    __slots__: Tuple[str, ...] = ("parent",)

    def __init__(self, parent: discord.ui.View) -> None:
        self.parent: discord.ui.View = parent
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Stop",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """|coro|

        When called, will respond to the interaction by editing the message
        with the diabled view.

        Parameters
        ----------
        interaction: :class:`discord.Interaction`
            The interaction that was created by interacting with the button.
        """
        for child in self.parent.children:
            child.disabled = True  # type: ignore

        self.parent.stop()
        return await interaction.response.edit_message(view=self.parent)


class GoHome(discord.ui.Button):
    """A button used to go home within the parent tree. Home
    is considered the root of the parent tree.

    Attributes
    ----------
    parent: Any
        The parent of the help command.
    bot: :class:`DuckBot`
        The bot that the help command is running on.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "bot",
    )

    def __init__(self, parent: ParentType) -> None:
        self.parent: ParentType = parent
        self.bot: DuckBot = _find_bot(parent)
        super().__init__(
            label="Go Home",
            emoji=HOME,
        )

    # noinspection PyProtectedMember
    async def _get_help_from_parent(self) -> HelpView:
        main_parent: Optional[DuckHelp] = discord.utils.find(lambda p: isinstance(p, DuckHelp), _walk_through_parents(self.parent))  # type: ignore
        if main_parent:
            clean_mapping = await main_parent._filter_mapping(
                {  # type: ignore # We're gonna pretend we're using TS today
                    cog: cog.get_commands() for cog in self.bot.cogs.values()
                }
            )
        else:
            clean_mapping = {cog: None for cog in self.bot.cogs.values()}

        return HelpView(parent=self.parent, cogs=clean_mapping.keys(), author=_find_author_from_parent(self.parent))  # type: ignore

    async def callback(self, interaction: discord.Interaction) -> None:
        """|coro|

        When called, will respond to the interaction by finding the root
        within the parent tree and editing the message with the highest
        parent.

        Parameters
        ----------
        interaction: :class:`discord.Interaction`
            The interaction that was created by interacting with the button.
        """
        # We need to find the base parent
        if self.parent is self.bot:
            # There is no home in cache, we need to create one
            view = await self._get_help_from_parent()
        else:
            # Let's try and find the home in cache
            for parent in _walk_through_parents(self.parent):
                if isinstance(parent, HelpView):
                    view = parent
                    break
            else:
                # No parent in parents history, we need to create one
                view = await self._get_help_from_parent()

        return await interaction.response.edit_message(embed=view.embed, view=view)


class GoBack(discord.ui.Button):
    """A button used to go back within the parent tree.

    Attributes
    ----------
    parent: :class:`discord.ui.View`
        The parent view of the help command.
    """

    __slots__: Tuple[str, ...] = ("parent",)

    def __init__(self, parent: discord.ui.View) -> None:
        super().__init__(label="Go Back")
        self.parent: discord.ui.View = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        """|coro|

        When called, will respond to the interaction by editing the message with the previous parent.

        Parameters
        ----------
        interaction: :class:`discord.Interaction`
            The interaction that was created by interacting with the button.
        """
        return await interaction.response.edit_message(embed=self.parent.embed, view=self.parent)  # type: ignore


class CommandSelecter(discord.ui.Select):
    """A select used to have the user select a command
    from a list of commands.

    Parameters
    ----------
    parent: ParentType
        The parent that created this select.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "_command_mapping",
    )

    def __init__(self, *, parent: ParentType, cmds: List[DuckCommand]) -> None:
        self.parent: ParentType = parent

        self._command_mapping: Mapping[str, DuckCommand] = {
            c.qualified_name: c for c in cmds
        }
        super().__init__(
            placeholder="Select a command...",
            options=[
                discord.SelectOption(
                    label=command.qualified_name,
                    description=command.brief[:100] if command.brief else "",
                    value=command.qualified_name,
                )
                for command in cmds
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """|coro|

        When called, will respond to the interaction by editing th emessage with
        a new view representing the selected command.

        Parameters
        ----------
        interaction: :class:`discord.Interaction`
            The interaction that was created by interacting with the button.
        """
        selected = self.values
        if not selected:
            return

        command = self._command_mapping[selected[0]]
        if isinstance(command, DuckGroup):
            view = HelpGroup(parent=self.parent, group=command)
        else:
            view = HelpCommand(parent=self.parent, command=command)  # type: ignore

        return await interaction.response.edit_message(embed=view.embed, view=view)


class HelpGroup(discord.ui.View):
    """A view representing the help for a command group.

    Attributes
    ----------
    parent: ParentType
        The parent thaty created this view.
    group: :class:`DuckGroup`
        The group that this view represents.
    author: Optional[Union[:class:`discord.Member`, :class:`discord.User`]]
        The author of the message that created this view.
    bot: :class:`DuckBot`
        The bot that this view is running on.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "_command_mapping",
        "_cs_embed",
    )

    def __init__(
        self,
        *,
        parent: ParentType,
        group: DuckGroup,
        author: Optional[Union[discord.Member, discord.User]] = None,
    ) -> None:
        super().__init__()

        self.parent: ParentType = parent
        self.group: DuckGroup = group
        self.author: Optional[Union[discord.Member, discord.User]] = author

        self.bot: DuckBot = _find_bot(parent)
        self.interaction_check: InteractionCheckCallback = partial(_interaction_check, self)  # type: ignore

        group_commands = list(group.commands)
        for command in group_commands:
            if isinstance(command, DuckGroup):
                group_commands.extend(command.commands)

        for chunk in self.bot.chunker(group_commands, size=20):
            self.add_item(CommandSelecter(parent=self, cmds=chunk))  # type: ignore

        self.add_item(GoHome(self))
        if isinstance(self.parent, discord.ui.View):
            self.add_item(GoBack(self.parent))

        self.add_item(Stop(self))

    @discord.utils.cached_slot_property("_cs_embed")
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: Returns an embed representing the help for the group."""
        if help_embed := getattr(self.group, "help_embed", None):
            return help_embed

        return _backup_command_embed(self.group)


class HelpCommand(discord.ui.View):
    """A view representing the help for a command.

    Attributes
    ----------
    parent: ParentType
        The parent thaty created this view.
    command: :class:`DuckCommand`
        The group that this view represents.
    author: Optional[Union[:class:`discord.Member`, :class:`discord.User`]]
        The author of the message that created this view.
    bot: :class:`DuckBot`
        The bot that this view is running on.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "command",
        "author",
        "interaction_check",
        "bot",
        "_cs_embed",
    )

    def __init__(
        self,
        *,
        parent: ParentType,
        command: DuckCommand,
        author: Optional[Union[discord.Member, discord.User]] = None,
    ) -> None:
        super().__init__()

        self.parent: ParentType = parent
        self.command: DuckCommand = command
        self.author: Optional[Union[discord.Member, discord.User]] = author

        self.interaction_check: InteractionCheckCallback = partial(_interaction_check, self)  # type: ignore
        self.bot: DuckBot = _find_bot(parent)

        self.add_item(GoHome(self))
        if isinstance(self.parent, discord.ui.View):
            self.add_item(GoBack(self.parent))

        self.add_item(Stop(self))

    @discord.utils.cached_slot_property("_cs_embed")
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: Returns an embed representing the help for the command."""
        if help_embed := getattr(self.command, "help_embed", None):
            return help_embed

        return _backup_command_embed(self.command)


class HelpCog(discord.ui.View):
    """A view representing the help for a cog.

    Attributes
    ----------
    parent: ParentType
        The parent thaty created this view.
    cog: :class:`DuckCog`
        The group that this view represents.
    author: Optional[Union[:class:`discord.Member`, :class:`discord.User`]]
        The author of the message that created this view.
    bot: :class:`DuckBot`
        The bot that this view is running on.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "cog",
        "author",
        "interaction_check",
        "bot",
        "_cs_embed",
    )

    def __init__(
        self,
        *,
        parent: ParentType,
        cog: DuckCog,
        author: Optional[Union[discord.Member, discord.User]] = None,
    ) -> None:
        super().__init__()

        self.parent: ParentType = parent
        self.cog: DuckCog = cog
        self.author: Optional[Union[discord.Member, discord.User]] = author

        self.bot: DuckBot = _find_bot(parent)
        self.interaction_check: InteractionCheckCallback = partial(_interaction_check, self)  # type: ignore

        for item in self.bot.chunker(cog.get_commands(), size=20):
            self.add_item(CommandSelecter(parent=self, cmds=list(item)))  # type: ignore

        self.add_item(GoHome(self))
        if isinstance(self.parent, discord.ui.View):
            self.add_item(GoBack(self.parent))

        self.add_item(Stop(self))

    @discord.utils.cached_slot_property("_cs_embed")
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: Returns an embed representing the help for the cog."""
        cog = self.cog
        embed = discord.Embed(
            title=f"{cog.emoji or QUESTION_MARK} {cog.qualified_name}",
            description=cog.description,
        )
        embed.add_field(
            name="Commands",
            value=human_join(
                [f"`{command.qualified_name}`" for command in cog.get_commands()],
                final="and",
            )
            or "No commands...",
        )
        embed.set_footer(text="Use the dropdown to get more info on a command.")
        return embed


class HelpSelect(discord.ui.Select):
    """A select prompting the user to select a cog.

    Attributes
    ----------
    parent: ParentType
        The parent thaty created this view.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "_cog_mapping",
    )

    def __init__(self, *, parent: ParentType, cogs: List[DuckCog]) -> None:
        self.parent: ParentType = parent
        self._cog_mapping: Mapping[int, DuckCog] = {c.id: c for c in cogs}

        super().__init__(
            placeholder="Select a group...",
            options=[
                discord.SelectOption(
                    label=cog.qualified_name,
                    value=str(cog.id),
                    description=cog.brief or "No description...",
                    emoji=cog.emoji,
                )
                for cog in cogs
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """|coro|

        When called, this will create a new view representing the selected cog.

        Parameters
        ----------
        interaction: :class:`discord.Interaction`
            The interaction that was used to select this option.
        """
        selected = self.values
        if not selected:
            return

        current_cog = self._cog_mapping[int(selected[0])]
        view = HelpCog(
            parent=self.parent,
            cog=current_cog,
            author=_find_author_from_parent(self.parent),
        )
        return await interaction.response.edit_message(embed=view.embed, view=view)


class HelpView(discord.ui.View):
    """The main Help View for the DuckHelper.

    When sending the initial Help Message with no arguments,
    this will be sent.

    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance.
    """

    __slots__: Tuple[str, ...] = (
        "parent",
        "bot",
        "author",
        "interaction_check",
        "_cs_embed",
    )

    def __init__(
        self,
        /,
        *,
        parent: ParentType,
        cogs: List[DuckCog],
        author: Optional[Union[discord.Member, discord.User]] = None,
    ) -> None:
        super().__init__()
        self.parent: ParentType = parent
        self.bot: DuckBot = _find_bot(parent)
        self.author: Optional[Union[discord.Member, discord.User]] = author
        self.interaction_check: InteractionCheckCallback = partial(_interaction_check, self)  # type: ignore

        self.add_item(HelpSelect(parent=self, cogs=cogs))
        if isinstance(self.parent, discord.ui.View):
            self.add_item(GoBack(self.parent))

        self.add_item(Stop(self))

    @discord.utils.cached_slot_property("_cs_embed")
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: The master embed for this view."""
        getting_help: List[str] = [
            "Use `db.help <command>` for more info on a command.",
            "There is also `db.help <command> [subcommand]`.",
            "Use `db.help <category>` for more info on a category.",
            "You can also use the menu below to view a category.",
        ]
        getting_support: List[str] = [
            "To get help, you can join my support server.",
            f"{SERVERS_ICON} https://discord.gg/TdRfGKg8Wh",
            "📨 You can also send me a DM if you prefer to.",
        ]

        embed = discord.Embed(
            title="DuckBot Help Menu",
            description="Hello, I'm DuckBot! A multi-purpose bot with a lot of features.",
        )
        embed.set_author(
            name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
        )
        embed.add_field(
            name="Getting Help", value="\n".join(getting_help), inline=False
        )
        embed.add_field(
            name="Getting Support", value="\n".join(getting_support), inline=False
        )
        embed.add_field(
            name="Who am I?",
            value=f"I'm DuckBot, a multipurpose bot created and maintained by {GITHUB}[LeoCx1000](https://github.com/LeoCx1000)."
            "and assisted by [NextChai](https://github.com/NextChai). You can use me to play games, moderate your server, mess with some images and more! "
            "Check out all my features using the dropdown below.\n\n"
            f"I've been online since {self.bot.uptime_timestamp}.\n"
            f"You can find my source code on {GITHUB}[GitHub](https://github.com/LeoCx1000/discord-bots/tree/rewrite).",
            inline=False,
        )
        embed.add_field(
            name="Support DuckBot",
            value="If you like DuckBot, you can support by voting here:\n"
            "⭐ https://top.gg/bot/788278464474120202 ⭐",
            inline=False,
        )
        embed.set_footer(
            text=f"{NON_MARKDOWN_INFORMATION_SOURCE} For more info on a command press {QUESTION_MARK} help."
        )
        return embed


class DuckHelp(commands.HelpCommand):
    """The main Help Command for the DuckBot.

    This help command works on a parential basis. This means there is a parent hierarchy
    that can be tracked per invoke by going up the parent chain.
    """

    if TYPE_CHECKING:
        context: DuckContext[DuckBot]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs, verify_checks=False)

    @property
    def bot(self) -> DuckBot:
        """:class:`DuckBot`: The bot instance."""
        if bot := getattr(self, "_bot", None):
            return bot

        return self.context.bot

    @bot.setter
    def bot(self, new: DuckBot) -> None:
        self._bot = new

    async def _filter_mapping(
        self, mapping: Mapping[Optional[DuckCog], List[DuckCommand]]
    ) -> Mapping[Optional[DuckCog], List[DuckCommand]]:
        """An internal helper method to filter all commands."""
        cmds = sum(mapping.values(), [])
        await self.filter_commands(cmds)

        cogs = {}
        for command in cmds:
            if not command.cog:
                continue

            key = command.cog
            if key not in cogs:
                cogs[key] = [command]
            else:
                cogs[key].append(command)

        return cogs  # type: ignore

    async def send_bot_help(
        self, mapping: Mapping[Optional[DuckCog], List[DuckCommand]]
    ) -> discord.Message:
        """|coro|

        A method used to send the bot's main help message.

        Parameters
        ----------
        mapping: Mapping[Optional[:class:`DuckCog`], List[:class:`DuckCommand`]]
            A mapping of :class:`DuckCog` to its list of commands.

        Returns
        -------
        :class:`discord.Message`
            The message that was sent to the user.
        """
        self.bot = self.context.bot
        mapping = await self._filter_mapping(mapping)
        view = HelpView(
            parent=self.bot,
            cogs=list(cog for cog in mapping if cog),
            author=self.context.author,
        )
        return await self.context.send(embed=view.embed, view=view)

    async def send_cog_help(self, cog: DuckCog, /) -> discord.Message:
        """|coro|

        A method used to send the cog help message for the given cog.

        Parameters
        ----------
        cog: :class:`DuckCog`
            The cog to get the help message for.

        Returns
        -------
        :class:`discord.Message`
            The message that was sent to the user.
        """
        view = HelpCog(parent=self.context.bot, cog=cog, author=self.context.author)
        return await self.context.send(embed=view.embed, view=view)

    async def send_group_help(
        self, group: DuckGroup[Any, ..., Any], /
    ) -> discord.Message:
        """|coro|

        A method used to display the help message for the given group.

        Parameters
        ----------
        group: :class:`DuckGroup`
            The group to display help for.

        Returns
        -------
        :class:`discord.Message`
            The message that was sent to the user.
        """
        view = HelpGroup(
            parent=self.context.bot, group=group, author=self.context.author
        )
        return await self.context.send(embed=view.embed, view=view)

    async def send_command_help(
        self, command: DuckCommand[Any, ..., Any], /
    ) -> discord.Message:
        """|coro|

        A method used to display the help message for the given command.

        Parameters
        ----------
        command: :class:`DuckCommand`
            The group to display help for.

        Returns
        -------
        :class:`discord.Message`
            The message that was sent to the user.
        """
        if isinstance(command, DuckGroup):
            return await self.send_group_help(command)
        view = HelpCommand(
            parent=self.context.bot, command=command, author=self.context.author
        )
        return await self.context.send(embed=view.embed, view=view)

    async def command_not_found(self, string: str, /) -> str:
        """|coro|

        A coroutine called when a command is not found. This will return any matches that are similar
        to what was searched for.

        Parameters
        ----------
        string: :class:`str`
            The command that the user tried to search for but couldn't find.

        Returns
        -------
        :class:`str`
            The string that will be sent to the user alerting them that the command was not found.
        """
        matches = [c.qualified_name for c in self.bot.commands]
        matches.extend(c.qualified_name for c in self.bot.cogs.values())

        maybe_found = await self.bot.wrap(process.extractOne, string, matches)
        return f'The command / group called "{string}" was not found. Maybe you meant `{self.context.prefix}{maybe_found[0]}`?'

    async def subcommand_not_found(
        self, command: DuckCommand[Any, ..., Any], string: str, /
    ) -> str:
        """|coro|

        A coroutine called when a subcommand is not found. This will return any matches that are similar
        to what was searched for.

        Parameters
        ----------
        command: :class:`DuckCommand`
            The command that doesn't have a subcommand requested.
        string: :class:`str`
            The command that the user tried to search for but couldn't find.

        Returns
        -------
        :class:`str`
            The string that will be sent to the user alerting them that the command was not found.
        """

        fmt = [f'There was no subcommand named "{string}" found on that command.']
        if isinstance(command, DuckGroup):
            maybe_found = await self.bot.wrap(
                process.extractOne, string, [c.qualified_name for c in command.commands]
            )
            fmt.append(f"Maybe you meant `{maybe_found[0]}`?")

        return "".join(fmt)

    async def on_help_command_error(
        self, ctx: DuckContext, error: commands.CommandError, /
    ) -> discord.Message:
        """|coro|

        A coroutine called when an error occurs while displaying the help command.

        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context of the command.
        error: :class:`commands.CommandError`
            The error that occurred.

        Returns
        -------
        :class:`discord.Message`
            The message that was sent to the user.
        """
        if isinstance(error, DuckBotNotStarted):
            return await ctx.send(
                f"Oop! Duck bot is not started yet, give me a minute and try again."
            )

        await ctx.bot.exceptions.add_error(error=error, ctx=ctx)
        return await ctx.send(
            "I ran into a new error! I apologize for the inconvenience."
        )


async def setup(bot: DuckBot) -> None:
    bot.help_command = DuckHelp()


async def teardown(bot: DuckBot) -> None:
    bot.help_command = commands.MinimalHelpCommand()

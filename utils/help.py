from __future__ import annotations


import copy
import logging
from fuzzywuzzy import process
from functools import partial
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
from bot import DuckBot

if TYPE_CHECKING:
    from .base_cog import DuckCog
    
    ParentType = Union[DuckBot, _Parentable, discord.ui.View] # type: ignore
    
QUESTION_MARK = '\N{BLACK QUESTION MARK ORNAMENT}'
HOME = '\N{HOUSE BUILDING}'
NON_MARDKWON_INFORMATION_SOURCE = '\N{INFORMATION SOURCE}'

log = logging.getLogger('Duckbot.utils.help')

async def _interaction_check(view: discord.ui.View, interaction: discord.Interaction) -> Optional[bool]:
    # NOTE: Implement this in a bit
    #if not getattr(view, 'author', None) == interaction.user:
    #    return await interaction.response.edit_message('Hey! This isn\'t yours!', ephemeral=True)
    
    return True


class _Parentable(Protocol):
    parent: Union[_Parentable, DuckBot]
    bot: Optional[DuckBot] 
    

def _find_bot(parentable: ParentType) -> DuckBot:
    base = parentable
    
    if isinstance(parentable, DuckBot):
        return parentable
    if (db := getattr(parentable, 'bot', None)):
        return db
    
    while hasattr(parentable, 'parent'):
        if isinstance(parentable, DuckBot):
            return parentable

        if (db := getattr(parentable, 'bot', None)):
            return db
        
        parentable = parentable.parent # type: ignore # Can not use isinstance for DuckBot so we have to ignore this

    raise DuckNotFound(f'Could not find DuckBot from base parentable {base}, {repr(base)}.')

def _walk_through_parents(parentable: ParentType) -> Generator[None, None, ParentType]:
    if isinstance(parentable, DuckBot):
        yield from []
    
    while hasattr(parentable, 'parent'):
        yield parentable
        parentable = getattr(parentable, 'parent') 


class Stop(discord.ui.Button):
    def __init__(self, parent: discord.ui.View) -> None:
        self.parent: discord.ui.View = parent
        super().__init__(
            style=discord.ButtonStyle.danger,
            label='Stop',
        )
    
    async def callback(self, interaction: discord.Interaction) -> Any:
        for child in self.parent.children:
            child.disabled = True # type: ignore
        
        self.parent.stop()
        return await interaction.response.edit_message(view=self.parent)


class GoHome(discord.ui.Button):
    def __init__(self, parent: ParentType) -> None:
        self.parent: ParentType = parent
        self.bot: DuckBot = _find_bot(parent)
        super().__init__(
            label='Go Home',
            emoji=HOME,
        )
    
    async def _get_help_from_parent(self) -> HelpView:
        main_parent: Optional[DuckHelp] = discord.utils.find(lambda p: isinstance(p, DuckHelp), _walk_through_parents(self.parent))
        if main_parent:
            clean_mapping = await main_parent._filter_mapping({ # type: ignore # We're gonna pretend we're using TS today
                cog: cog.get_commands() for cog in self.bot.cogs.values()
            }) 
        else:
            clean_mapping = {cog: None for cog in self.bot.cogs.values()}
        
        return HelpView(parent=self.parent, cogs=clean_mapping.keys())
        
    async def callback(self, interaction: discord.Interaction) -> None:
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
                

class CommandSelecter(discord.ui.Select):
    def __init__(self, *, parent: ParentType, commands: List[commands.Command]) -> None:
        self.parent: ParentType = parent
        
        self._command_mapping: Mapping[str, commands.Command] = {c.qualified_name: c for c in commands}
        super().__init__(
            placeholder='Select a command...',
            options=[
                discord.SelectOption(
                    label=command.qualified_name,
                    value=command.qualified_name
                )
                for command in commands
            ]
        )
        
    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values
        if not selected:
            return
        
        command = self._command_mapping[selected[0]]
        if isinstance(command, commands.Group):
            view = HelpGroup(parent=self.parent, group=command)
        else:
            view = HelpCommand(parent=self.parent, command=command) # type: ignore
        
        return await interaction.response.edit_message(embed=view.embed, view=view)


class HelpGroup(discord.ui.View):
    def __init__(self, *, parent: ParentType, group: commands.Group) -> None:
        super().__init__()
        
        self.parent: ParentType = parent
        self.group: commands.Group = group
        self.bot: DuckBot = _find_bot(parent)
        
        group_commands = list(group.commands)
        for command in group_commands:
            if isinstance(command, commands.Group):
                group_commands.extend(command.commands)
        
        for chunk in self.bot.chunker(group_commands, size=20):
            self.add_item(CommandSelecter(parent=self, commands=chunk)) # type: ignore
        
        self.add_item(GoHome(self))
        self.add_item(Stop(self))
        
    @property
    def embed(self) -> discord.Embed:
        group = self.group
        embed = discord.Embed(
            title=group.qualified_name,
            description=group.help,
        )
        embed.add_field(name='How to use', value=group.signature or 'No signature', inline=False)
        embed.add_field(name='Subcommands', value=human_join([f'`{c.name}`' for c in group.commands], final='and'), inline=False)
        embed.set_footer(text=f'Select a subcommand to get more information about it.')
        return embed
    
    
class HelpCommand(discord.ui.View):
    def __init__(self, *, parent: ParentType, command: commands.Command) -> None:
        super().__init__()
        
        self.parent: ParentType = parent
        self.command: commands.Command = command
        self.bot: DuckBot = _find_bot(parent)
        self.add_item(GoHome(self))
        self.add_item(Stop(self))
    
    @property
    def embed(self) -> discord.Embed:
        # Maybe statistics here?
        # Also leo style this plz
        
        command = self.command
        embed = discord.Embed(
            title=command.qualified_name,
            description=command.help,
        )
        embed.add_field(name='How to use', value=command.signature or 'No signature', inline=False)
        
        return embed


class HelpCog(discord.ui.View):
    def __init__(self, *, parent: ParentType, cog: DuckCog) -> None:
        super().__init__()
        
        self.parent: ParentType = parent
        self.bot: DuckBot = _find_bot(parent)
        self.cog: DuckCog = cog
        
        # Want to show all subcommands as well, so it's a bit easier for the user
        # to select what they want.
        cog_commands = cog.get_commands()
        for command in cog_commands:
            if isinstance(command, commands.Group):
                cog_commands.extend(command.commands)
        
        for item in self.bot.chunker(cog_commands, size=20):
            self.add_item(CommandSelecter(parent=self, commands=list(item))) # type: ignore
        
        self.add_item(GoHome(self))
        self.add_item(Stop(self))

    @property
    def embed(self) -> discord.Embed:
        cog = self.cog
        embed = discord.Embed(
            title=f'{cog.emoji or QUESTION_MARK} {cog.qualified_name}',
            description=cog.description,
        )
        embed.add_field(
            name='Commands',
            value=human_join([f'`{command.qualified_name}`' for command in cog.get_commands()], final='and')
        )
        embed.set_footer(text='Use the dropdown to get more info on a command.')
        return embed


class HelpSelect(discord.ui.Select):
    def __init__(self, *, parent: ParentType, cogs: List[DuckCog]) -> None:
        self.parent: ParentType = parent
        self._cog_mapping: Mapping[int, DuckCog] = {c.id: c for c in cogs}
        
        super().__init__(
            placeholder='Select a group...',
            options=[
                discord.SelectOption(
                    label=cog.qualified_name,
                    value=str(cog.id),
                    description=cog.brief or 'No description...',
                    emoji=cog.emoji
                )
                for cog in cogs
            ]
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values
        if not selected:
            return
        
        current_cog = self._cog_mapping[int(selected[0])]
        view = HelpCog(parent=self.parent, cog=current_cog)
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
        'bot',
        '_cs_embed',
    )
    
    def __init__(
        self, 
        /,
        *,
        parent: ParentType, 
        cogs: List[DuckCog],
    ) -> None:
        super().__init__()
        self.bot: DuckBot = _find_bot(parent)
        self.add_item(HelpSelect(parent=self, cogs=cogs))
        self.add_item(Stop(self))
    
    @discord.utils.cached_slot_property('_cs_embed')
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: The master embed for this view."""
        getting_help = [
            'Use `db.help <command>` for more info on a command.',
            'There is also `db.help <command> [subcommand]`.',
            'Use `db.help <category>` for more info on a category.',
            'You can also use the menu below to view a category.',
        ]
        getting_support = [
            'To get help, you can join my support server.',
            f'{SERVERS_ICON} https://discord.gg/TdRfGKg8Wh',
            '📨 You can also send me a DM if you prefer to.'
        ]
        
        embed = discord.Embed(
            title='DuckBot Help Menu',
            description='Hello, I\'m DuckBot! A multi-purpose bot with a lot of features.'
        )
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
        embed.add_field(name='Getting Help', value='\n'.join(getting_help), inline=False)
        embed.add_field(name='Getting Support', value='\n'.join(getting_support), inline=False)
        embed.add_field(name='Who am I?', value=f'I\'m DuckBot, a multipurpose bot created and maintained by {GITHUB}[LeoCx1000](https://github.com/LeoCx1000).'
                        'and assisted by [NextChai](https://github.com/NextChai). You can use me to play games, moderate your server, mess with some images and more! '
                        'Check out all my features using the dropdown below.\n\n'
                        f'I\'ve been online since {self.bot.uptime_timestamp}.\n'
                        f'You can find my source code on {GITHUB}[GitHub](https://github.com/LeoCx1000/discord-bots/tree/rewrite).', inline=False)
        embed.add_field(name='Support DuckBot', value='If you like DuckBot, you can support by voting here:\n'
                        '⭐ https://top.gg/bot/788278464474120202 ⭐', inline=False)
        embed.set_footer(text=f'{NON_MARDKWON_INFORMATION_SOURCE} For more info on a command press {QUESTION_MARK} help.')
        return embed
    
    
class DuckHelp(commands.HelpCommand):
    if TYPE_CHECKING:
        context: DuckContext[DuckBot]
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs, verify_checks=True)
        
    @property
    def bot(self) -> DuckBot:
        if (bot := getattr(self, '_bot', None)):
            return bot
        
        return self.context.bot 
    
    @bot.setter
    def bot(self, new: DuckBot) -> None:
        self._bot = new
        
    async def _filter_mapping(self, mapping: Mapping[Optional[DuckCog], List[commands.Command]]) -> Mapping[Optional[DuckCog], List[commands.Command]]:
        commands = sum(mapping.values(), [])
        await self.filter_commands(commands)
        
        cogs = {}
        for command in commands:
            if not command.cog:
                continue
            
            key = command.cog
            if key not in cogs:
                cogs[key] = [command]
            else:
                cogs[key].append(command)
        
        return cogs
    
    async def send_bot_help(self, mapping: Mapping[Optional[DuckCog], List[commands.Command]]) -> discord.Message:
        self.bot = self.context.bot
        mapping = await self._filter_mapping(mapping)
        view = HelpView(parent=self.bot, cogs=list(cog for cog in mapping if cog)) 
        return await self.context.send(embed=view.embed, view=view)
    
    async def send_cog_help(self, cog: DuckCog, /) -> discord.Message:
        
        # We need to filter the command ourselves. To do this, let's
        # make a copy of the cog and fuck it a bit.
        keep_commands = [c for c in cog.__cog_commands__ if c.parent]
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        
        new_cog = copy.copy(cog)
        new_cog.__cog_commands__ = keep_commands + filtered
        view = HelpCog(parent=self.context.bot, cog=new_cog)
        return await self.context.send(embed=view.embed, view=view)

    async def send_group_help(self, group: commands.Group[Any, ..., Any], /) -> discord.Message:
        view = HelpGroup(parent=self.context.bot, group=group)
        return await self.context.send(embed=view.embed, view=view)
    
    async def send_command_help(self, command: commands.Command[Any, ..., Any], /) -> discord.Message:
        view = HelpCommand(parent=self.context.bot, command=command)
        return await self.context.send(embed=view.embed, view=view)
    
    async def command_not_found(self, string: str, /) -> str:
        maybe_found = await self.bot.wrap(process.extractOne, string, [c.qualified_name for c in self.bot.commands])
        return f'The command called "{string}" was not found. Maybe you meant `{self.context.prefix}{maybe_found[0]}`?'
    
    async def subcommand_not_found(self, command: commands.Command[Any, ..., Any], string: str, /) -> str:
        fmt = [f'There was no subcommand named "{string}" found on that command.']
        if isinstance(command, commands.Group):
            maybe_found = await self.bot.wrap(process.extractOne, string, [c.qualified_name for c in command.commands])
            fmt.append(f'Maybe you meant `{maybe_found[0]}`?')
        
        return ''.join(fmt)
    
    async def on_help_command_error(self, ctx: DuckContext, error: commands.CommandError, /) -> discord.Message:
        if isinstance(error, DuckBotNotStarted):
            return await ctx.send(f'Oop! Duck bot is not started yet, give me a minute and try again.')
        
        log.warning('New error in help command', exc_info=error)
        return await ctx.send('I ran into a new error! I apologize for the inconvenience.')


async def setup(bot: DuckBot) -> None:
    bot.help_command = DuckHelp()

async def teardown(bot: DuckBot) -> None:
    bot.help_command = commands.MinimalHelpCommand()
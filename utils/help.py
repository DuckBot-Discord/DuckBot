from __future__ import annotations

from functools import partial
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    Tuple,
    Union,
    Callable,
)

import discord
from discord.ext import commands

from .constants import SERVERS_ICON, GITHUB, INFORMATION_SOURCE

if TYPE_CHECKING:
    from bot import DuckBot
    from utils import DuckCog
    
InteractionCheck = Callable[[discord.ui.View, discord.Interaction], Optional[bool]]

QUESTION_MARK = '\N{BLACK QUESTION MARK ORNAMENT}'
HOME = '\N{HOUSE BUILDING}'


async def _interaction_check(view: discord.ui.View, interaction: discord.Interaction) -> Optional[bool]:
    # NOTE: Implement this in a bit
    #if not getattr(view, 'author', None) == interaction.user:
    #    return await interaction.response.send_message('Hey! This isn\'t yours!', ephemeral=True)
    
    return True
    
    
class HelpSelect(discord.ui.Select):
    """The main :class:`~discord.ui.Select` class
    that is shown on :class:`HelpView`.
    
    Attributes
    ----------
    parent: :class:`HelpView`
        The parent :class:`HelpView` instance.
    """
    __slots__: Tuple[str, ...] = (
        'parent',
        '_cogs',
    )
    
    def __init__(self, parent: HelpView, cogs: List[DuckCog]) -> None:
        super().__init__(
            custom_id='_db_help_select_1',
            placeholder='Select a command group...',
            options=[
                discord.SelectOption(label=cog.qualified_name, value=cog.qualified_name, emoji=cog.emoji) for cog in cogs
            ]
        )
        self.parent: HelpView = parent
        self._cogs: List[DuckCog] = cogs
    
    async def callback(self, interaction: discord.Interaction) -> None:
        raise NotImplementedError()


class HelpHome(discord.ui.Button):
    """
    A simple button to return to the home page.
    
    Attributes
    ----------
    parent: :class:`HelpView`
        The parent :class:`HelpView` instance.
    """
    __slots__: Tuple[str, ...] = (
        'parent',
    )
    
    def __init__(self, parent: Union[HelpCog, HelpCommand, HelpView]) -> None:
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji=HOME,
            label='Go Back'
        )
        
        while hasattr(parent, 'parent'):
            parent = getattr(parent, 'parent')
        
        # At this point we should have found the root parent instance
        self.parent: HelpView = parent # type: ignore
        if not isinstance(self.parent, HelpView):
            raise RuntimeError(f'Parent {self.parent} has no parent attribute')
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """|coro|
        
        The main callback for the button. Will edit the current message to go home.
        
        Parameters
        ----------
        interaction: :class:`~discord.Interaction`
            The interaction that was created from the button press.
        """
        return await interaction.response.edit_message(embed=self.parent.embed, view=self.parent)
    

class AboutHelpView(discord.ui.View):
    """
    A view to show the about page. You can get to this by pressing
    the "? Help" button on the home screen.
    
    Attributes
    ----------
    parent: :class:`HelpView`
        The parent :class:`HelpView` instance.
    """
    __slots__: Tuple[str, ...] = (
        'parent',
        '_cs_embed'
    )
    
    def __init__(self, parent: HelpView) -> None:
        super().__init__()
        self.parent: HelpView = parent
        self.add_item(HelpHome(parent))
    
    @discord.utils.cached_slot_property('_cs_embed')
    def embed(self) -> discord.Embed:
        raise NotImplementedError
    
        

class HelpCog(discord.ui.View):
    """Represents a Cog's help command within the help menu.
    
    Can be created via :class:`HelpView` or if a user requests to see
    this cogs help.
    
    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance.
    cog: :class:`DuckCog`
        The cog that is being displayed.
    parent: :class:`HelpView`
        The parent help view.
    """
    __slots__: Tuple[str, ...] = (
        'bot',
        'cog',
        'parent',
        'interaction_check',
        '_cs_embed',
    )
    
    def __init__(self, bot: DuckBot, cog: DuckCog,parent: Optional[HelpView] = None) -> None:
        self.bot: DuckBot = bot
        self.cog: DuckCog = cog
        self.parent: HelpView = parent or HelpView(bot)
        self.interaction_check: InteractionCheck = partial(_interaction_check, self) # type: ignore
    
    @discord.utils.cached_slot_property('_cs_embed')
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: The master embed for this view."""
        raise NotImplementedError('This method must be implemented.')


class HelpCommand(discord.ui.View):
    """
    Represents a command's help menu.
    
    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance.
    command: :class:`commands.Command`
        The command that is being displayed.
    """
    __slots__: Tuple[str, ...] = (
        'bot',
        'command',
        'interaction_check',
        '_cs_embed',
    )
    
    def __init__(self, bot: DuckBot, command: commands.Command) -> None:
        self.bot: DuckBot = bot
        self.command: commands.Command = command
        self.interaction_check: InteractionCheck = partial(_interaction_check, self) # type: ignore
    
    @discord.utils.cached_slot_property('_cs_embed')
    def embed(self) -> discord.Embed:
        """:class:`discord.Embed`: The master embed for this view."""
        raise NotImplementedError('This method must be implemented.')
        
        
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
        'interaction_check',
        '_cs_embed',
    )
    
    def __init__(self, bot: DuckBot) -> None:
        super().__init__()
        self.bot: DuckBot = bot
        self.add_item(HelpSelect(self, list(bot.cogs.values()))) # type: ignore
        
        self.interaction_check: InteractionCheck = partial(_interaction_check, self) # type: ignore
    
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
        embed.add_field(name='Getting Help', value='\n'.join(getting_help))
        embed.add_field(name='Getting Support', value='\n'.join(getting_support))
        embed.add_field(name='Who am I?', value=f'I\'m DuckBot, a multipurpose bot created and maintained by {GITHUB}[LeoCx1000](https://github.com/LeoCx1000).'
                        'and assisted by [NextChai](https://github.com/NextChai). You can use me to play games, moderate your server, mess with some images and more! '
                        'Check out all my features using the dropdown below.\n\n'
                        f'I\'ve been online since {self.bot.uptime_timestamp}.\n'
                        f'You can find my source code on {GITHUB}[GitHub](https://github.com/LeoCx1000/discord-bots/tree/rewrite).')
        embed.add_field(name='Support DuckBot', value='If you like DuckBot, you can support by voting here:\n'
                        '⭐ https://top.gg/bot/788278464474120202 ⭐')
        embed.set_footer(text=f'{INFORMATION_SOURCE} For more info on a command press {QUESTION_MARK} help.')
        return embed
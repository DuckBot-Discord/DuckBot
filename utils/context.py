from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Generic, 
    Tuple, 
    Optional,
    TypeVar
)

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord.message import Message
    from bot import DuckBot

from .translation_helpers import FormatString, TranslatedEmbed


__all__: Tuple[str, ...] = (
    'DuckContext',
    'tick',
)

BotT = TypeVar('BotT', bound='DuckBot')

def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
    """A function to convert a boolean value with label to an emoji with label.
        
    Parameters
    ----------
    opt: Optional[:class:`bool`]
        The boolean value to convert.
    label: Optional[:class:`str`]
        The label to use for the emoji.
    
    Returns
    -------
    :class:`str`
        The emoji with label.
    """
    lookup = {
        True: '\N{WHITE HEAVY CHECK MARK}',
        False: '\N{CROSS MARK}',
        None: '\N{BLACK QUESTION MARK ORNAMENT}'
    }
    emoji = lookup.get(opt, '\N{CROSS MARK}')
    if label is not None:
        return f'{emoji} {label}'

    return emoji


class ConfirmationView(discord.ui.View):
    def __init__(self, ctx: DuckContext, *, timeout: int = 60) -> None:
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value = None
        self.message: discord.Message | None = None
        self.ctx.bot.views.add(self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self) -> None:
        self.ctx.bot.views.discard(self)
        if self.message:
            for item in self.children:
                item.disabled = True # type: ignore
                
            await self.message.edit(content=f'Timed out waiting for a button press from {self.ctx.author}.', view=self)

    def stop(self) -> None:
        self.ctx.bot.views.discard(self)
        super().stop()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        assert interaction.message is not None
        
        self.value = True
        self.stop()
        await interaction.message.delete()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        assert interaction.message is not None
        
        self.value = False
        self.stop()
        await interaction.message.delete()


class DuckContext(commands.Context, Generic[BotT]):
    """The subclassed Context to allow some extra functionality."""
    if TYPE_CHECKING:
        bot: DuckBot
        guild: discord.Guild

    __slots__: Tuple[str, ...] = ()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.is_error_handled = False

    @staticmethod
    @discord.utils.copy_doc(tick)
    def tick(opt: Optional[bool], label: Optional[str] = None) -> str:
        return tick(opt, label)

    @discord.utils.cached_property
    def color(self) -> discord.Color:
        """:class:`~discord.Color`: Returns DuckBot's color, or the author's color. Falls back to blurple """
        def check(color):
            return color not in {discord.Color.default(), None}
        checks = (
            me_color if check(me_color := self.me.color) else None,
            you_color if check(you_color := self.author.color) else None,
            self.bot.color
        )

        result = discord.utils.find(lambda e: e, checks)
        if not result:
            raise RuntimeError('Unreachable code has been reached')

        return result

    async def get_locale(self) -> str:
        """|coro|
        Gets the locale to use for the translation.
        """
        return self.bot.validate_locale(
            await self.bot.pool.fetchval('SELECT locale FROM user_settings WHERE user_id = $1', self.author.id),
            default = self.bot.validate_locale(self.interaction.locale if self.interaction else None,
            default = self.bot.validate_locale(self.guild.preferred_locale if self.guild else None,
            default = 'en_us')))


    async def translate(self, translation_id: int, /, *args: Any, locale: str | discord.Locale | None = None) -> str:
        """|coro|
        Handles translating a translation ID.

        Parameters
        ----------
        translation_id: :class:`int`
            The translation ID to translate.
        args: :class:`Any`
            The arguments to pass to the translation.
        locale: Optional[:class:`str` | :class:`~discord.Locale`]
            The locale to use for the translation.
        """
        locale = locale or await self.get_locale()
        return await self.bot.translate(translation_id, *args, locale=locale)

    async def send(self, content: int | str | FormatString | None = None, *args: Any, **kwargs: Any) -> Message:
        """|coro|
        
        Sends a message to the invoking context's channel.

        View :meth:`~discord.ext.commands.Context.send` for more information of parameters.
        
        Returns
        -------
        :class:`~discord.Message`
            The message that was created.
        """
        if kwargs.get('embed') and kwargs.get('embeds'):
            raise ValueError('Cannot send both embed and embeds')
        
        locale = kwargs.pop('locale', await self.get_locale())

        embeds = kwargs.pop('embeds', []) or ([kwargs.pop('embed')] if kwargs.get('embed', None) else [])
        if embeds:
            for i, embed in enumerate(embeds):
                if isinstance(embed, TranslatedEmbed):
                    embed = await embed.translate(self.bot, locale)
                    embeds[i] = embed
                if embed.color is None:
                    # Made this the bot's vanity colour, although we'll
                    # be keeping self.color for other stuff like userinfo
                    embed.color = self.bot.color

            kwargs['embeds'] = embeds
        
        if isinstance(content, int):
            content = await self.translate(content, *args, locale=locale)
        elif isinstance(content, FormatString):
            content = await self.translate(content.id, *content.args, locale=locale)
            

        return await super().send(content, **kwargs)

    async def confirm(self, content=None, /, *, timeout: int = 30, **kwargs) -> bool | None:
        """|coro|

        Prompts a confirmation message that users can confirm or deny.

        Parameters
        ----------
        content: str | None
            The content of the message. Can be an embed.
        timeout: int | None
            The timeout for the confirmation.
        kwargs:
            Additional keyword arguments to pass to `self.send`.

        Returns
        -------
        :class:`bool`
            Whether the user confirmed or not.
            None if the view timed out.
        """
        view = ConfirmationView(self, timeout=timeout)
        try:
            view.message = await self.channel.send(content, **kwargs, view=view)
            await view.wait()
            return view.value
        except discord.HTTPException:
            view.stop()
            return None


async def setup(bot: DuckBot) -> None:
    """Sets up the DuckContext class.

    Parameters
    ----------
    bot: DuckBot
        The bot to set up the DuckContext class for.
    """
    bot._context_cls = DuckContext


async def teardown(bot: DuckBot) -> None:
    """Tears down the DuckContext class.

    Parameters
    ----------
    bot: DuckBot
        The bot to tear down the DuckContext class for.
    """
    bot._context_cls = commands.Context

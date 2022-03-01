from __future__ import annotations

import contextlib
import typing
import cachetools
from typing import (
    TYPE_CHECKING,
    List,
    Dict, 
    Any,
    Optional,
    Tuple,
    Type,
    TypeVar
)

import discord
from discord.ext import commands

from utils import DuckCog
from utils.context import DuckContext

T = TypeVar('T')

fm_dt = discord.utils.format_dt


class Page(typing.NamedTuple):
    """Represents a page of news."""
    news_id: int
    title: str
    content: str
    author_id: int


class NewsFeed:
    """
    Represents a news feed that the user can navigate through.
    
    Attributes
    ----------
    news: List[:class:`Page`]
        A list of news pages.
    max_pages: :class:`int`
        The maximum number of pages in the feed.
    """
    __slots__: Tuple[str, ...] = (
        'news',
        'max_pages', 
        '_current_page',
    )

    def __init__(self, news: List[Dict[str, Any]]) -> None:
        self.news: List[Page] = [Page(**n) for n in news]
        self.max_pages = len(news)
        self._current_page = 0

    def advance(self) -> None:
        """Advance to the next page."""
        self._current_page += 1
        if self._current_page >= self.max_pages:
            self._current_page = 0

    def go_back(self) -> None:
        """Go back to the previous page."""
        self._current_page -= 1
        if self._current_page < 0:
            self._current_page = self.max_pages - 1

    @property
    def previous(self) -> Page:
        """Get the previous page."""
        number = self._current_page - 1 if self._current_page > 0 else self.max_pages - 1
        return self.news[number]

    @property
    def current(self) -> Page:
        """Get the current page"""
        return self.news[self._current_page]

    @property
    def next(self) -> Page:
        """Get the next page"""
        number = self._current_page + 1 if self._current_page + 1 < self.max_pages else 0
        return self.news[number]

    @property
    def current_index(self):
        """Get the current index of the paginator."""
        return self._current_page


class NewsViewer(discord.ui.View):
    """The news viewer View.
    
    This class implements the functionality of the news viewer,
    allowing the user to navigate through the news feed.
    
    Attributes
    ----------
    ctx: :class:`DuckContext`
        The context of the command.
    news: :class:`NewsFeed`
        The news feed.
    """
    if TYPE_CHECKING:
        message: discord.Message
    
    def __init__(self, ctx: DuckContext, news: List[Dict[str, Any]]):
        super().__init__()
        self.ctx: DuckContext = ctx
        self.news = NewsFeed(news)
        
    async def interaction_check(self, interaction: discord.Interaction) -> Optional[bool]:
        """|coro|
        
        Used to check if the interaction is valid. If it isn't the user that selected
        the button won't be allowed to interact with the menu.
        
        Parameters
        ----------
        interaction: :class:`discord.Interaction`
            The interaction to check.
        
        Returns
        -------
        Optional[:class:`bool`] 
            Whether the interaction is valid.
        """
        val = interaction.user == self.ctx.author
        if not val:
            return await interaction.response.send_message(content='Hey! You can\'t do that!')
        
        return val

    @cachetools.cached(cachetools.LRUCache(maxsize=10))
    def get_embed(self, page: Page) -> discord.Embed:
        """:class:`discord.Embed`: Used to get the embed for the current page."""
        time = discord.utils.snowflake_time(page.news_id)
        
        embed = discord.Embed(title=f"\N{NEWSPAPER} {fm_dt(time)} ({fm_dt(time, 'R')})")
        embed.add_field(name=page.title, value=page.content)
        
        author = self.ctx.bot.get_user(page.author_id)
        if author:
            embed.set_footer(text=f"ID: {page.news_id} - Authored by {author}", icon_url=author.display_avatar.url)
            
        return embed

    @staticmethod
    def format_snowflake(snowflake: int) -> str:
        """:class:`str`: Used to format a snowflake."""
        date = discord.utils.snowflake_time(snowflake)
        return date.strftime("%d %b %Y %H:%M")

    @discord.ui.button(style=discord.ButtonStyle.blurple, label='\u226a')
    async def previous(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """|coro|
        
        Used to go back to the previous page.
        
        Parameters
        ----------
        button: :class:`discord.ui.Button`
            The button that was pressed.
        interaction: :class:`discord.Interaction`
            The interaction that was created.
        """
        self.news.advance()
        page = self.news.current
        self.update_labels()
        return await interaction.response.edit_message(embed=self.get_embed(page), view=self)

    @discord.ui.button(style=discord.ButtonStyle.red)
    async def current(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """|coro|
        
        Used to stop the news viewer.
        
        Parameters
        ----------
        button: :class:`discord.ui.Button`
            The button that was pressed.
        interaction: :class:`discord.Interaction`
            The interaction that was created.
        """
        self.stop()
        await self.message.delete()
        
        with contextlib.suppress(discord.HTTPException):
            await self.ctx.message.add_reaction(self.ctx.bot.done_emoji)

    @discord.ui.button(style=discord.ButtonStyle.blurple, label='\u226b')
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        """|coro|
        
        Used to go to the next page.
        
        Parameters
        ----------
        button: :class:`discord.ui.Button`
            The button that was pressed.
        interaction: :class:`discord.Interaction`
            The interaction that was created.
        """
        self.news.go_back()
        page = self.news.current
        self.update_labels()
        await interaction.response.edit_message(embed=self.get_embed(page), view=self)

    def update_labels(self):
        """Used to update the internal cache of the view, it will update the labels of the buttons."""
        previous_page_num = self.news.max_pages - self.news.news.index(self.news.previous)
        self.next.disabled = previous_page_num == 1

        self.current.label = self.news.max_pages - self.news.current_index

        next_page_num = self.news.max_pages - self.news.news.index(self.news.next)
        self.previous.disabled = next_page_num == self.news.max_pages

    @classmethod
    async def start(cls: Type[T], ctx: DuckContext, news: List[Dict[str, Any]]) -> T:
        """|coro|
        
        Used to start the view and build internal cache.
        
        Parameters
        ----------
        ctx: :class:`DuckContext`
            The context of the command.
        news: :class:`List[Dict[:class:`str`, Any]]`
            The news feed.
            
        Returns
        -------
        :class:`NewsViewer`
            The news viewer after it has finished.
        """
        new = cls(ctx, news)
        new.update_labels()
        new.message = await new.ctx.send(embed=new.get_embed(new.news.current), view=new)
        await new.wait()
        return new
        
        
class News(DuckCog):
    """
    News cog
    """

    @commands.group(invoke_without_command=True)
    async def news(self, ctx: DuckContext):
        """|coro|
        
        Opens the bot's news feed.
        """
        news = await ctx.bot.pool.fetch("SELECT * FROM news ORDER BY news_id DESC")
        if not news:
            return await ctx.send("No news has been posted yet.")
        
        await NewsViewer.start(ctx, news)

    @news.command(hidden=True)
    async def add(self, ctx: DuckContext, title, *, content: str):
        """|coro| 
        
        Adds a news item to the news feed

        Parameters
        ----------
        title: :class:`str`
            The title of the news item (up to 256 characters)
        content: :class:`str`
            The content of the news item (up to 1024 characters)
        """
        if not await ctx.bot.is_owner(ctx.author):
            return await ctx.invoke(self.news)

        async with ctx.bot.safe_connection() as conn:
            await conn.execute("INSERT INTO news (news_id, title, content, author_id) VALUES ($1, $2, $3, $4)",
                               ctx.message.id, title, content, ctx.author.id)
            
        with contextlib.suppress(discord.HTTPException):
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @news.command(hidden=True)
    async def remove(self, ctx: DuckContext, news_id: int):
        """|coro| 
        
        Removes a news item from the news feed

        Parameters
        ----------
        news_id: :class:`int`
            The snowflake ID of the news item to remove
        """
        if not await ctx.bot.is_owner(ctx.author):
            return await ctx.invoke(self.news)

        async with ctx.bot.safe_connection() as conn:
            query = """
            WITH deleted AS (
                DELETE FROM news WHERE news_id = $1 RETURNING *
            ) SELECT COUNT(*) FROM deleted
            """
            removed = await conn.fetchval(query, news_id)
            
        with contextlib.suppress(discord.HTTPException):
            # Leo really...
            await ctx.message.add_reaction(f"{removed}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}")

import collections
import contextlib
import functools
import typing

import cachetools
import discord
from discord.utils import format_dt as fm_dt
from discord import Interaction
from discord.ui import Button
from typing import List, Dict, Any

from utils import DuckCog
from discord.ext import commands

from utils.context import DuckContext


class Page(typing.NamedTuple):
    news_id: int
    title: str
    content: str
    author_id: int


class NewsFeed:
    __slots__ = ('news', 'max_pages', '_current_page')

    def __init__(self, news: List[Dict[str, Any]]):
        self.news: List[Page] = [Page(**n) for n in news]
        self.max_pages = len(news)
        self._current_page = 0

    def advance(self):
        self._current_page += 1
        if self._current_page >= self.max_pages:
            self._current_page = 0

    def go_back(self):
        self._current_page -= 1
        if self._current_page < 0:
            self._current_page = self.max_pages - 1

    @property
    def previous(self) -> Page:
        number = self._current_page - 1 if self._current_page > 0 else self.max_pages - 1
        return self.news[number]

    @property
    def current(self) -> Page:
        return self.news[self._current_page]

    @property
    def next(self) -> Page:
        number = self._current_page + 1 if self._current_page + 1 < self.max_pages else 0
        return self.news[number]

    @property
    def current_index(self):
        return self._current_page


class NewsViewer(discord.ui.View):
    def __init__(self, ctx: DuckContext, news: List[Dict[str, Any]]):
        super().__init__()
        self.message: typing.Optional[discord.Message] = None
        self.ctx: DuckContext = ctx
        self.news = NewsFeed(news)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user == self.ctx.author

    @functools.cache
    def get_embed(self, page: Page):
        time = discord.utils.snowflake_time(page.news_id)
        embed = discord.Embed(title=f"\N{NEWSPAPER} {fm_dt(time)} ({fm_dt(time, 'R')})")
        embed.add_field(name=page.title, value=page.content)
        author = self.ctx.bot.get_user(page.author_id)
        if author:
            embed.set_footer(text=f"ID: {page.news_id} - Authored by {author}", icon_url=author.display_avatar.url)
        return embed

    @staticmethod
    def format_snowflake(snowflake: int):
        date = discord.utils.snowflake_time(snowflake)
        return date.strftime("%d %b %Y %H:%M")

    @discord.ui.button(style=discord.ButtonStyle.blurple,
                       label='\u226a')
    async def previous(self, _, interaction: Interaction):
        self.news.advance()
        page = self.news.current
        self.update_labels()
        await interaction.response.edit_message(embed=self.get_embed(page), view=self)

    @discord.ui.button(style=discord.ButtonStyle.red)
    async def current(self, _, interaction: Interaction):
        self.stop()
        await self.message.delete()
        with contextlib.suppress(discord.HTTPException):
            await self.ctx.message.add_reaction(self.ctx.bot.done_emoji)

    @discord.ui.button(style=discord.ButtonStyle.blurple,
                       label='\u226b')
    async def next(self, _, interaction: Interaction):
        self.news.go_back()
        page = self.news.current
        self.update_labels()
        await interaction.response.edit_message(embed=self.get_embed(page), view=self)

    def update_labels(self):
        previous_page_num = self.news.max_pages - self.news.news.index(self.news.previous)
        self.next.disabled = previous_page_num == 1

        self.current.label = self.news.max_pages - self.news.current_index

        next_page_num = self.news.max_pages - self.news.news.index(self.news.next)
        self.previous.disabled = next_page_num == self.news.max_pages

    async def start(self):
        self.update_labels()
        self.message = await self.ctx.send(embed=self.get_embed(self.news.current), view=self)

class News(DuckCog):
    """
    News cog
    """

    @commands.group(invoke_without_command=True)
    async def news(self, ctx: DuckContext):
        """Opens the bot's news feed"""
        news = await ctx.bot.pool.fetch("SELECT * FROM news ORDER BY news_id DESC")
        if not news:
            return await ctx.send("No news has been posted yet.")
        view = NewsViewer(ctx, news)
        await view.start()

    @news.command(hidden=True)
    async def add(self, ctx: DuckContext, title, *, content: str):
        """|coro| Adds a news item to the news feed

        Parameters
        ----------
        title: str
            The title of the news item (up to 256 characters)
        content: str
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
        """|coro| Removes a news item from the news feed

        Parameters
        ----------
        news_id: int
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
            await ctx.message.add_reaction(f"{removed}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}")

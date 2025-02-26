from __future__ import annotations

import contextlib
from typing import Optional, TypeVar

import discord

from utils import DuckCog, group
from ._news_viewer import NewsViewer
from utils import DuckContext

T = TypeVar('T')

fm_dt = discord.utils.format_dt


class News(DuckCog):
    """
    News cog
    """

    @group(invoke_without_command=True)
    async def news(self, ctx: DuckContext):
        """Opens the bot's news feed."""
        news = await ctx.bot.pool.fetch("SELECT * FROM news ORDER BY news_id DESC")
        if not news:
            return await ctx.send("No news has been posted yet.")

        await NewsViewer.start(ctx, news)

    @news.command(hidden=True)
    async def add(self, ctx: DuckContext, title: Optional[str] = None, *, content: Optional[str] = None):
        """Adds a news item to the news feed

        Parameters
        ----------
        title: Optional[:class:`str`]
            The title of the news item (up to 256 characters)
        content: Optional[:class:`str`]
            The content of the news item (up to 1024 characters)
        """
        if not await ctx.bot.is_owner(ctx.author):
            return await self.news(ctx)

        async with ctx.bot.safe_connection() as conn:
            await conn.execute(
                "INSERT INTO news (news_id, title, content, author_id) VALUES ($1, $2, $3, $4)",
                ctx.message.id,
                title,
                content,
                ctx.author.id,
            )

        try:
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        except discord.HTTPException:
            with contextlib.suppress(discord.HTTPException):
                await ctx.send("\N{WHITE HEAVY CHECK MARK}")

    @news.command(hidden=True)
    async def remove(self, ctx: DuckContext, news_id: int):
        """Removes a news item from the news feed

        Parameters
        ----------
        news_id: :class:`int`
            The snowflake ID of the news item to remove
        """
        if not await ctx.bot.is_owner(ctx.author):
            return await self.news(ctx)

        async with ctx.bot.safe_connection() as conn:
            query = """
            WITH deleted AS (
                DELETE FROM news WHERE news_id = $1 RETURNING *
            ) SELECT COUNT(*) FROM deleted
            """
            removed = await conn.fetchval(query, news_id)

        try:
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}" if removed else "\N{WARNING SIGN}")
        except discord.HTTPException:
            with contextlib.suppress(discord.HTTPException):
                await ctx.send("\N{WHITE HEAVY CHECK MARK} deleted." if removed else "\N{WARNING SIGN} not found.")

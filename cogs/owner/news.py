from utils import DuckCog, DuckContext, HandleHTTPException, group


class NewsManagement(DuckCog):

    @group()
    async def news(self, ctx): ...

    @news.command(hidden=True, hybrid=False)
    async def add(self, ctx: DuckContext, title: str, *, content: str):
        """Adds a news item to the news feed

        Parameters
        ----------
        title: :class:`str`
            The title of the news item (up to 256 characters)
        content: :class:`str`
            The content of the news item (up to 1024 characters)
        """
        async with ctx.bot.safe_connection() as conn:
            await conn.execute(
                "INSERT INTO news (news_id, title, content, author_id) VALUES ($1, $2, $3, $4)",
                ctx.message.id,
                title,
                content,
                ctx.author.id,
            )

        async with HandleHTTPException(ctx):
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @news.command(hidden=True, hybrid=False)
    async def remove(self, ctx: DuckContext, news_id: int):
        """Removes a news item from the news feed

        Parameters
        ----------
        news_id: :class:`int`
            The snowflake ID of the news item to remove
        """
        async with ctx.bot.safe_connection() as conn:
            query = """
            WITH deleted AS (
                DELETE FROM news WHERE news_id = $1 RETURNING *
            ) SELECT COUNT(*) FROM deleted
            """
            removed = await conn.fetchval(query, news_id)

        async with HandleHTTPException(ctx):
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}" if removed else "\N{WARNING SIGN}")

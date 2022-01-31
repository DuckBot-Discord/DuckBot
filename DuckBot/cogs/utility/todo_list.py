import discord
import jishaku
from discord.ext import commands
from jishaku.paginators import WrappedPaginator

from DuckBot.__main__ import CustomContext
from DuckBot.helpers.paginator import PaginatedStringListPageSource, TodoListPaginator
from ._base import UtilityBase


class TodoList(UtilityBase):

    @commands.group()
    async def todo(self, ctx: CustomContext):
        """ Sends help about the to​do command """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @todo.command(name='add')
    async def todo_add(self, ctx: CustomContext, *, text: commands.clean_content):
        """ Adds an item to your to​do list """
        insertion = await self.bot.db.fetchrow(
            "INSERT INTO todo (user_id, text, jump_url, added_time) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (user_id, text) DO UPDATE SET user_id = $1 RETURNING jump_url, added_time",
            ctx.author.id, text[0:4000], ctx.message.jump_url, ctx.message.created_at)
        if insertion['added_time'] != ctx.message.created_at:
            embed = discord.Embed(description=f'⚠ **That is already added to your todo list:**'
                                              f'\n\u200b  → [added here]({insertion["jump_url"]}) '
                                              f'{discord.utils.format_dt(insertion["added_time"], style="R")}')
            return await ctx.send(embed=embed, footer=False)
        await ctx.send('**Added to todo list:**'
                       f'\n\u200b  → {text[0:200]}{"..." if len(text) > 200 else ""}')

    @todo.command(name='list', invoke_without_command=True)
    async def todo_list(self, ctx: CustomContext):
        """ Shows your to​do list """
        user = ctx.author
        entries = await self.bot.db.fetch(
            'SELECT text, added_time, jump_url FROM todo WHERE user_id = $1 ORDER BY added_time ASC', user.id)
        if not entries:
            return await ctx.send(embed=discord.Embed(description='Your to-do list is empty'))

        pages = jishaku.paginators.WrappedPaginator(prefix='', suffix='', max_size=4098)
        for page in [
            f'**[{i + 1}]({entries[i]["jump_url"]} \"Jump to message\"). ({discord.utils.format_dt(entries[i]["added_time"], style="R")}):** {entries[i]["text"]}'
            for i in range(len(entries))]:
            pages.add_line(page[0:4098])

        source = PaginatedStringListPageSource(pages.pages, ctx=ctx)
        view = TodoListPaginator(source, ctx=ctx, compact=True)
        await view.start()

    @todo.command(name='clear')
    async def todo_clear(self, ctx: CustomContext):
        """ Clears all your to​do entries """
        response = await ctx.confirm('Are you sure you want to clear your todo list?', return_message=True)
        if response[0] is True:
            count = await self.bot.db.fetchval(
                'WITH deleted AS (DELETE FROM todo WHERE user_id = $1 RETURNING *) SELECT count(*) FROM deleted;',
                ctx.author.id)
            return await response[1].edit(content=f'✅ **|** Done! Removed **{count}** entries.', view=None)
        await response[1].edit(content='❌ **|** cancelled! Removed **0** entries.', view=None)

    @todo.command(name='remove')
    async def todo_remove(self, ctx: CustomContext, index: int):
        """ Removes one of your to​do list entries """
        entries = await self.bot.db.fetch(
            'SELECT text, added_time FROM todo WHERE user_id = $1 ORDER BY added_time ASC', ctx.author.id)
        try:
            to_delete = entries[index - 1]
        except IndexError:
            raise commands.BadArgument(f'⚠ **|** You do not have a task with index **{index}**')
        await self.bot.db.execute("DELETE FROM todo WHERE (user_id, text) = ($1, $2)", ctx.author.id, to_delete['text'])
        return await ctx.send(
            f'**Deleted** task number **{index}**! - created at {discord.utils.format_dt(to_delete["added_time"], style="R")}'
            f'\n\u200b  → {to_delete["text"][0:1900]}{"..." if len(to_delete["text"]) > 1900 else ""}')

    @todo.command(name='edit')
    async def todo_edit(self, ctx: CustomContext, index: int, *, text: commands.clean_content):
        """ Edits one of your to​do list entries """
        entries = await self.bot.db.fetch(
            'SELECT text, added_time FROM todo WHERE user_id = $1 ORDER BY added_time ASC', ctx.author.id)
        try:
            to_delete = entries[index - 1]
        except KeyError:
            raise commands.BadArgument(f'⚠ **|** You do not have a task with index **{index}**')

        await self.bot.db.execute('UPDATE todo SET text = $4, jump_url = $3 WHERE user_id = $1 AND text = $2',
                                  ctx.author.id, to_delete['text'], ctx.message.jump_url, text)

        return await ctx.send(
            f'✏ **|** **Modified** task number **{index}**! - created at {discord.utils.format_dt(to_delete["added_time"], style="R")}'
            f'\n\u200b  → {text[0:200]}{"..." if len(to_delete["text"]) > 200 else ""}')


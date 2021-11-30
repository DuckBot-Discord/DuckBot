import logging
import re
import typing

import asyncpg
import discord
import tabulate
from discord.ext import commands
import jishaku.paginators
from ozbot import slash_utils
from ozbot.__main__ import Ozbot


def setup(bot):
    bot.add_cog(Coords(bot))


class Coords(slash_utils.ApplicationCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot: Ozbot = bot

    @slash_utils.slash_command(name='save', guild_id=706624339595886683)
    @slash_utils.describe(description='Annotation to add to the saved coordinates.',
                          x='X coordinate.', z='Z coordinate.')
    async def save_coords(self, ctx: slash_utils.Context, x: int, z: int, description: str):
        """ Saves a coordinate to the public database """
        try:
            await self.bot.db.execute("INSERT INTO coords (author, x, z, description) VALUES ($1, $2, $3, $4)",
                                      ctx.author.id, x, z, description)
        except asyncpg.UniqueViolationError:
            return await ctx.send("Someone has already saved that coordinate to the global spreadsheet!")
        await ctx.send(f"Coordinate `{x}X {z}Z` saved with annotation: `{discord.utils.remove_markdown(description)}`"[0:2000])

    SortType = typing.Literal['Description A-Z', 'Description Z-A', 'Descending X Coord', 'Ascending X Coord',
                              'Descending Z Coord', 'Ascending Z Coord', 'By Author A-Z', 'By Author Z-A']

    @slash_utils.slash_command(name='list', guild_id=706624339595886683)
    @slash_utils.describe(search='Searches the saved coordinates by description (selecting a suggested result is optional)',
                          sort='Sorts the results by the selected criteria.')
    async def list_coords(self, ctx: slash_utils.Context, search: slash_utils.Autocomplete[str] = None, sort: SortType = None):
        """ Lists all coordinates saved to the database """
        q = "SELECT author, x, z, description FROM coords"
        if search:
            q += " WHERE SIMILARITY(description, $1) > 0.2"
            await ctx.channel.send(q)

        sort_modes = {'Description A-Z': 'ORDER BY description ASC',
                      'Description Z-A': 'ORDER BY description DESC',
                      'Descending X Coord': 'ORDER BY x ASC',
                      'Ascending X Coord': 'ORDER BY x DESC',
                      'Descending Z Coord': 'ORDER BY z ASCe',
                      'Ascending Z Coord': 'ORDER BY z DESC',
                      'By Author A-Z': 'ORDER BY description ASC',
                      'By Author Z-A': 'ORDER BY description ASC'}

        should_sort = None
        if sort := sort_modes.get(sort):
            if 'Author A-Z' in sort:
                should_sort = False
            elif 'Author Z-A' in sort:
                should_sort = True

            query = f"{q} {sort}"
        else:
            if not search:
                query = f"{q} ORDER BY description ASC"
            else:
                query = f"{q} ORDER BY SIMILARITY(description, $1) ASC"

        if not search:
            coords = await self.bot.db.fetch(query)
        else:
            coords = await self.bot.db.fetch(query, search)

        if not coords:
            if not search:
                return await ctx.send("There are no coordinates saved! Do `/save` to save one.", ephemeral=True)
            else:
                return await ctx.send("There are no coordinates saved that match your search!", ephemeral=True)

        table = [(self.bot.get_user(author) or author, str(x), str(z), brief) for author, x, z, brief in coords]
        if should_sort is not None:
            table.sort(key=lambda x: str(x[0]), reverse=should_sort)
        table = tabulate.tabulate(table, headers=["Author", "X", "Z", "Description"], tablefmt="presto")
        lines = table.split("\n")
        lines, headers = lines[2:], '\n'.join(lines[0:2])
        header = f"All global coords. do /save to save one".center(len(lines[0]))
        pages = jishaku.paginators.WrappedPaginator(prefix=f'```\n{header}\n{headers}', max_size=1950)
        [pages.add_line(line) for line in lines]
        interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
        await interface.send_to(ctx)

    @list_coords.on_autocomplete('search')
    async def list_auto(self, _, user_input: str):
        query = "SELECT author, description FROM coords WHERE SIMILARITY(description, $1) > 0.1 LIMIT 25"
        results = await self.bot.db.fetch(query, user_input) or []

        return {str(description)[0:100]: str(description)[0:100] for author, description in results}

    @slash_utils.slash_command(name='delete', guild_id=706624339595886683)
    @slash_utils.describe(search='Searches trough the descriptions of your saved coordinates.')
    async def delete(self, ctx, search: slash_utils.Autocomplete[str]):
        """ Deletes one of your saved coordinates """
        match = re.search(r'^(?P<X>-?\d+) \| (?P<z>-?\d+)$', search)
        if not match:
            return await ctx.send("Sorry, but you must select one of the suggested options!", ephemeral=True)
        x, z = match.group('X'), match.group('z')
        description = await self.bot.db.fetchval("DELETE FROM coords WHERE x = $1 AND z = $2 AND author = $3 RETURNING description", int(x), int(z), ctx.author.id)
        if not description:
            return await ctx.send("Sorry, but somehow, the coordinate you tried to delete wasn't yours, or does not exist anymore!", ephemeral=True)
        await ctx.send(f"Deleted coordinate `{x}X {z}Z` with annotation: `{description}`"[0:2000])

    @delete.on_autocomplete('search')
    async def delete_auto(self, interaction: discord.Interaction, user_input: str):
        if len(user_input) < 3:
            results = await self.bot.db.fetch("SELECT x, z, description FROM coords WHERE author = $1 LIMIT 25",
                                              interaction.user.id) or []
        else:
            results = await self.bot.db.fetch("SELECT x, z, description FROM coords WHERE SIMILARITY(description, $1) > 0.1 AND author = $2 LIMIT 25",
                                              user_input, interaction.user.id) or []

        return {f'{x} | {z}': f"{x}X {z}Z - {description}" for x, z, description in results}

import asyncpg
import discord
import jishaku.paginators
import tabulate
from discord.ext import commands

from ozbot.__main__ import Ozbot


def setup(bot):
    bot.add_cog(Coords(bot))


class Coords(commands.Cog):
    def __init__(self, bot):
        self.bot: Ozbot = bot

    @commands.command(name='save', aliases=['save-coords'], brief='Saves your coordinates to the database.', slash_command=True, message_command = False, slash_command_guilds=[706624339595886683])  # Dont ask for fork they all shit!
    async def save_coords(self, ctx: commands.Context, x: int, z: int, *, description: discord.utils.remove_markdown):
        """ Saves a coordinate to the public database """
        try:
            await self.bot.db.execute("INSERT INTO coords (author, x, z, description) VALUES ($1, $2, $3, $4)",
                                      ctx.author.id, x, z, description)
        except asyncpg.UniqueViolationError:
            return await ctx.send("Someone has already saved that coordinate to the global spreadsheet!", ephemeral=True)
        await ctx.send(f"Coordinate `{x}X {z}Z` saved with annotation: `{discord.utils.remove_markdown(description)}`")

    @commands.command(name='list', aliases=['list-coords', 'coords'], brief='Lists all coordinates saved by you.', slash_command=True, message_command = False, slash_command_guilds=[706624339595886683])  # Dont ask for fork they all shit!
    async def list_coords(self, ctx: commands.Context, sort: str = None, search: str = None):
        """ Lists all coordinates saved to the database """
        q = "SELECT author, x, z, description FROM coords"
        if search:
            q += " WHERE SIMILARITY(description, $1) > 0.4"
        if sort == 'a_to_z':
            query = f"{q} ORDER BY description ASC"
        elif sort == 'z_to_a':
            query = f"{q} ORDER BY description DESC"
        elif sort == 'desc_x':
            query = f"{q} ORDER BY x ASC"
        elif sort == 'asc_x':
            query = f"{q} ORDER BY x DESC"
        elif sort == 'desc_z':
            query = f"{q} ORDER BY z ASC"
        elif sort == 'asc_z':
            query = f"{q} ORDER BY z DESC"
        elif sort == 'author_a_to_z':
            query = f"{q} ORDER BY author ASC"
        elif sort == 'author_z_to_a':
            query = f"{q} ORDER BY author DESC"
        else:
            if not search:
                query = f"{q} ORDER BY author ASC"
            else:
                query = f"{q} ORDER BY SIMILARITY(description, $1) ASC"
        if not search:
            coords = await self.bot.db.fetch(query)
        else:
            coords = await self.bot.db.fetch(query, search)
        if not coords:
            if not search:
                return await ctx.send("There are no coordinates saved! Do `/save` to save one.")
            else:
                return await ctx.send("There are no coordinates saved that match your search!")
        table = [(self.bot.get_user(author) or author, str(x), str(z), brief) for author, x, z, brief in coords]
        table = tabulate.tabulate(table, headers=["Author", "X", "Z", "Description"], tablefmt="presto")
        lines = table.split("\n")
        lines, headers = lines[2:], '\n'.join(lines[0:2])
        header = f"All global coords. do /save to save one".center(len(lines[0]))
        pages = jishaku.paginators.WrappedPaginator(prefix=f'```\n{header}\n{headers}', max_size=1950)
        [pages.add_line(line) for line in lines]
        pages.add_line(query)
        interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
        await interface.send_to(ctx)

# !jsk py ```py
#         from discord.http import Route
#         route = Route(
#             "POST",
#             f"/applications/{ctx.bot.application_id}/guilds/{ctx.guild.id}/commands")
#
#         json = {
#             "name": "save",
#             "type": 1,
#              "description": "Saves a coordinate to the public database",
#         "options": [
#         {
#             "name": "x",
#             "description": "X Coordinate",
#             "type": 4,
#             "required": True
#         },
#         {
#             "name": "z",
#             "description": "Z coodrinate",
#             "type": 4,
#             "required": True
#         },
#         {
#             "name": "description",
#             "description": "Annotation to add to the saved coordinates.",
#             "type": 3,
#             "required": True
#         }
#         ]
#
#         }
#         await ctx.bot.http.request(route=route, json=json, headers={"Authorization": f"Bot {ctx.bot.http.token}"})
#
# ```

# !jsk py ```py
#         from discord.http import Route
#         route = Route(
#             "POST",
#             f"/applications/{ctx.bot.application_id}/guilds/{ctx.guild.id}/commands")
#
#         json = {
#             "name": "list",
#             "type": 1,
#              "description": "Lists all the saved coordinates",
#         }
#         await ctx.bot.http.request(route=route, json=json, headers={"Authorization": f"Bot {ctx.bot.http.token}"})
# ```

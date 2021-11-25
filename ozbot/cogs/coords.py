import re
import typing
from contextvars import ContextVar

import asyncpg
import discord
import jishaku.paginators
import tabulate
from discord import Interaction
from discord.ext import commands
from discord.types.interactions import ApplicationCommandOptionChoice
from discord.webhook.async_ import AsyncWebhookAdapter

from ozbot.__main__ import Ozbot


def setup(bot):
    bot.add_cog(Coords(bot))


class Coords(commands.Cog):
    def __init__(self, bot):
        self.bot: Ozbot = bot

    @commands.command(name='save', aliases=['save-coords'], brief='Saves your coordinates to the database.',
                      slash_command=True, message_command=False,
                      slash_command_guilds=[706624339595886683])  # Dont ask for fork they all shit!
    async def save_coords(self, ctx: commands.Context, x: int, z: int, *, description: discord.utils.remove_markdown):
        """ Saves a coordinate to the public database """
        try:
            await self.bot.db.execute("INSERT INTO coords (author, x, z, description) VALUES ($1, $2, $3, $4)",
                                      ctx.author.id, x, z, description)
        except asyncpg.UniqueViolationError:
            return await ctx.send("Someone has already saved that coordinate to the global spreadsheet!",
                                  ephemeral=True)
        await ctx.send(f"Coordinate `{x}X {z}Z` saved with annotation: `{discord.utils.remove_markdown(description)}`"[0:2000])

    @commands.command(name='list', aliases=['list-coords', 'coords'], brief='Lists all coordinates saved by you.',
                      slash_command=True, message_command=False,
                      slash_command_guilds=[706624339595886683])  # Dont ask for fork they all shit!
    async def list_coords(self, ctx: commands.Context, sort: str = None, search: str = None):
        """ Lists all coordinates saved to the database """
        q = "SELECT author, x, z, description FROM coords"
        if search:
            q += " WHERE SIMILARITY(description, $1) > 0.2"
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
                query = f"{q} ORDER BY description ASC"
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
        interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
        await interface.send_to(ctx)

    @commands.Cog.listener('on_message')
    async def insert_into_database(self, message: discord.Message):
        if message.author.id != 864969115839758356 or message.channel.id != 851314198654484521:
            return
        if not (match := re.search(r"^(?P<X>-?[0-9]*) \| (?P<Z>-?[0-9]*) \| (?P<Name>\w+) \| (?P<UUID>[0-9a-f]{8}[-]?[0-9a-f]{4}[-]?[0-9a-f]{4}[-]?[0-9a-f]{4}[-]?[0-9a-f]{12}) \| (?P<Description>.*)$", message.content)):
            return
        x, z, name, uuid, description = match.group('X'), match.group('Z'), match.group('Name'), match.group('UUID'), match.group('Description')
        author_id = await self.bot.db.fetchval("SELECT user_id FROM usernames WHERE minecraft_id = $1", uuid)
        if not author_id:
            await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Succesfully saved to discord database as ","color":"gold"},{"text":"insert_discord_username ","color":"yellow"},{"text":"with annotation ","color":"gold"},{"text":"insert_note_here","color":"yellow"}]
            """.replace("insert_minecraft_username", name))
            return
        try:
            await self.bot.db.execute("INSERT INTO coords (author, x, z, description) VALUES ($1, $2, $3, $4)", author_id, int(x), int(z), description)
            await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Succesfully saved to discord database as ","color":"gold"},{"text":"insert_discord_username ","color":"yellow"},{"text":"with annotation ","color":"gold"},{"text":"insert_note_here","color":"yellow"}]
            """.replace("insert_minecraft_username", name).replace("insert_discord_username", str(self.bot.get_user(author_id) or f'User not found (ID: {author_id})')).replace("insert_note_here", description))
        except asyncpg.UniqueViolationError:
            coords_author_id = await self.bot.db.fetchval("SELECT author FROM coords WHERE x = $1 AND z = $2", int(x), int(z))
            if coords_author_id:
                await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Sorry but ","color":"red"},{"text":"insert_discord_username ","color":"yellow"},{"text":"has already saved these coordinates. ","color":"red"},{"text":"Maybe move a bit?","color":"yellow"}]
                """.replace("insert_discord_username", str(self.bot.get_user(coords_author_id) or f'User not found (ID: {coords_author_id})')).replace("insert_minecraft_username", name))
            else:
                await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Sorry but ","color":"red"},{"text":"insert_discord_username ","color":"yellow"},{"text":"has already saved these coordinates. ","color":"red"},{"text":"Maybe move a bit?","color":"yellow"}]
                """.replace("insert_discord_username", 'UNKNOWN USER').replace("insert_minecraft_username", name))

    @commands.Cog.listener('on_interaction')
    async def type_printer(self, interaction: Interaction):
        if interaction.type != discord.InteractionType.application_command_autocomplete:
            return
        if not (name := interaction.data.get('name', None)):
            return
        if not (options := interaction.data.get('options', None)):
            return
        response: discord.InteractionResponse = interaction.response
        if name == 'list':
            option = discord.utils.find(lambda o: o.get('name', '') == 'search' and o.get('focused', False) is True, options)
            user_input = option.get('value', '')
            results = await self.bot.db.fetch("SELECT author, description FROM coords WHERE SIMILARITY(description, $1) > 0.1 LIMIT 25", user_input) or []
            responses = []
            for author, description in results:
                responses.append(ApplicationCommandOptionChoice(name=str(description)[0:100], value=str(description)[0:100]))
            return await response.autocomplete_result(responses)
        elif name == 'delete':
            option = discord.utils.find(lambda o: o.get('name', '') == 'search' and o.get('focused', False) is True, options)
            user_input = option.get('value', '')
            if len(user_input) < 3:
                results = await self.bot.db.fetch("SELECT x, z, description FROM coords WHERE author = $1 LIMIT 25", interaction.user.id) or []
            else:
                results = await self.bot.db.fetch("SELECT x, z, description FROM coords WHERE SIMILARITY(description, $1) > 0.1 AND author = $2 LIMIT 25", user_input, interaction.user.id) or []
            responses = []
            for x, z, description in results:
                responses.append(ApplicationCommandOptionChoice(name=f"{x}X {z}Z - {description}", value=f'{x} | {z}'))
            return await response.autocomplete_result(responses)

    @commands.command(name='delete', brief='Saves your coordinates to the database.',
                      slash_command=True, message_command=False,
                      slash_command_guilds=[706624339595886683])  # Dont ask for fork they all shit!
    async def delete(self, ctx, *, search: str):
        """ Deletes one of your saved coordinates """
        match = re.search(r'^(?P<X>-?\d+) \| (?P<z>-?\d+)$', search)
        if not match:
            return await ctx.send("Sorry, but you must select one of the suggested options!", ephemeral=True)
        x, z = match.group('X'), match.group('z')
        description = await self.bot.db.fetchval("DELETE FROM coords WHERE x = $1 AND z = $2 AND author = $3 RETURNING description", int(x), int(z), ctx.author.id)
        if not description:
            return await ctx.send("Sorry, but somehow, the coordinate you tried to delete wasn't yours, or does not exist anymore!", ephemeral=True)
        await ctx.send(f"Deleted coordinate `{x}X {z}Z` with annotation: `{description}`"[0:2000])

    @commands.Cog.listener('on_message')
    async def fetch_close_by(self, message: discord.Message):
        if message.author.id != 864969115839758356 or message.channel.id != 851314198654484521:
            return
        if not (match := re.search(r'FETCH_NEARBY \| (?P<X>-?\d+) \| (?P<z>-?\d+) \| (?P<Name>\w+) \| (?P<radius>-?\d+)', message.content)):
            return
        x, z, name, radius = match.group('X'), match.group('z'), match.group('Name'), match.group('radius')
        results = await self.bot.db.fetch("""
        SELECT x, z, description FROM coords 
        WHERE x 
            BETWEEN $1::INTEGER - $3::INTEGER 
            AND $1::INTEGER + $3::INTEGER 
        AND z 
            BETWEEN $2::INTEGER - $3::INTEGER 
            AND $2::INTEGER + $3::INTEGER
            """, int(x), int(z), int(radius))
        if not results:
            return await message.channel.send("""!xc tellraw insert_player_here ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"] ","bold":true,"color":"blue"},{"text":"No results founds within a insert_radius_here block radius!","color":"red"}]
            """.replace('insert_radius_here', radius).replace('insert_player_here', name))
        lines = ["""{"text":"\\nxcoord","color":"yellow"},{"text":"X","color":"gold"},{"text":" zcoord","color":"yellow"},{"text":"Z","color":"gold"},{"text":" - description","color":"gray"}""".replace('xcoord', str(x)).replace('zcoord', str(z)).replace('description', description) for x, z, description in results]
        header = f"------ Locations within {radius} blocks ------"
        pages = jishaku.paginators.WrappedPaginator(prefix="", suffix="", max_size=1600)
        [pages.add_line(line) for line in lines]
        page = str(pages.pages[0]).replace('\n', ',')
        page = """!xc tellraw insert_player_here ["",{"text":"header_here","color":"blue"}table_thing{"text":"\\n---------------------------------amountstr","color":"blue"}]
        """.replace('header_here', header).replace('insert_player_here', name).replace('table_thing', page).replace('amountstr', str('-'*len(str(radius))))
        if len(page) <= 2000:
            await message.channel.send(page)
        else:
            return await message.channel.send("""!xc tellraw insert_player_here ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"] ","bold":true,"color":"blue"},{"text":"The amount of characters exceeded the amount of characters allowed! Please contact Leo and tell him to fix it.","color":"red"}]
            """.replace('insert_radius_here', radius).replace('insert_player_here', name))


async def autocomplete_result(response: discord.InteractionResponse, choices: typing.List[ApplicationCommandOptionChoice]):
    """ This is enhanced-dpy's way of responding to an autocomplete type interaction """
    if response.is_done():
        raise discord.InteractionResponded(response._parent)

    parent = response._parent
    if parent.type is not discord.InteractionType.application_command_autocomplete:
        return

    adapter = ContextVar("async_webhook_context", default=AsyncWebhookAdapter()).get()
    await adapter.create_interaction_response(
        parent.id,
        parent.token,
        session=parent._session,
        type=discord.InteractionResponseType.application_command_autocomplete_result.value,
        data={"choices": choices},
    )

    response.responded_at = discord.utils.utcnow()


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

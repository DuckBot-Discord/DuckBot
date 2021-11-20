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

    @commands.command(name='save', aliases=['save-coords'], brief='Saves your coordinates to the database.', slash_command=True)
    async def save_coords(self, ctx: commands.Context, x: int, y: int, z: int, *, description: str):
        """ Saves a coordinate to the public database """
        try:
            await self.bot.db.execute("INSERT INTO coords (author, x, y, z, description) VALUES ($1, $2, $3, $4)",
                                      ctx.author.id, x, y, z, description)
        except asyncpg.UniqueViolationError:
            return await ctx.send("Someone has already saved that coordinate to the global spreadsheet!", ephemeral=True)
        await ctx.send(f"Coordinate `{x}X {y}Y {z}Z` saved!")

    @commands.command(name='list', aliases=['list-coords', 'coords'], brief='Lists all coordinates saved by you.', slash_command=True)
    async def list_coords(self, ctx: commands.Context):
        """ Lists all coordinates saved by you """
        coords = await self.bot.db.fetch("SELECT author, x, y, z, description FROM coords", ctx.author.id)
        if not coords:
            return await ctx.send("You haven't saved any coordinates yet!", ephemeral=True)
        table = [(command, self.bot.get_user(user_id) or user_id, guild_id, str(timestamp).replace('+00:00', ''))
                 for command, user_id, guild_id, timestamp in coords]
        table = tabulate.tabulate(table, headers=["Command", "User/UID", "Guild ID", "Timestamp"], tablefmt="presto")
        lines = table.split("\n")
        lines, headers = lines[2:], '\n'.join(lines[0:2])
        header = f"Latest executed commands".center(len(lines[0]))
        pages = jishaku.paginators.WrappedPaginator(prefix=f'```\n{header}\n{headers}', max_size=1950)
        [pages.add_line(line) for line in lines]
        interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
        await interface.send_to(ctx)


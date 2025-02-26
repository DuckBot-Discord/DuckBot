from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

import discord
from discord.ext import commands

from utils import DuckCog, DuckGuildContext, group

if TYPE_CHECKING:
    from bot import DuckBot


class PrefixChanges(DuckCog):
    def __init__(self, bot: DuckBot) -> None:
        super().__init__(bot)

    @group(name='prefix', aliases=['prefixes', 'pre'], invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx: DuckGuildContext, *, prefix: Optional[str] = None) -> Optional[discord.Message]:
        """Adds a prefix for this server (you can have up to 25 prefixes).

        Parameters
        ----------
        prefix: Optional[:class:`str`]
            The prefix to add to the bot. If no prefix is given,
            the current prefixes will be shown.
        """
        if prefix is None:
            prefixes = await self.bot.get_prefix(ctx.message, raw=True)
            embed = discord.Embed(title='Current Prefixes', description='\n'.join(prefixes))
            return await ctx.send(embed=embed)

        if not ctx.author.guild_permissions.manage_guild:
            raise commands.MissingPermissions(['manage_guild'])

        if len(prefix) > 50:
            return await ctx.send('Prefixes can only be up to 50 characters long.')

        prefixes = await self.bot.pool.fetchval(
            """
            INSERT INTO guilds (guild_id, prefixes) VALUES ($1, ARRAY(
            SELECT DISTINCT * FROM unnest(array_append($3::text[], $2::text))))
            ON CONFLICT (guild_id) DO UPDATE SET prefixes = ARRAY( 
            SELECT DISTINCT * FROM UNNEST( ARRAY_APPEND(
            CASE WHEN array_length(guilds.prefixes, 1) > 0 
            THEN guilds.prefixes ELSE $3::text[] END, $2)))
            RETURNING guilds.prefixes
        """,
            ctx.guild.id,
            prefix,
            ctx.bot.command_prefix,
        )

        await ctx.send(f'✅ Added prefix {prefix}')

    @prefix.command(name='clear', aliases=['wipe'])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_clear(self, ctx: DuckGuildContext) -> Optional[discord.Message]:
        """Clears all prefixes from this server, restting them to default."""
        await self.bot.pool.execute("UPDATE guilds SET prefixes = ARRAY[]::TEXT[] WHERE guild_id = $1", ctx.guild.id)
        await ctx.send('✅ Reset prefixes to the default.')

    @discord.utils.copy_doc(prefix)
    @prefix.command(name='add', aliases=['append'])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_add(self, ctx: DuckGuildContext, *, prefix: str) -> Optional[discord.Message]:
        return await ctx.invoke(self.prefix, prefix=prefix)

    @prefix.command(name='remove', aliases=['delete', 'del', 'rm'])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_remove(self, ctx: DuckGuildContext, *, prefix: str) -> Optional[discord.Message]:
        """Removes a prefix from the bots prefixes.

        Parameters
        ----------
        prefix: :class:`str`
            The prefix to remove from the bots prefixes.
        """
        if len(prefix) > 50:
            return await ctx.send('Prefixes can only be up to 50 characters long.')

        await self.bot.pool.execute(
            "UPDATE guilds SET prefixes = ARRAY_REMOVE(prefixes, $1) WHERE guild_id = $2", prefix, ctx.guild.id
        )
        return await ctx.send(f'✅ Removed prefix {prefix}')

    @prefix_remove.autocomplete('prefix')  # type: ignore
    async def prefix_remove_autocomplete(self, ctx: DuckGuildContext, value: str) -> List[str]:
        return list(await ctx.bot.get_prefix(ctx.message, raw=True))

import discord
import asyncpg
from discord.ext import commands

from bot import CustomContext
from ._base import ConfigBase


class Prefixes(ConfigBase):
    @commands.group(invoke_without_command=True, aliases=['prefixes'])
    async def prefix(self, ctx: CustomContext) -> discord.Message:
        """Lists all the bots prefixes."""
        prefixes = await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True)
        embed = discord.Embed(title="Here are my prefixes:", description=ctx.me.mention + '\n' + '\n'.join(prefixes))
        embed.add_field(
            name="Available prefix commands:",
            value=f"```fix"
            f"\n{ctx.clean_prefix}{ctx.command} add"
            f"\n{ctx.clean_prefix}{ctx.command} remove"
            f"\n{ctx.clean_prefix}{ctx.command} clear"
            f"\n```",
        )
        return await ctx.send(embed=embed)

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefix.command(name="add")
    async def prefixes_add(self, ctx: CustomContext, new: str) -> discord.Message:
        """Adds a prefix to the bots prefixes.\nuse quotes to add spaces: %PRE%prefix \"duck \" """
        try:
            await self.bot.db.execute("INSERT INTO pre(guild_id, prefix) VALUES ($1, $2)", ctx.guild.id, new)
            self.bot.prefixes[ctx.guild.id] = await self.bot.fetch_prefixes(ctx.message)
            await ctx.send(f'✅ **|** Added `{new}` to my prefixes!')
        except asyncpg.exceptions.UniqueViolationError:
            return await ctx.send('⚠ **|** That is already one of my prefixes!')

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefix.command(name="remove", aliases=['delete'])
    async def prefixes_remove(self, ctx: CustomContext, prefix: str) -> discord.Message:
        """Removes a prefix from the bots prefixes.\nuse quotes to add spaces: %PRE%prefix \"duck \" """

        old = list(await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True))
        if prefix in old:
            await ctx.send(f"✅ **|** Successfully removed `{prefix}` from my prefixes!")
        else:
            await ctx.send('⚠ **|** That is not one of my prefixes!')
        await self.bot.db.execute('DELETE FROM pre WHERE (guild_id, prefix) = ($1, $2)', ctx.guild.id, prefix)
        self.bot.prefixes[ctx.guild.id] = await self.bot.fetch_prefixes(ctx.message)

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefix.command(name="clear", aliases=['delall'])
    async def prefixes_clear(self, ctx):
        """Clears the bots prefixes, resetting it to default."""
        await self.bot.db.execute("DELETE FROM pre WHERE guild_id = $1", ctx.guild.id)
        self.bot.prefixes[ctx.guild.id] = self.bot.PRE
        return await ctx.send("✅ **|** Cleared prefixes!")

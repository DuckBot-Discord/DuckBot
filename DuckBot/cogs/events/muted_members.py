import discord
from discord.ext import commands

from ._base import EventsBase


class MutedMembers(EventsBase):
    @commands.Cog.listener('on_member_join')
    async def add_previously_muted(self, member: discord.Member):
        if not await self.bot.db.fetchval(
            "SELECT user_id FROM muted WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id
        ):
            return
        await self.bot.db.execute("DELETE FROM muted WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id)
        if not (role := await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', member.guild.id)):
            return
        if not (role := member.guild.get_role(role)):
            return
        if role >= member.guild.me.top_role:
            return
        await member.add_roles(role, reason='Member was previously muted.')

    @commands.Cog.listener('on_member_remove')
    async def remove_previously_muted(self, member: discord.Member):
        if not (role := await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', member.guild.id)):
            return
        if not (role := member.guild.get_role(role)):
            return
        if role in member.roles:
            await self.bot.db.execute(
                'INSERT INTO muted (user_id, guild_id) VALUES ($1, $2) ' 'ON CONFLICT (user_id, guild_id) DO NOTHING',
                member.id,
                member.guild.id,
            )

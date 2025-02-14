import datetime
import logging

import discord
from discord.ext import commands

from utils import DuckContext, DuckCog
from utils.time import ShortTime, human_timedelta

log = logging.getLogger('auto-ban')


class NewAccountGate(DuckCog):
    @commands.command(name='min-age')
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def min_age(self, ctx: DuckContext, *, time: ShortTime | None = None):
        """Sets up or un-sets the minimum account age for the server.

        Joining members who's account age is smaller will be automatically kicked.

        Run with no argument to un-set the minimum account age.
        Example usage: `db.min-age 1month2weeks1day`
        Valid time identifiers: months/mo; weeks/w; days/d; hours/h; minutes/m; seconds/s (can be singular or plural)
        """
        if not time:
            await self.bot.pool.execute('UPDATE GUILDS SET min_join_age = NULL WHERE guild_id = $1', ctx.guild.id)
            await ctx.send('Unset minimum account age')
        else:
            seconds = (time.dt - ctx.message.created_at).total_seconds()
            await self.bot.pool.execute(
                'INSERT INTO GUILDS (guild_id, min_join_age) VALUES ($1, $2)'
                'ON CONFLICT (guild_id) DO UPDATE SET min_join_age = $2',
                ctx.guild.id,
                seconds,
            )
            await ctx.send(f'I will now kick joining accounts that are less than **{human_timedelta(time.dt)}** old.')

    @commands.Cog.listener('on_member_join')
    async def kick_new_members(self, member: discord.Member):
        """kicks joining members, as per the user-defined settings."""
        if not member.guild.me.guild_permissions.kick_members:
            return

        threshold_seconds: int | None = await self.bot.pool.fetchval(
            'SELECT min_join_age FROM guilds WHERE guild_id = $1', member.guild.id
        )
        if not threshold_seconds:
            return
        account_age_seconds = (discord.utils.utcnow() - member.created_at).total_seconds()

        if account_age_seconds < threshold_seconds:
            min_age = discord.utils.utcnow() + datetime.timedelta(seconds=threshold_seconds)
            await member.kick(reason=f'Account too young. Did not exceed the *{human_timedelta(min_age)} old* threshold.')

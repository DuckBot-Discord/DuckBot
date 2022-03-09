from __future__ import annotations

import logging
import datetime
from typing import (
    TYPE_CHECKING,
    Optional,
    List, 
    Tuple
)

import discord
from discord.ext import commands

from utils import (
    DuckCog,
    DuckContext,
    UserFriendlyTime,
    human_timedelta
)

from utils.errors import (
    HierarchyException, 
    MemberNotMuted,
    MemberAlreadyMuted, 
)

from utils.timer import Timer

if TYPE_CHECKING:
    from asyncpg import Connection
    
log = logging.getLogger('DuckBot.cogs.moderation.tempmute')

__all__: Tuple[str, ...] = (
    'ToLower',
    'TempMute',
)


# I understand this can be a simple function,
# but the UserFriendlyTime class is a bit of a mess
# and needs it to work. Thanks danny.
class ToLower(commands.Converter):
    __slots__: Tuple[str, ...] = ()

    # noinspection PyProtocol
    async def convert(self, ctx: DuckContext, argument: str) -> str:
        return argument.lower()
    
    
class TempMute(DuckCog):
    """A helper cog to tempmute users."""
    __slots__: Tuple[str, ...] = ()
    
    async def _create_muted_role(self, guild: discord.Guild) -> discord.Role:
        """|coro|
        
        Create a muted role for the guild.
        
        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild to create the muted role for.
        
        Returns
        -------
        :class:`discord.Role`
            The newly created muted role.
        """
        role = await guild.create_role(
            name='Muted',
            permissions=discord.Permissions(send_messages=False, connect=False),
            hoist=False,
            mentionable=False,
            reason='Muted role being created for tempmute.'
        )
        
        for channel in guild.channels:
            await channel.set_permissions(role, send_messages=False, connect=False)
        
        return role
    
    async def _get_muted_role(self, guild: discord.Guild, *, conn: Connection) -> discord.Role:
        """|coro|
        
        A helper function used internally. Will get the "Muted" role and return it whilst
        managing DB interactions.  // TODO: *not* do this. raise a "no role" error instead.
        
        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild to get the muted role from.
        conn: :class:`asyncpg.Connection`
            The connection to use.
        
        Returns
        -------
        :class:`discord.Role`
            The muted role.
        """
        # I'm using fetchrow here to validate we even have data in the guilds table.
        # If packet is None, then we dont have ANY data in the guilds table, and we need to create it.
        packet = await conn.fetchrow('SELECT guild_id, muted_role_id FROM guilds WHERE guild_id = $1', guild.id)
        if not packet:
            role = discord.utils.get(guild.roles, name='Muted')
            if not role:
                role = await self._create_muted_role(guild)
            
            await conn.execute('INSER INTO guilds(guild_id, muted_role_id) VALUES($1, $2)', guild.id, role.id)
            return role

        role_id = packet['muted_role_id']
        if role_id:
            role = discord.utils.get(guild.roles, id=role_id)
            if not role: # Role was deleted, re-create it.
                role = await self._create_muted_role(guild)
                await conn.execute('UPDATE guilds SET muted_role_id = $1 WHERE guild_id = $2', role.id, guild.id)

            return role
    
        # Let's check for a muted role, and if not found create one.
        role = discord.utils.get(guild.roles, name='Muted')
        if not role:
            role = await self._create_muted_role(guild)
            
        await conn.execute('UPDATE guilds SET muted_role_id = $1 WHERE guild_id = $2', role.id, guild.id)
    
        return role
    
    @commands.group(name='tempmute', aliases=['tm', 'mute'], invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def tempmute(
        self, 
        ctx: DuckContext, 
        member: discord.Member, 
        *, 
        time: UserFriendlyTime(converter=ToLower, default='being a jerk!') # type: ignore # Pyright doesn't like class definitions in annotations
    ) -> Optional[discord.Message]:
        """|coro|
        
        Temporarily mute a member from speaking or connecting to channels in the Discord. Mutes
        over 28 days are created using a Timer system. Mutes under 28 days are creating using Discord's
        timeout feature. If a Member is muted using the Timer system, you need to use `db.tempmute remove` to
        unmute them.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to mute.
        time: :class:`str`
            The total time and reason for the mute. For example, `1h`, `1h for being a jerk!`, `tomorrow at 2pm for being a jerk!`.
        """
        if ctx.invoked_subcommand:
            return
        
        guild = ctx.guild
        if not guild:
            return None
        
        if member.top_role > guild.me.top_role:
            raise HierarchyException(member)
        
        async with self.bot.safe_connection() as connection:
            data = await connection.fetchrow('SELECT mutes, guild_id FROM guilds WHERE guild_id = $1', guild.id)
            if not data:
                await connection.execute('INSERT INTO guilds(guild_id) VALUES($1)', guild.id)
                muted = []
            else:
                muted = data['mutes']
            
            if muted and member.id in muted:
                raise MemberAlreadyMuted(member)
        
            days_out = time.dt - discord.utils.utcnow()
            if days_out <= datetime.timedelta(days=28):
                try:
                    await member.edit(timed_out_until=time.dt)
                except discord.HTTPException as exc:
                    embed = discord.Embed(
                        title='Thats not good!',
                        description=f'I ran into a nasty error while trying to mute {member.mention}.',
                        timestamp=time.dt
                    )
                    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                    embed.set_footer(text=f'Member ID: {member.id}')
                    embed.add_field(name='Error Message', value=exc.text)
                    return await ctx.send(embed=embed)
                
                await connection.execute('UPDATE guilds SET mutes = array_append(mutes, $1) WHERE guild_id = $2', member.id, guild.id)
                
                embed = discord.Embed(
                    title=f'{str(member)} has been muted.',
                    description=f'{member.mention} has been muted for {human_timedelta(time.dt)}',
                    timestamp=time.dt
                )
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.set_footer(text=f'Member ID: {member.id}')
                return await ctx.send(embed=embed)
            
            # We need to manage roles now. Who TF mutes someone for over 28 days???? Like I dont understand...
            async with ctx.typing():
                muted_role = await self._get_muted_role(guild, conn=connection)
            roles_to_keep = [role for role in member.roles if not role.is_assignable()]

            # We need to get this before editing the member, because the member .roles attribute
            # will get updated after the edit. (singleton moment)
            roles_to_restore = [role for role in member.roles if role.is_assignable()]
            
            try:
                await member.edit(roles=[*roles_to_keep, *[muted_role]])
            except discord.HTTPException as exc:
                embed = discord.Embed(
                    title='Thats not good!',
                    description=f'I ran into a nasty error while trying to mute {member.mention}.',
                )
                # See THIS is why we use a bot Embed to allow for author field :) hehe
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.set_footer(text=f'Member ID: {member.id}')
                embed.add_field(name='Error Message', value=exc.text)
                return await ctx.send(embed=embed)
            
            await self.bot.create_timer(
                time.dt,
                'mute',
                member.id, 
                guild.id, 
                roles=[role.id for role in roles_to_restore],
            )
            await connection.execute('UPDATE guilds SET mutes = array_append(mutes, $1) WHERE guild_id = $2', member.id, guild.id)
            
            embed = discord.Embed(
                title=f'{str(member)} has been muted.',
                description=f'{member.mention} has been muted for {human_timedelta(time.dt)}',
                timestamp=time.dt
            )
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f'Member ID: {member.id}')
            return await ctx.send(embed=embed)
    
    @tempmute.command(name='remove')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def tempmute_remove(self, ctx: DuckContext, member: discord.Member) -> Optional[discord.Message]:
        """|coro|
        
        Umute a member that was muted.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to unmute.
        """
        # Fuck me. This whole command. So bad.
        guild = ctx.guild
        if not guild:
            return
        
        async with self.bot.safe_connection() as conn:
            mutes = await conn.fetchval('SELECT mutes FROM guilds WHERE guild_id = $1', guild.id)
            
            if not mutes or member.id not in mutes:
                raise MemberNotMuted(member)
            
            if member.timed_out_until:
                await member.edit(timed_out_until=None)
            else:
                # Let's find the timer(s)
                timer = await conn.fetch("""
                SELECT * FROM timers WHERE event = 'mute'
                
                    AND (extra->'args'->0)::bigint = $1 
                        -- arg at position 0 is the member id
                        
                    AND (extra->'args'->1)::bigint = $2;
                        -- arg at position 1 is the guild id
                """, member.id, guild.id)
                timers = [Timer(record=r) for r in timer]

                for timer in timers:
                    await self.bot.call_timer(timer)
            
        embed = discord.Embed(
            title=f'{str(member)} has been unmuted.',
            description=f'{member.mention} has been unmuted.',
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_footer(text=f'Member ID: {member.id}')
        return await ctx.send(embed=embed)
    
    @commands.command(name='unmute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute(self, ctx: DuckContext, member: discord.Member) -> Optional[discord.Message]:
        """|coro|
        
        Unmute a member that was muted.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to unmute.
        """
        # noinspection PyTypeChecker
        return await ctx.invoke(self.tempmute_remove, member)
        
    @commands.Cog.listener('on_member_update')
    async def cache_validation(self, before: discord.Member, after: discord.Member) -> None:
        """|coro|
        
        A listener that updates the internal cache of muted members.
        
        This even gets called when the member's timeout expires, removing it from the DB.
        
        Parameters
        ----------
        before: :class:`discord.Member`
            The member before the update.
        after: :class:`discord.Member`
            The member after the update.
        """
        if after.timed_out_until:
            return
        
        async with self.bot.safe_connection() as conn:
            mutes = await conn.fetchval('SELECT mutes FROM guilds WHERE guild_id = $1', after.guild.id)
            if not mutes:
                return
            
            if after.id in mutes:
                await conn.execute('UPDATE guilds SET mutes = array_remove(mutes, $1) WHERE guild_id = $2', after.id, after.guild.id)
    
    @commands.Cog.listener('on_mute_timer_complete')
    async def mute_dispatcher(self, member_id: int, guild_id: int, *, roles: List[int]) -> None:
        """|coro|
        
        A mute dispatcher that listenes for when a timer expires. Once it does, it restores the member's roles
        back to what they were before the mute.
    
        Parameters
        ----------
        member_id: :class:`int`
            The member ID.
        guild_id: :class:`int`
            The guild ID.
        roles: List[:class:`int`]
            A list of role IDS to restore to the member.
        """
        log.info(f'Mute timer for {member_id} in {guild_id} has expired. Restoring {len(roles)} roles.')
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return log.debug('Ignoring mute timer for guild %s, it no longer exists.', guild_id)
        
        if not guild.me.guild_permissions.manage_roles: # The bot doesn't have the permissions to manage roles anymore, do nothing.
            return log.debug('Ignoring mute timer for guild %s, the bot no longer has the Manage Roles permission.', guild_id)
        
        try:
            member = guild.get_member(member_id) or await guild.fetch_member(member_id)
        except (discord.NotFound, discord.HTTPException):
            return log.debug('Ignoring mute timer for member %s, they no longer exist.', member_id)
        
        try:
            await member.edit(roles=list(discord.Object(id=id) for id in roles))
        except discord.HTTPException:
            log.debug('Failed to restore roles for member %s', member_id)
        
        async with self.bot.safe_connection() as conn:
            await conn.execute('UPDATE guilds SET mutes = array_remove(mutes, $1) WHERE guild_id = $2', member_id, guild_id)
from __future__ import annotations

import datetime
from typing import (
    Optional,
    List
)

import discord
from discord.ext import commands

from utils import DuckCog
from utils.context import DuckContext
from utils.time import UserFriendlyTime, human_timedelta
from utils.errors import HierarchyException
    

class ToLower(commands.Converter):
    async def convert(self, ctx: DuckContext, argument: str) -> str:
        return argument.lower()
    
    
class TempMute(DuckCog):
    """A helper cog to tempmute users."""
    
    async def _create_muted_role(self, guild: discord.Guild) -> discord.Role:
        return await guild.create_role(
            name='Muted',
            permissions=discord.Permissions(send_messages=False, connect=False),
            hoist=False,
            mentionable=False,
            reason='Muted role being created for tempmute.'
        )
    
    async def _get_muted_role(self, guild: discord.Guild) -> discord.Role:
        async with self.bot.safe_connection() as conn:
            # I'm using fetchrow here to validate we even have data in the guilds table.
            # If packet is None, then we dont have ANY data in the guilds table, and we need to create it.
            packet = await conn.fetchow('SELECT guild_id, muted_role_id FROM guilds WHERE guild_id = $1', guild.id)
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
    
    @commands.group(name='tempmute', aliases=['tm'], invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_guild_permissions(timeout_members=True, manage_roles=True)
    @commands.has_guild_permissions(timeout_members=True, manage_roles=True)
    async def tempmute(
        self, 
        ctx: DuckContext, 
        member: discord.Member, 
        *, 
        time: UserFriendlyTime(converter=ToLower, default='being a jerk!') # type: ignore # Pyright doesn't like class definitions in annotations
    ) -> Optional[discord.Message]:
        """|coro|
        
        Temporarily mute a member from speaking or connecting to channels in the Discord.
        
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
        
        days_out = discord.utils.utcnow() - time.dt
        if days_out <= datetime.timedelta(days=28):
        
            try:
                await member.edit(communication_disabled_until=time.dt)
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
            
            embed = discord.Embed(
                title=f'{str(member)} has been muted.',
                description=f'{member.mention} has been muted for {human_timedelta(time.dt)}',
                timestamp=time.dt
            )
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f'Member ID: {member.id}')
            return await ctx.send(embed=embed)
        
        # We need to manage roles now. Who TF mutes someone for over 28 days???? Like I dont understand...
        muted_role = await self._get_muted_role(guild)
        roles_to_keep = [role for role in member.roles if not role.is_assignable()]
        roles_to_remove = [role.id for role in member.roles if role not in roles_to_keep]
        
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
        
        await self.bot.create_timer(time.dt, 'mute', member.id, guild.id, roles=roles_to_remove)
        embed = discord.Embed(
            title=f'{str(member)} has been muted.',
            description=f'{member.mention} has been muted for {human_timedelta(time.dt)}',
            timestamp=time.dt
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_footer(text=f'Member ID: {member.id}')
        return await ctx.send(embed=embed)
    
    @tempmute.command(name='remove')
    async def tempmute_remove(self, ctx: DuckContext, member: discord.Member) -> None:
        pass
    
    @commands.Cog.listener('on_mute_timer_complete')
    async def mute_dispatcher(self, member_id, guild_id, *, roles: List[int]) -> None:
        ...
        
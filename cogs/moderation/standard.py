from __future__ import annotations

from typing import (
    Optional,
    Union,    
)

import discord
from discord.ext import commands

from utils import DuckCog
from utils.context import DuckContext
from utils.errors import HierarchyException


class StandardModeration(DuckCog):
    """A cog dedicated to holding standard
    moderation commands. Such as ban or kick.
    
    Attributes
    ----------
    bot: :class:`DuckBot`
        The main bot instance.
    """
    
    @commands.command(name='kick', aliases=['boot'])
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_guild_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: DuckContext, member: discord.Member, *, reason: Optional[str] = 'being a jerk!') -> Optional[discord.Message]:
        """|coro|
        
        Kick a member from the server.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to kick.
        reason: Optional[:class:`str`]
            The reason for kicking the member. Defaults to 'being a jerk!'.
        """
        guild = ctx.guild
        if guild is None:
            return 
        
        if member.top_role > guild.me.top_role:
            raise HierarchyException(member)
        
        try:
            await guild.kick(member, reason=reason)
        except discord.HTTPException as exc:
            embed = discord.Embed(
                title='Something goofed!',
                description=f'Kicking this member failed!'
            )
            embed.add_field(name='Error Message', value=str(exc))
            return await ctx.send(embed=embed)

        return await ctx.send(f'{member.mention} has been kicked for: {reason}.')
    
    
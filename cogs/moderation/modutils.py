from __future__ import annotations

from typing import (
    Optional,
    TYPE_CHECKING,
    Callable
)


import discord
from discord.ext import commands
from discord.guild import BanEntry

from utils.errorhandler import HandleHTTPException
from utils.errors import HierarchyException, ActionNotExecutable
from utils.context import DuckContext


def can_execute_action():
    """|coro|

    Checks if the action can be executed on the author and the bot.
    """
    
    async def predicate(ctx: DuckContext) -> Optional[bool]:
        """|coro|
        
        A wrapped predicate to check if the action can be executed.
        
        Parameters
        ----------
        ctx: :class:`commands.Context`
            The context of the command.
        
        Returns
        -------
        Optional[:class:`bool`]
            Whether the action can be executed.
            
        Raises
        ------
        HierarchyException
            The action cannot be executed due to role hierarchy.
        ActionNotExecutable
            The action cannot be executed due to other reasons.
        commands.NoPrivateMessage
            This command cannot be used in private messages.
        """
        target = discord.utils.find(lambda m: isinstance(m, (discord.User, discord.Member)), ctx.args) or ctx.author
        
        guild = ctx.guild
        if guild is None or not isinstance(ctx.author, discord.Member):
            raise commands.NoPrivateMessage('This command cannot be used in private messages.')
        
        if isinstance(target, discord.User):
            upgraded = await ctx.bot.get_or_fetch_member(guild, target)
            if not upgraded:
                return 
            
            target = upgraded

        if guild.me.top_role <= target.top_role:
            raise HierarchyException(target)
        elif ctx.author == target:
            raise ActionNotExecutable('You cannot execute this action on yourself!')
        elif guild.owner == target:
            raise ActionNotExecutable('I cannot execute any action on the server owner!')
        elif guild.owner == ctx.author:
            return 
        elif ctx.author.top_role <= target.top_role:
            raise HierarchyException(target, author_error=True)
        
    return commands.check(predicate) # type: ignore 


def safe_reason(ctx: commands.Context, reason: str, *, length: int = 512):
    base = f'Action by {ctx.author} ({ctx.author.id}) for: '
    length_limit = length - len(base)
    if len(reason) > length_limit:
        reason = reason[:length_limit-3] + '...'
    return base + reason


class BanEntryConverter(BanEntry):
    """A converter for :class:`BanEntry`."""
    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> BanEntry:
        await ctx.trigger_typing()

        # this isn't really necessary, but it's just in case an error occurs while
        # fetching the bans, like Missing Permissions. Shouldn't happen though.
        async with HandleHTTPException(ctx):
            if argument.isdigit():
                member_id = int(argument, base=10)
                try:
                    entry = await ctx.guild.fetch_ban(discord.Object(id=member_id))
                    return cls(user=entry.user, reason=entry.reason)  # type: ignore
                except discord.NotFound:
                    raise commands.BadArgument('This member has not been banned before.') from None

            # we search by username now.
            ban_list = await ctx.guild.bans()
            if not (entity := discord.utils.find(lambda u: str(u.user) == argument, ban_list)):
                if not (entity := discord.utils.find(lambda u: str(u.user).lower() == argument.lower(), ban_list)):
                    if not (entity := discord.utils.find(lambda u: u.user.name == argument, ban_list)):
                        entity = discord.utils.find(lambda u: str(u.user.name).lower() == argument.lower(), ban_list)

            if entity is None:
                raise commands.BadArgument('This member has not been banned before.')
            return cls(user=entity.user, reason=entity.reason)  # type: ignore

    def __str__(self):
        return f'{self.user} ({self.user.id})'

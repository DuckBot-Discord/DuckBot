from __future__ import annotations

from typing import (
    Type,
    Union,
    Tuple,
    overload,
    Dict,
    TypeVar
)

import discord
from discord.ext import commands

from . import can_execute_action, DuckContext, HandleHTTPException

BET = TypeVar('BET', bound='discord.guild.BanEntry')


class TargetVerifierMeta(type):
    
    @overload
    def __getitem__(cls, item: Type[discord.Member]) -> TargetVerifier:
        ...
        
    @overload
    def __getitem__(cls, item: Type[discord.User]) -> TargetVerifier:
        ...
        
    @overload
    def __getitem__(cls, item: Type[Tuple[Union[discord.Member, discord.User], ...]]) -> TargetVerifier:
        ...
        
    @overload
    def __getitem__(cls, item: Type[Tuple[Union[discord.User, discord.Member], ...]]) -> TargetVerifier:
        ...

    def __getitem__(cls, item) -> TargetVerifier:
        return cls(item)
    
    
class TargetVerifier(metaclass=TargetVerifierMeta):
    __slots__: Tuple[str, ...] = (
        '_targets',
        'fail_if_not_upgrade',
        '_cs_converter_mapping',
    )
    
    def __init__(
        self, 
        targets: Type[
            Union[
                Union[discord.Member, discord.User],
                Tuple[Union[discord.Member, discord.User], ...]
            ]
        ],
        fail_if_not_upgrade: bool = True,
    ) -> None:
        self._targets = targets
        self.fail_if_not_upgrade: bool = fail_if_not_upgrade
        
    @discord.utils.cached_slot_property('_cs_converter_mapping')
    def converter_mapping(self) -> Dict[Type[Union[discord.Member, discord.User]], Type[commands.Converter]]:
        return {
            discord.Member: commands.MemberConverter,
            discord.User: commands.UserConverter
        }
            
    async def convert(self, ctx: DuckContext, argument: str) -> Union[discord.Member, discord.User]:
        # We need to determine what we're trying to upgrade to.
        # To do that, let's check the targets attribute.
        target = None
        try:
            if issubclass(self._targets, (discord.Member, discord.User)):
                # We upgrade to a member or user based upon the guild in this case.
                converter = self.converter_mapping[self._targets]
            else:
                # Something goofed here
                raise RuntimeError(f'Invalid target type {self._targets} ({type(self._targets)})')
        except TypeError:
            # We need to this manually. It's both discord.Member and discord.User
            if ctx.guild:
                try:
                    target = await commands.MemberConverter().convert(ctx, argument)
                except:
                    pass
            
            if not target:
                target = await commands.UserConverter().convert(ctx, argument)
        else:
            target = await converter().convert(ctx, argument)
        
        # Then check if the operation is legal
        await can_execute_action(ctx, target, fail_if_not_upgrade=self.fail_if_not_upgrade)
        return target
    
    
# Including `commands.Converter` is faster on discord backend iirc
class BanEntryConverter(discord.guild.BanEntry):
    """A converter for :class:`BanEntry`."""
    
    @classmethod
    async def convert(cls: Type[BanEntryConverter], ctx: DuckContext, argument: str) -> discord.guild.BanEntry:
        await ctx.trigger_typing()
        
        guild = ctx.guild
        if guild is None:
            raise commands.NoPrivateMessage('This command cannot be used in private messages.')

        # this isn't really necessary, but it's just in case an error occurs while
        # fetching the bans, like Missing Permissions. Shouldn't happen though.
        async with HandleHTTPException(ctx):
            if argument.isdigit():
                member_id = int(argument, base=10)
                try:
                    entry = await guild.fetch_ban(discord.Object(id=member_id))
                except discord.NotFound:
                    raise commands.BadArgument('This member has not been banned before.') from None
                else:
                    return cls(user=entry.user, reason=entry.reason) 
            
            _find_entitiy = lambda u: str(u.user.lower()) == argument.lower() or str(u.user.name).lower() == argument.lower()
            
            # we search by username now.
            ban_list = await guild.bans()
            entity = discord.utils.find(_find_entitiy, ban_list)
            
            if entity is None:
                raise commands.BadArgument('This member has not been banned before.')
            
            return cls(user=entity.user, reason=entity.reason) 

    def __repr__(self) -> str:
        return '<BanEntryConverter user={0.user} ({0.user.id}) reason={0.reason}>'
    
    def __str__(self) -> str:
        return '{0.user} ({0.user.id})'.format(self)
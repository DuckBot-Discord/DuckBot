import typing

import discord
from discord.ext import commands
from utils.errors import HierarchyException, ActionNotExecutable

async def upgrade_to_member(guild: discord.Guild, user: discord.User) -> typing.Optional[discord.Member]:
    try:
        return guild.get_member(user.id) or await guild.fetch_member(user.id)
    except discord.HTTPException:
        return None

async def can_execute_action(ctx: commands.Context, target: typing.Union[discord.Member, discord.User]) -> None:
    """|coro|

    Checks if the action can be executed on the author and the bot.

    Parameters
    ----------
    ctx: :class:`commands.Context`
        The context of the command.
    target: Union[:class:`discord.Member`, :class:`discord.User`]
        The target of the action.

    Raises
    ------
    HierarchyException
        The action cannot be executed due to role hierarchy.
    ActionNotExecutable
        The action cannot be executed due to other reasons.
    """
    if isinstance(target, discord.User):
        upgraded = await upgrade_to_member(ctx.guild, target)
        if not upgraded:
            return
        target = upgraded

    if ctx.me.top_role < target.top_role:
        raise HierarchyException(target)
    if ctx.author.top_role < target.top_role:
        raise HierarchyException(target, author_error=True)
    if ctx.author == target:
        raise ActionNotExecutable('You cannot execute this action on yourself!')
    if ctx.guild is not None and ctx.guild.owner == target:
        raise ActionNotExecutable('I cannot execute any action on the server owner!')

def safe_reason(ctx: commands.Context, reason: str, *, length: int = 512):
    base = f'Action by {ctx.author} ({ctx.author.id}) for: '
    length_limit = length - len(base)
    if len(reason) > length_limit:
        reason = reason[:length_limit-3] + '...'
    return base + reason
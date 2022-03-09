import discord
from discord import (
    Interaction, Member, User,
)

from typing import (
    Union,
    Tuple,
    TYPE_CHECKING,
)

from . import errors
from .. import errors as base_errors

if TYPE_CHECKING:

    from bot import DuckBot


__all__: Tuple[str, ...] = (
    'can_execute_action',
    'has_permissions',
    'bot_has_permissions',
)

async def can_execute_action(
        interaction: Interaction,
        target: Union[Member, User],
        fail_if_not_upgrade: bool = False,
) -> None:
    """|coro|

    Checks if the user can execute the action.

    Parameters
    ----------
    interaction: `Interaction`
        The interaction to check.
    target: Union[:class:`discord.Member`, :class:`discord.User`]
        The target of the action.
    fail_if_not_upgrade: Optional[:class:`bool`]
        Whether to fail if the user can't be upgraded to a member.

    Returns
    -------
    Optional[:class:`bool`]
        Whether the action can be executed.

    Raises
    ------
    """
    bot: DuckBot = interaction.client  # type: ignore
    guild: discord.Guild = interaction.guild
    user: discord.Member = interaction.user
    if not interaction.user:
        raise errors.ActionNotExecutable('Somehow, I think you don\'t exist. `Interaction.user` was None...\n'
                                         'Join our support server to get help, or try again later.')
    if not target:
        raise errors.ActionNotExecutable('Somehow the target was not found.')
    if not guild:
        raise errors.ActionNotExecutable('This action cannot be executed in DM.')
    if not isinstance(target, Member):
        upgraded = await bot.get_or_fetch_member(guild, target)
        if upgraded is None:
            if fail_if_not_upgrade:
                raise errors.ActionNotExecutable('That user is not a member of this server.')
        else:
            target = upgraded

    if interaction.user == target:
        raise errors.ActionNotExecutable('You cannot execute this action on yourself!')
    if guild.owner == target:
        raise errors.ActionNotExecutable('I cannot execute any action on the server owner!')

    if isinstance(target, Member):
        if guild.me.top_role <= target.top_role:
            raise base_errors.HierarchyException(target)
        if guild.owner == interaction.user:
            return
        if user.top_role <= target.top_role:
            raise base_errors.HierarchyException(target, author_error=True)


async def has_permissions(
        interaction: discord.Interaction,
        **perms: bool,
) -> None:
    """|coro|
    
    Checks permissions of the invoking interaction user.
    
    """
    if interaction.channel:
        permissions = interaction.channel.permissions_for(interaction.user)
    elif isinstance(interaction.user, discord.Member):
        permissions = interaction.user.guild_permissions
    else:
        permissions = discord.Permissions.none()

    missing_p = {perm: value for perm, value in perms.items() if getattr(permissions, perm) != value}

    needed = [p for p, v in missing_p.items() if v]
    missing = [p for p, v in missing_p.items() if not v]
    if any((missing, needed)):
        raise errors.PermissionsError(needed=needed, missing=missing)

async def bot_has_permissions(
        interaction: discord.Interaction,
        **perms: bool,
) -> None:
    """|coro|

    Checks permissions of the invoking interaction user.

    """
    if interaction.channel and interaction.guild:
        permissions = interaction.channel.permissions_for(interaction.guild.me)
    elif interaction.guild:
        permissions = interaction.guild.me.guild_permissions
    else:
        permissions = discord.Permissions.none()

    missing_p = {perm: value for perm, value in perms.items() if getattr(permissions, perm) != value}

    needed = [p for p, v in missing_p.items() if v]
    missing = [p for p, v in missing_p.items() if not v]
    if any((missing, needed)):
        raise errors.BotPermissionsError(needed=needed, missing=missing)

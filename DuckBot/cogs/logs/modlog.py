import datetime
import typing
from typing import List, Optional

import asyncpg
import discord
from discord import Colour as Col
from discord.ext import commands

from ._base import LoggingBase

colors = {
    "ban": Col.red(),
    "unban": Col.green(),
    "kick": Col.orange(),
    "role_add": Col.green(),
    "role_remove": Col.red(),
    "timeout_grant": Col.red(),
    "timeout_remove": Col.green(),
    "timeout_update": Col.orange(),
}


def format_action(action: str) -> str:
    return action.replace("_", " ").title()


def strip(obj: typing.Any) -> str:
    """Strips the object of all mentions and other stuff
    Like markdown formatting, etc."""
    if obj is None:
        return ''
    return discord.utils.escape_mentions(discord.utils.escape_markdown(str(obj)))


class ModLogs(LoggingBase):
    base_query = """
    CREATE TABLE IF NOT EXISTS modlogs.modlogs_{} (
        case_id    serial                   primary key,
        action     text                     not null,
        reason     text,
        offender   bigint                   not null,
        role_id    bigint,
        moderator  bigint,
        message_id bigint,
        log_date   timestamp with time zone not null
    )"""

    async def is_guild_logged(self, guild: discord.Guild) -> bool:
        """
        Checks if a guild is logged
        """
        return await self.bot.db.fetchval("SELECT modlog FROM prefixes WHERE guild_id = $1", guild.id) is not None

    async def get_modlog(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """
        Gets the modlog channel for a guild
        """
        ch_id = await self.bot.db.fetchval("SELECT modlog FROM prefixes WHERE guild_id = $1", guild.id)
        if ch_id is None:
            return None
        return guild.get_channel(ch_id)  # type: ignore

    def build_embed(
        self,
        action: str,
        offender: Optional[discord.abc.User],
        case_id: int,
        role: Optional[discord.Role] = None,
        log_date: Optional[datetime.datetime] = None,
        moderator: Optional[discord.abc.User] = None,
        reason: Optional[str] = None,
    ) -> discord.Embed:
        """
        Builds an embed for the modlog
        """
        embed = discord.Embed(
            color=colors.get(action, Col.dark_grey()),
            title=f"{format_action(action)} | Case #{case_id}",
            timestamp=log_date or discord.utils.utcnow(),
        )

        information = [f"**Offender**: {strip(offender)} ({offender and offender.id})"]

        no_reason = f"No reason provided. Do `db.modlogs reason {case_id} <reason>` to add one."

        if role is not None:
            information.append(f"**Role**: {strip(role)} ({role.id})")

        if moderator is not None:
            information.append(f"**Moderator**: {strip(moderator)} ({moderator.id})")
        else:
            information.append(f"**Moderator**: Unknown moderator. Do `db.modlogs setmod {case_id} <user>` to add one.")

        information.append(f"**Reason**: {strip(reason) or no_reason}")

        embed.description = "\n".join(information)

        return embed

    async def log_action(
        self,
        action: str,
        guild: discord.Guild,
        offender: discord.abc.User,
        role: Optional[discord.Role] = None,
        moderator: Optional[discord.abc.User] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Logs an action to the Mod Log"""
        if not (modlog := await self.get_modlog(guild)):
            return
        now_date = discord.utils.utcnow()
        args = [
            "INSERT INTO modlogs.modlogs_{} (action, reason, offender, role_id, moderator, log_date) "
            "VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id".format(guild.id),
            action,
            reason,
            offender.id,
            getattr(role, "id", None),
            getattr(moderator, "id", None),
            now_date,
        ]
        try:
            case_id = await self.bot.db.fetchval(*args)
        except asyncpg.UndefinedTableError:
            await self.bot.db.execute(self.base_query.format(guild.id))
            case_id = await self.bot.db.fetchval(*args)

        embed = self.build_embed(
            action=action,
            offender=offender,
            case_id=case_id,
            role=role,
            log_date=now_date,
            moderator=moderator,
            reason=reason,
        )
        message = await modlog.send(embed=embed)
        await self.bot.db.execute(
            "UPDATE modlogs.modlogs_{} SET message_id = $1 WHERE case_id = $2".format(guild.id), message.id, case_id
        )

    async def try_user(self, u_id):
        try:
            return self.bot.get_user(u_id) or await self.bot.fetch_user(u_id)
        except discord.NotFound:
            return None

    async def update_message(self, guild: discord.Guild, case_id: int) -> None:
        """
        Updates an action in the Mod Log
        """
        if not (modlog := await self.get_modlog(guild)):
            return
        case = await self.bot.db.fetchrow(
            "SELECT action, reason, offender, role_id, moderator, message_id, log_date FROM modlogs.modlogs_774561547930304536 WHERE case_id = $1".format(
                guild.id
            ),
            case_id,
        )
        if not case:
            return
        action, reason, offender, role_id, moderator, message_id, log_date = case
        embed = self.build_embed(
            action=action,
            offender=await self.try_user(offender),
            case_id=case_id,
            role=guild.get_role(role_id),
            log_date=log_date,
            moderator=await self.try_user(moderator),
            reason=reason,
        )
        try:
            await modlog.get_partial_message(message_id).edit(embed=embed)
        except discord.HTTPException:
            print("Failed to update message")

    @commands.Cog.listener('on_member_update')
    async def member_update_modlog(self, before: discord.Member, after: discord.Member):
        """
        Logged actions:
            - Special Role Add
            - Special Role Remove
            - Timeout grant
            - Timeout remove
            - Timeout update
        """
        if not await self.is_guild_logged(before.guild):
            return

        if before.timed_out_until != after.timed_out_until:

            if before.timed_out_until is None and after.timed_out_until is not None:
                action = 'timeout_grant'
            elif before.timed_out_until is not None and after.timed_out_until is None:
                action = 'timeout_remove'
            else:
                action = 'timeout_update'

            moderator = reason = None
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if (
                    hasattr(entry.before, 'timed_out_until')
                    and hasattr(entry.after, 'timed_out_until')
                    and entry.target == after
                ):
                    moderator = entry.user
                    reason = entry.reason

            await self.log_action(action=action, guild=before.guild, offender=after, moderator=moderator, reason=reason)

        if before.roles != after.roles:
            special_roles: List[int] = await self.bot.db.fetchval(
                "SELECT special_roles FROM prefixes WHERE guild_id = $1", before.guild.id
            )

            if special_roles:
                added_roles = set(after.roles) - set(before.roles)
                removed_roles = set(before.roles) - set(after.roles)
                for role in added_roles:
                    if role.id in special_roles:
                        action = 'role_add'
                        moderator = reason = None
                        async for entry in before.guild.audit_logs(
                            limit=4, action=discord.AuditLogAction.member_role_update
                        ):
                            if hasattr(entry.before, 'roles') and hasattr(entry.after, 'roles') and entry.target == after:
                                if role in entry.before.roles:
                                    moderator = entry.user
                                    reason = entry.reason
                                    break
                        await self.log_action(
                            action=action, guild=before.guild, offender=after, role=role, moderator=moderator, reason=reason
                        )
                for role in removed_roles:
                    if role.id in special_roles:
                        action = 'role_remove'
                        moderator = reason = None
                        async for entry in before.guild.audit_logs(
                            limit=4, action=discord.AuditLogAction.member_role_update
                        ):
                            if hasattr(entry.before, 'roles') and hasattr(entry.after, 'roles') and entry.target == after:
                                if role in entry.after.roles:
                                    moderator = entry.user
                                    reason = entry.reason
                                    break
                        await self.log_action(
                            action=action, guild=before.guild, offender=after, role=role, moderator=moderator, reason=reason
                        )

    @commands.Cog.listener('on_member_ban')
    async def member_ban_modlog(self, guild: discord.Guild, user: discord.User):
        """
        Logged actions:
            - Ban
        """
        if not await self.is_guild_logged(guild):
            return

        moderator = reason = None
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target == user:
                moderator = entry.user
                reason = entry.reason
                break

        await self.log_action(action='ban', guild=guild, offender=user, moderator=moderator, reason=reason)

    @commands.Cog.listener('on_member_unban')
    async def member_unban_modlog(self, guild: discord.Guild, user: discord.User):
        """
        Logged actions:
            - Unban
        """
        if not await self.is_guild_logged(guild):
            return

        moderator = reason = None
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            if entry.target == user:
                moderator = entry.user
                reason = entry.reason
                break

        await self.log_action(action='unban', guild=guild, offender=user, moderator=moderator, reason=reason)

    @commands.Cog.listener('on_member_remove')
    async def member_remove_modlog(self, member: discord.Member):
        """
        Logged actions:
            - Kick
        """
        if not await self.is_guild_logged(member.guild):
            return

        moderator = reason = None
        async for entry in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.kick):
            if entry.target == member:
                moderator = entry.user
                reason = entry.reason
                break

        if not moderator:
            return

        await self.log_action(action='kick', guild=member.guild, offender=member, moderator=moderator, reason=reason)

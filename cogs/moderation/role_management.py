import asyncio

import discord
import humanize.time
from discord.ext import commands

from ._base import ModerationBase
from bot import CustomContext
from helpers.helper import RoleConverter

class RoleManagementCommands(ModerationBase):
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True, name='role')
    async def role_group(self, ctx: CustomContext, member: discord.Member, *, argument: str):
        """
        Manages roles in your channel.
        """

        role = await RoleConverter().convert(ctx, argument)

        if role >= ctx.author.top_role: # type: ignore # check in __init__.py file to insure guild only.
            raise commands.BadArgument('❌ **|** You cannot assign roles higher (or equal to) your own top role!')
        if not role.is_assignable():
            raise commands.BadArgument('❌ **|** I lack permissions to add that role!')
        await member.add_roles(role, reason=f'Role added by {ctx.author} (ID: {ctx.author.id})')
        await ctx.send(
            f'✅ **|** Added role **{role}** to **{member}**', allowed_mentions=discord.AllowedMentions.none(), reply=False
        )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role_group.group(invoke_without_command=True, name='remove')
    async def role_remove(self, ctx: CustomContext, member: discord.Member, *, argument: str):
        """
        Removes a role from a user.
        """

        role = await RoleConverter().convert(ctx, argument)

        if role >= ctx.author.top_role and not ctx.guild.owner == ctx.author: # type: ignore # check in __init__.py file to insure guild only.
            raise commands.BadArgument('❌ **|** You cannot remove roles higher (or equal to) your own top role!')
        if not role.is_assignable():
            raise commands.BadArgument('❌ **|** I lack permissions to add that role!')
        await member.remove_roles(role, reason=f'Role removed by {ctx.author} (ID: {ctx.author.id})')
        await ctx.send(
            f'✅ **|** Removed role **{role}** from **{member}**',
            allowed_mentions=discord.AllowedMentions.none(),
            reply=False,
        )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role_group.command(name='all')
    async def role_all(self, ctx: CustomContext, *, argument: str):
        """
        Adds a role to all users.
        """

        role = await RoleConverter().convert(ctx, argument)

        if role >= ctx.author.top_role and not ctx.guild.owner == ctx.author: # type: ignore # check in __init__.py file to insure guild only.
            raise commands.BadArgument('❌ **|** You cannot assign roles higher (or equal to) your own top role!')
        if not role.is_assignable():
            raise commands.BadArgument('❌ **|** I lack permissions to add that role!')

        await ctx.send(
            f'⏳ **|** Adding role to all users... **ETA: in {humanize.time.precisedelta((ctx.guild.member_count - len(role.members)) * 1.2)}**',
            reply=False,
        )

        for member in ctx.guild.members:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f'Bulk-added added by {ctx.author} (ID: {ctx.author.id})')
                    await asyncio.sleep(1)
                except discord.Forbidden:
                    raise commands.BadArgument('❌ **|** I do not have permission to add this role!')

        await ctx.send(
            f'✅ **|** Added role **{role}** to all users!', allowed_mentions=discord.AllowedMentions.none(), reply=False
        )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role_remove.command(name='all')
    async def role_remove_all(self, ctx: CustomContext, *, argument: str):
        """
        Removes a role from all users.
        """

        role = await RoleConverter().convert(ctx, argument)

        if role >= ctx.author.top_role and not ctx.guild.owner == ctx.author: # type: ignore # check in __init__.py file to insure guild only.
            raise commands.BadArgument('❌ **|** You cannot remove roles higher (or equal to) your own top role!')
        if not role.is_assignable():
            raise commands.BadArgument('❌ **|** I lack permissions to add that role!')

        await ctx.send(
            f'⏳ **|** Removing role from all users... **ETA: in {humanize.time.precisedelta((ctx.guild.member_count - len(role.members)) * 1.2)}**',
            reply=False,
        )

        for member in ctx.guild.members:
            if role in member.roles:
                try:
                    await member.remove_roles(role, reason=f'Bulk-removed role by {ctx.author} (ID: {ctx.author.id})')
                    await asyncio.sleep(1)
                except discord.Forbidden:
                    raise commands.BadArgument('❌ **|** I do not have permission to remove this role!')
                except discord.HTTPException:
                    raise commands.BadArgument('⚠ **|** Something went wrong !')

        await ctx.send(
            f'✅ **|** Removed role **{role}** from all users!', allowed_mentions=discord.AllowedMentions.none(), reply=False
        )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role_remove.command(name='add_all')
    async def role_add_all(self, ctx: CustomContext, *, argument: str):
        """
        Adds a role to all users.
        """

        role = await RoleConverter().convert(ctx, argument)

        if role >= ctx.author.top_role and not ctx.guild.owner == ctx.author: # type: ignore # check in __init__.py file to insure guild only.
            raise commands.BadArgument('❌ **|** You cannot add roles higher (or equal to) your own top role!')
        if not role.is_assignable():
            raise commands.BadArgument('❌ **|** I lack permissions to add that role!')

        await ctx.send(
            f'⏳ **|** Adding role to all users... **ETA: in {humanize.time.precisedelta((ctx.guild.member_count - len(role.members)) * 1.2)}**',
            reply=False,
        )

        for member in ctx.guild.members:
            if role in member.roles:
                try:
                    await member.remove_roles(role, reason=f'Bulk-added role by {ctx.author} (ID: {ctx.author.id})')
                    await asyncio.sleep(1)
                except discord.Forbidden:
                    raise commands.BadArgument('❌ **|** I do not have permission to add this role!')
                except discord.HTTPException:
                    raise commands.BadArgument('⚠ **|** Something went wrong !')

        await ctx.send(
            f'✅ **|** Added role **{role}** to all users!', allowed_mentions=discord.AllowedMentions.none(), reply=False
        )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role_group.command(name='list')
    async def role_list(self, ctx: CustomContext):
        """Lists all roles."""
        roles = sorted(
            [role for role in ctx.guild.roles if not role.is_default()], key=lambda role: role.position, reverse=True
        )
        roles = [f'`{discord.utils.remove_markdown(role.name)}`' for role in roles]
        roles = ', '.join(roles)
        await ctx.send(f'📋 **|** Roles: {roles}', allowed_mentions=discord.AllowedMentions.none(), reply=False)

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role_group.command(name='multi-give')
    async def role_multi_give(self, ctx: CustomContext, roles: commands.Greedy[discord.Role], *members: discord.Member):
        """
        Gives multiple roles to multiple users.
        """
        if not roles:
            raise commands.BadArgument('❌ **|** You must specify at least one role!')
        for role in roles:
            if role >= ctx.author.top_role and not ctx.guild.owner == ctx.author: # type: ignore # check in __init__.py file to insure guild only.
                raise commands.BadArgument(
                    f'❌ **|** Sorry but **you** can\'t add `@{role.name}` because its higher (or equal to) **your top role**!'
                )
            if not role.is_assignable():
                raise commands.BadArgument(f'❌ **|** Sorry but **I** can\'t add the role `@{role.name}`!')

        await ctx.send(
            f'⏳ **|** Adding roles to all users... **ETA: in {humanize.time.precisedelta((len(members) * len(roles)) * 1.2)}**',
            reply=False,
        )

        for member in members:
            await member.add_roles(*roles, reason=f'Bulk-added added by {ctx.author} (ID: {ctx.author.id})')
            await asyncio.sleep(1)

        await ctx.send(f'✅ **|** Added roles to all users!', allowed_mentions=discord.AllowedMentions.none(), reply=False)

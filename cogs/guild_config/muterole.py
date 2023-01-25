import asyncio
import time

import discord
from discord.ext import commands

import errors
from bot import CustomContext
from ._base import ConfigBase


class MuteRole(ConfigBase):
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole(self, ctx: CustomContext, new_role: discord.Role = None):
        """
        Sets the mute-role. If no role is specified, shows the current mute role.
        """
        if ctx.invoked_subcommand is None:
            if new_role:
                await self.bot.db.execute(
                    "INSERT INTO guilds(guild_id, muted_id) VALUES ($1, $2) "
                    "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                    ctx.guild.id,
                    new_role.id,
                )

                return await ctx.send(
                    f"Updated the muted role to {new_role.mention}!", allowed_mentions=discord.AllowedMentions().none()
                )

            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                raise errors.MuteRoleNotFound

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                raise errors.MuteRoleNotFound

            return await ctx.send(
                f"This server's mute role is {role.mention}" f"\nChange it with the `muterole [new_role]` command",
                allowed_mentions=discord.AllowedMentions().none(),
            )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @muterole.command(name="remove", aliases=["unset"])
    async def muterole_remove(self, ctx: CustomContext):
        """
        Unsets the mute role for the server,
        note that this will NOT delete the role, but only remove it from the bot's database!
        If you want to delete it, do "%PRE%muterole delete" instead
        """
        await self.bot.db.execute(
            "INSERT INTO guilds(guild_id, muted_id) VALUES ($1, $2) " "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
            ctx.guild.id,
            None,
        )

        return await ctx.send(f"Removed this server's mute role!", allowed_mentions=discord.AllowedMentions().none())

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @muterole.command(name="create")
    async def muterole_create(self, ctx: CustomContext):
        starting_time = time.monotonic()

        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', ctx.guild.id)

        if mute_role:
            mute_role = ctx.guild.get_role(mute_role)
            if mute_role:
                raise commands.BadArgument('You already have a mute role')

        await ctx.send(
            f"Creating Muted role, and applying it to all channels."
            f"\nThis may take awhile ETA: {len(ctx.guild.channels)} seconds."
        )

        async with ctx.typing():
            permissions = discord.Permissions(send_messages=False, add_reactions=False, connect=False, speak=False)
            role = await ctx.guild.create_role(
                name="Muted",
                colour=0xFF4040,
                permissions=permissions,
                reason=f"DuckBot mute-role creation. Requested " f"by {ctx.author} ({ctx.author.id})",
            )
            await self.bot.db.execute(
                "INSERT INTO guilds(guild_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                ctx.guild.id,
                role.id,
            )

            modified = 0
            for channel in ctx.guild.channels:
                perms = channel.overwrites_for(role)
                # noinspection PyTypeChecker
                perms.update(send_messages=None, add_reactions=None, create_public_threads=None, create_private_threads=None)
                try:
                    await channel.set_permissions(
                        role,
                        overwrite=perms,
                        reason=f"DuckBot mute-role creation. Requested " f"by {ctx.author} ({ctx.author.id})",
                    )
                    modified += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
                await asyncio.sleep(1)

            ending_time = time.monotonic()
            complete_time = ending_time - starting_time
            await ctx.send(
                f"done! took {round(complete_time, 2)} seconds"
                f"\nSet permissions for {modified} channel{'' if modified == 1 else 's'}!"
            )

    @muterole.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole_delete(self, ctx: CustomContext):
        """
        Deletes the server's mute role if it exists.
        # If you want to keep the role but not
        """
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            await self.bot.db.execute(
                "INSERT INTO guilds(guild_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                ctx.guild.id,
                None,
            )

            return await ctx.send(
                "It seems like the muted role was already deleted, or I can't find it right now!"
                "\n I removed it from my database. If the mute role still exists, delete it manually"
            )

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to delete that role!")

        if role > ctx.author.top_role:
            return await ctx.send("You're not high enough in role hierarchy to delete that role!")

        try:
            await role.delete(reason=f"Mute role deletion. Requested by {ctx.author} ({ctx.author.id})")
        except discord.Forbidden:
            return await ctx.send("I can't delete that role! But I deleted it from my database")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while deleting the muted role!")
        await self.bot.db.execute(
            "INSERT INTO guilds(guild_id, muted_id) VALUES ($1, $2) " "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
            ctx.guild.id,
            None,
        )
        await ctx.send("🚮")

    @muterole.command(name="fix")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole_fix(self, ctx: CustomContext):
        async with ctx.typing():
            starting_time = time.monotonic()
            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                raise errors.MuteRoleNotFound

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                raise errors.MuteRoleNotFound

            cnf = await ctx.confirm(f'Are you sure you want to change the permissions for **{role.name}** in all channels?')
            if not cnf:
                return

            modified = 0
            for channel in ctx.guild.channels:
                perms = channel.overwrites_for(role)
                perms.update(
                    send_messages=False,
                    add_reactions=False,
                    connect=False,
                    speak=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    send_messages_in_threads=False,
                )
                try:
                    await channel.set_permissions(
                        role,
                        overwrite=perms,
                        reason=f"DuckBot mute-role creation. Requested " f"by {ctx.author} ({ctx.author.id})",
                    )
                    modified += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
                await asyncio.sleep(1)

            ending_time = time.monotonic()
            complete_time = ending_time - starting_time
            await ctx.send(
                f"done! took {round(complete_time, 2)} seconds"
                f"\nSet permissions for {modified} channel{'' if modified == 1 else 's'}!"
            )

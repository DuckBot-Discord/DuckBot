import contextlib
import datetime
import inspect
import typing

from ._base import ModerationBase
from discord.ext import commands
from discord.ext.tasks import loop

from helpers.context import CustomContext
from helpers.time_inputs import ShortTime, human_timedelta
import discord


def ensure_muterole(*, required: bool = True):
    async def predicate(ctx: CustomContext):
        if not ctx.guild:
            raise commands.BadArgument('Only servers can have mute roles')
        if not required:
            return True
        if not (role := await ctx.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', ctx.guild.id)):
            raise commands.BadArgument('This server has no mute role set')
        if not (role := ctx.guild.get_role(role)):
            raise commands.BadArgument("It seems like I could not find this server's mute role. Was it deleted?")
        if role >= ctx.me.top_role:
            raise commands.BadArgument("This server's mute role seems to be above my top role. I can't assign it!")
        return True

    return commands.check(predicate)  # type: ignore


async def muterole(ctx) -> discord.Role:
    if not ctx.guild:
        raise commands.BadArgument('Only servers can have mute roles')
    if not (role := await ctx.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', ctx.guild.id)):
        raise commands.BadArgument('This server has no mute role set')
    if not (role := ctx.guild.get_role(role)):
        raise commands.BadArgument("It seems like I could not find this server's mute role. Was it deleted?")
    if role >= ctx.me.top_role:
        raise commands.BadArgument("This server's mute role seems to be above my top role. I can't assign it!")
    return role


class MuteCommands(ModerationBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temporary_mutes.start()

    def cog_unload(self):
        self.temporary_mutes.cancel()

    @loop()
    async def temporary_mutes(self):
        next_task = await self.bot.db.fetchrow('SELECT * FROM temporary_mutes ORDER BY end_time LIMIT 1')
        if next_task is None:
            self.temporary_mutes.cancel()
            return

        await discord.utils.sleep_until(next_task['end_time'])

        guild: discord.Guild = self.bot.get_guild(next_task['guild_id'])

        if guild:
            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', next_task['guild_id'])
            if mute_role:
                role = guild.get_role(int(mute_role))
                if isinstance(role, discord.Role):
                    if not role > guild.me.top_role:
                        try:
                            member = guild.get_member(next_task['member_id']) or await guild.fetch_member(
                                next_task['member_id']
                            )
                            if member:
                                await member.remove_roles(role)
                        except discord.HTTPException:
                            pass

        await self.bot.db.execute(
            'DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)',
            next_task['guild_id'],
            next_task['member_id'],
        )

    @temporary_mutes.before_loop
    async def wait_for_bot_ready(self):
        await self.bot.wait_until_ready()

    def mute_task(self):
        if self.temporary_mutes.is_running():
            self.temporary_mutes.restart()
        else:
            self.temporary_mutes.start()

    # Indefinitely mute member

    @commands.command()
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None) -> discord.Message:
        """
        Mutes a member indefinitely.
        """
        if not self.can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        try:
            await member.add_roles(
                role, reason=f"Muted by {ctx.author} ({ctx.author.id}) {f'for: {reason}' if reason else ''}"[0:500]
            )
        except discord.Forbidden:
            raise commands.BadArgument(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute(
            'DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)', ctx.guild.id, member.id
        )

        self.mute_task()

        if ctx.channel.permissions_for(role).send_messages_in_threads:
            embed = discord.Embed(
                color=discord.Color.red(),
                description='The mute role has permissions to create threads!'
                '\nYou may want to fix that using the `muterole fix` command!'
                '\nIf you don\'t want to receive security warnings, you can do `warnings off` command',
                title='Warning',
            )
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.send(embed=embed)

        if reason:
            reason = f"\nReason: {reason}"
        return await ctx.send(
            f"**{ctx.author}** muted **{member}**{reason or ''}", allowed_mentions=discord.AllowedMentions().none()
        )

    @commands.command(
        aliases=['mass-mute', 'multi_mute', 'mass_mute', 'multimute', 'massmute'],
        name='multi-mute',
        usage='<members>... [reason]',
    )
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def multi_mute(
        self, ctx: CustomContext, members: commands.Greedy[discord.Member], reason: str = None
    ) -> discord.Message:
        """
        Mutes a lot of members indefinitely indefinitely.
        """

        role = await muterole(ctx)

        reason = f"Mute by {ctx.author} ({ctx.author.id}){f': {reason}' if reason else ''}"[0:500]

        successful: typing.List[discord.Member] = []
        failed_perms: typing.List[discord.Member] = []
        failed_internal: typing.List[discord.Member] = []

        for member in members:
            if not self.can_execute_action(ctx, ctx.author, member):
                failed_perms.append(member)
                continue

            try:
                await member.add_roles(role, reason=reason)
                successful.append(member)
            except (discord.Forbidden, discord.HTTPException):
                failed_internal.append(member)
                continue

            await self.bot.db.execute(
                'DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)', ctx.guild.id, member.id
            )

        failed = ""

        if failed_perms:
            failed += (
                f"\n**{len(failed_perms)} failed** because the author didn't have the required permissions to mute them."
            )
        if failed_internal:
            failed += f"\n**{len(failed_internal)}** failed due to a discord error."

        await ctx.send(
            f"**Successfully muted {len(successful)}/{len(members)}**:"
            f"\n**Successful:** {', '.join([m.display_name for m in successful])}{failed}"
        )

        self.mute_task()

    @commands.command(aliases=['hardmute'], name='hard-mute')
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def hardmute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None) -> discord.Message:
        """
        Mutes a member indefinitely, and removes all their roles.
        """
        if not self.can_execute_action(ctx, ctx.author, member):
            return await ctx.send("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        roles = [r for r in member.roles if not r.is_assignable()] + [role]

        try:
            await member.edit(
                roles=roles, reason=f"Mute by {ctx.author} ({ctx.author.id}) {f'for {reason}' if reason else ''}"[0:500]
            )
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute(
            'DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)', ctx.guild.id, member.id
        )

        self.mute_task()

        not_removed = [r for r in member.roles if not r.is_assignable() and not r.is_default()]
        nl = '\n'
        if not reason:
            return await ctx.send(
                f"✅ **|** **{ctx.author}** hard-muted **{member}** "
                f"{f'{nl}⚠ **|** Could not remove **{len(not_removed)}** role(s).' if not_removed else ''}",
                allowed_mentions=discord.AllowedMentions().none(),
            )
        return await ctx.send(
            f"✅ **|** **{ctx.author}** hard-muted **{member}**"
            f"\nℹ **| With reason:** {reason[0:1600]}"
            f"{f'{nl}⚠ **|** Could not remove **{len(not_removed)}** role(s).' if not_removed else ''}",
            allowed_mentions=discord.AllowedMentions().none(),
        )

    @commands.command()
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """
        Unmutes a member
        """
        if not self.can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument("You're not high enough in role hierarchy to mute that member.")

        role = await muterole(ctx)

        try:
            await member.remove_roles(
                role, reason=f"Unmute by {ctx.author} ({ctx.author.id}) {f'for {reason}' if reason else ''}"[0:500]
            )
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to remove the `{role.name}` role")

        await self.bot.db.execute(
            'DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)', ctx.guild.id, member.id
        )

        self.mute_task()

        reason = f"\nReason: {reason}" if reason else ""
        await ctx.send(f"**{ctx.author}** unmuted **{member}**{reason}", allowed_mentions=discord.AllowedMentions().none())

    @commands.command(
        aliases=['mass-unmute', 'multi_unmute', 'mass_unmute', 'massunmute', 'multiunmute'],
        name='multi-unmute',
        usage='<members...> [reason]',
    )
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def multi_unmute(
        self, ctx: CustomContext, members: commands.Greedy[discord.Member], reason: str = None
    ) -> discord.Message:
        """
        Mutes a lot of members indefinitely indefinitely.
        """
        role = await muterole(ctx)

        if not members:
            raise commands.MissingRequiredArgument(
                inspect.Parameter(
                    'members', annotation=commands.Greedy[discord.Member], kind=inspect.Parameter.POSITIONAL_OR_KEYWORD
                )
            )

        successful: typing.List[discord.Member] = []
        failed_perms: typing.List[discord.Member] = []
        failed_internal: typing.List[discord.Member] = []

        for member in members:
            if not self.can_execute_action(ctx, ctx.author, member):
                failed_perms.append(member)
                continue

            try:
                await member.remove_roles(role, reason=reason)
                successful.append(member)
            except (discord.Forbidden, discord.HTTPException):
                failed_internal.append(member)
                continue

            await self.bot.db.execute(
                'DELETE FROM temporary_mutes WHERE (guild_id, member_id) = ($1, $2)', ctx.guild.id, member.id
            )

        await ctx.send(
            f"**Successfully unmuted {len(successful)}/{len(members)}**:"
            f"\n**Successful:** {', '.join([m.display_name for m in successful])}"
            f"\n**Failed:** {', '.join([m.display_name for m in failed_perms + failed_internal])}"
        )

        self.mute_task()

    @commands.command()
    @ensure_muterole()
    @commands.bot_has_permissions(manage_roles=True)
    async def selfmute(self, ctx, *, duration: ShortTime):
        """
        Temporarily mutes yourself for the specified duration.
          note that: `relative_time` must be a short time!
        for example: 1d, 5h, 3m or 25s, or a combination of those, like 3h5m25s (without spaces between these times)
        You can only mute yourself for a maximum of 24 hours and a minimum of 5 minutes.
        # ❓❔ Do not ask a moderator to unmute you! ❓❔
        """
        reason = "self mute"

        role = await muterole(ctx)

        created_at = ctx.message.created_at
        if duration.dt > (created_at + datetime.timedelta(days=1)):
            return await ctx.send('Duration is too long. Must be at most 24 hours.')

        if duration.dt < (created_at + datetime.timedelta(minutes=5)):
            return await ctx.send('Duration is too short. Must be at least 5 minutes.')

        delta = human_timedelta(duration.dt, source=created_at)
        warning = (
            f"_Are you sure you want to mute yourself for **{delta}**?_" f"\n**__Don't ask the moderators to undo this!__**"
        )

        if not await ctx.confirm(warning, delete_after_confirm=True):
            return

        try:
            await ctx.author.add_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute(
            "INSERT INTO temporary_mutes(guild_id, member_id, reason, end_time) "
            "VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, member_id) DO "
            "UPDATE SET reason = $3, end_time = $4",
            ctx.guild.id,
            ctx.author.id,
            reason,
            duration.dt,
        )

        self.mute_task()

        await ctx.send(f"{self.bot.constants.SHUT_SEAGULL} 👍")

    # Temp-mute

    @commands.command()
    @ensure_muterole()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def tempmute(self, ctx, member: discord.Member, *, duration: ShortTime):
        """
        Temporarily mutes a member for the specified duration.
        # Duration must be a short time, for example: 1s, 5m, 3h, or a combination of those, like 3h5m25s
        """

        reason = f"Temporary mute by {ctx.author} ({ctx.author.id})"

        if not self.can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument("You're not high enough in role hierarchy to do that!")

        role = await muterole(ctx)

        created_at = ctx.message.created_at
        if duration.dt < (created_at + datetime.timedelta(minutes=1)):
            return await ctx.send('Duration is too short. Must be at least 1 minute.')

        delta = human_timedelta(duration.dt, source=created_at)

        try:
            await member.add_roles(role, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await self.bot.db.execute(
            "INSERT INTO temporary_mutes(guild_id, member_id, reason, end_time) "
            "VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, member_id) DO "
            "UPDATE SET reason = $3, end_time = $4",
            ctx.guild.id,
            member.id,
            reason,
            duration.dt,
        )

        self.mute_task()

        await ctx.send(f"**{ctx.author}** muted **{member}** for **{delta}**")

    @commands.Cog.listener('on_guild_channel_create')
    async def automatic_channel_update(self, channel: discord.abc.GuildChannel) -> None:
        """
        Adds mute overwrites to any newly created channels.
        """
        if not channel.permissions_for(channel.guild.me).manage_channels:
            return
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM guilds WHERE guild_id = $1', channel.guild.id)
        if not mute_role:
            return
        role = channel.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            return
        if role > channel.guild.me.top_role:
            return

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
        return await channel.set_permissions(role, overwrite=perms, reason="DuckBot automatic mute role permissions")

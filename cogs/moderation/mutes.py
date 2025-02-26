from __future__ import annotations

import asyncio
import logging
import datetime
import itertools
import collections
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, NamedTuple, TypeVar, Literal, Callable, Awaitable, overload

import discord
from discord.ext import commands, menus

from utils import (
    VerifiedMember,
    SilentCommandError,
    MemberNotMuted,
    NoMutedRole,
    Timer,
    DuckCog,
    DuckContext,
    UserFriendlyTime,
    ShortTime,
    View,
    ViewMenuPages,
    plural as plural_fmt,
    human_timedelta,
    human_join,
    command,
    group,
    safe_reason,
    mdr,
)

if TYPE_CHECKING:
    from asyncpg import Connection

log = logging.getLogger(__name__)


GuildChannelT_co = TypeVar('GuildChannelT_co', bound='discord.abc.GuildChannel', covariant=True)


class plural(plural_fmt):
    def __format__(self, format_spec: str) -> str:
        formatted = super().__format__(format_spec)
        return formatted.removeprefix(f"{self.value} ")


class WarningsPageSource(menus.ListPageSource):
    def __init__(
        self,
        entries: list[tuple[GuildChannelT_co, list[str]]],
    ):
        super().__init__(entries, per_page=5)

    async def format_page(self, menu: ViewMenuPages, page: list[tuple[GuildChannelT_co, list[str]]]):
        embed = discord.Embed(
            title='These channels have some permissions that they shouldn\'t:',
            color=discord.Color.red(),
            description='Use `db.muterole fix` to update permissions.',
        )
        for channel, error_message_keys in page:
            fmt = human_join(
                error_message_keys,
                delim='`, `',
                final='` and `',
                spaces=False,
                fmt_key=lambda perm: perm.replace('_', ' ').title(),
            )

            embed.add_field(
                name=channel.mention,
                value=f"Not denied: `{fmt}`",
                inline=False,
            )
        return embed


class ShowWarnings(View):
    def __init__(
        self,
        context: DuckContext,
        page_source: WarningsPageSource,
    ):
        self.context = context
        self.page_source = page_source
        super().__init__(bot=context.bot)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user == self.context.author:
            return True
        await interaction.response.send_message('This is not your menu!', ephemeral=True)
        return False

    @discord.ui.button(label='view warnings')
    async def view_warnings(self, interaction: discord.Interaction, button: discord.ui.Button):
        menu = ViewMenuPages(self.page_source, ctx=self.context)
        await menu.start_ephemeral(interaction)


class MutedRole(NamedTuple):
    role: discord.Role
    errors: list[tuple[discord.abc.GuildChannel, list[str]]]


class RoleMode(Enum):
    no_sending = 0
    no_view_channel = 1


class RoleModeView(View):
    def __init__(self, ctx: DuckContext):
        self.value: RoleMode | None = None
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=30, bot=ctx.bot)

    @discord.ui.select(
        placeholder='Select Role Mode...',
        options=[
            discord.SelectOption(
                label='Basic', value='0', description='Users will be denied send messages and other permissions.'
            ),
            discord.SelectOption(label='Strict', value='1', description='Users will be denied view channel.'),
        ],
        cls=discord.ui.Select,  # This suppresses the stupid "Untyped function decorator" error. WHY does it even happen!?
    )
    async def view_mode_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.value = RoleMode(int(select.values[0]))

        if self.value is RoleMode.no_view_channel and not interaction.app_permissions.administrator:
            # FIXME: Cannot reliably set permissions to channel(s) when the bot is not an administrator, for some reason.
            await interaction.response.send_message(
                'Due to the way discord works, I cannot reliably deny "View Channel" unless I am an admin. '
                'Please temporarily allow me that permission, then you can deny it again. Sorry for the inconvenience!',
                ephemeral=True,
            )
            return

        self.stop()
        await interaction.response.defer()
        await interaction.delete_original_response()

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(content='Timed out waiting for a response...', view=None)
        return await super().on_timeout()


PERMISSIONS_TO_DENY = {
    RoleMode.no_sending: discord.Permissions(
        send_messages=True,
        create_instant_invite=True,
        send_messages_in_threads=True,
        create_public_threads=True,
        create_private_threads=True,
        connect=True,
    ),
    RoleMode.no_view_channel: discord.Permissions(
        view_channel=True,
        send_messages=True,
        create_instant_invite=True,
        send_messages_in_threads=True,
        create_public_threads=True,
        create_private_threads=True,
        connect=True,
    ),
}

_BASE = discord.Permissions.general() | discord.Permissions.membership()
CHANNEL_TYPE_PERMISSIONS_MAP = {
    discord.TextChannel: _BASE | discord.Permissions.text(),
    discord.ForumChannel: _BASE | discord.Permissions.text(),
    discord.VoiceChannel: _BASE | discord.Permissions.voice(),
    discord.StageChannel: _BASE | discord.Permissions.voice(),
    discord.CategoryChannel: discord.Permissions.all_channel(),
    discord.abc.GuildChannel: discord.Permissions.all_channel(),
}


class TempMute(DuckCog):
    """A helper cog to tempmute users."""

    async def _update_role_permissions(self, role: discord.Role, role_mode: RoleMode):
        """Updates the permissions for a role.

        Parameters
        ----------
        guild: discord.Guild
            The guild to create the muted role for.
        role_mode: RoleMode
            The guild permissions mode configuration.

        Returns
        -------
        Tuple[Role, int, int, int, int]
            The applied, partially applied, skipped and errored channel counts, respectively.
        """
        applied: int = 0
        partial: int = 0
        skipped: int = 0
        errored: int = 0

        guild = role.guild

        for channel in guild.channels:
            if channel == guild.rules_channel:
                skipped += 1
                continue
            if channel.permissions_for(guild.me).manage_permissions:
                try:
                    original_deny_perms = PERMISSIONS_TO_DENY[role_mode]
                    deny_perms = original_deny_perms & channel.permissions_for(channel.guild.me)

                    if self._get_missing_permissions_for(role, channel, role_mode):
                        await channel.set_permissions(
                            role,
                            overwrite=discord.PermissionOverwrite.from_pair(discord.Permissions(), deny_perms),
                            reason='DuckBot muted role auto-setup.',
                        )

                except discord.HTTPException:
                    errored += 1
                else:
                    if original_deny_perms == deny_perms:
                        applied += 1
                    else:
                        partial += 1
            else:
                skipped += 1

        return applied, partial, skipped, errored

    async def _create_muted_role(self, guild: discord.Guild, role_mode: RoleMode):
        """Creates a muted role for the guild.

        Parameters
        ----------
        guild: discord.Guild
            The guild to create the muted role for.
        role_mode: RoleMode
            The guild permissions mode configuration.

        Returns
        -------
        Tuple[int, int, int, int]
            The applied, partially applied, skipped and errored channel counts, respectively.
        """
        role = await guild.create_role(
            name='Muted',
            hoist=False,
            mentionable=False,
            reason='Muted role being created for tempmute.',
        )

        return role, *await self._update_role_permissions(role=role, role_mode=role_mode)

    @overload
    async def _get_muted_role(
        self,
        guild: discord.Guild,
        *,
        conn: Optional[Connection] = None,
        fail_if_no_role: Literal[False],
    ) -> Optional[discord.Role]: ...

    @overload
    async def _get_muted_role(
        self,
        guild: discord.Guild,
        *,
        conn: Optional[Connection] = None,
        fail_if_no_role: Literal[True] = ...,
    ) -> discord.Role: ...

    async def _get_muted_role(
        self,
        guild: discord.Guild,
        *,
        conn: Optional[Connection] = None,
        fail_if_no_role: bool = True,
    ) -> Optional[discord.Role]:
        """A helper function used internally. Will get the "Muted" role and return it whilst
        managing DB interactions.

        Parameters
        ----------
        guild: discord.Guild
            The guild to get the muted role from.
        conn: asyncpg.Connection
            The connection to use.
        fail_if_no_role: bool
            Wether to raise NoMutedRole if the role is not found.

        Returns
        -------
        discord.Role
            The muted role.

        Raises
        ------
        NoMutedRole
            Raised if there's no muted role in the guild.
        """

        async def actual_func(pg_conn: Connection):
            role_id: int | None = await pg_conn.fetchval('SELECT muted_role_id FROM guilds WHERE guild_id = $1', guild.id)
            role = guild.get_role(role_id or -1)
            if not role and fail_if_no_role:
                raise NoMutedRole()
            return role

        if not conn:
            async with self.bot.safe_connection() as conn:
                return await actual_func(conn)
        return await actual_func(conn)

    def _get_missing_permissions_for(self, muted_role: discord.Role, channel: discord.abc.GuildChannel, role_mode: RoleMode):
        """Gets the missing mute role permissions for a channel.

        Parameters
        ----------
        muted_role: discord.Role
            The muted role.
        channel: discord.abc.GuildChannel
            The channel to get permissions for.
        role_mode: RoleMode
            The role mode configured for the channel's guild.

        Returns
        -------
        list[str]
            The permissions that need to be denied in the channel.
        """
        if channel == channel.guild.rules_channel:
            return []
        # Bitwise operators W
        permissions_for_channel = CHANNEL_TYPE_PERMISSIONS_MAP[type(channel)]
        required = PERMISSIONS_TO_DENY[role_mode] & permissions_for_channel
        denied = channel.overwrites_for(muted_role).pair()[1]
        missing = required & ~denied
        return [k.replace('instant_', '') for k, v in missing if v]

    async def _prompt_role_mode(self, ctx: DuckContext, conn: Optional[Connection] = None) -> RoleMode:
        """Prompts the user to supply a role mode.

        Parameters
        ----------
        ctx: DuckContext
            The invocation context of the command.
        conn: Optional[Connection]
            An asyncpg connection. If passed, this method will update the settings for the guild.

        Returns
        -------
        RoleMode
            The selected role mode

        Raises
        ------
        SilentCommandError
            The user did not respond.
        """
        view = RoleModeView(ctx)
        view.message = await ctx.send(view=view)
        await view.wait()
        if not view.value:
            raise SilentCommandError()

        if conn:
            await conn.execute('UPDATE guilds SET muted_role_mode = $1 WHERE guild_id = $2', view.value.value, ctx.guild.id)

        return view.value

    async def _mute_member(self, ctx: DuckContext, member: discord.Member, time: UserFriendlyTime):
        guild = ctx.guild
        async with self.bot.safe_connection() as connection:
            reason = safe_reason(ctx.author, time.arg)  # type: ignore

            # We need to manage roles now. Who TF mutes someone for over 28 days???? Like I dont understand...
            async with ctx.typing():
                muted_role = await self._get_muted_role(guild, conn=connection)
                roles_to_keep = [role for role in member.roles if not role.is_assignable()]

                # We need to get this before editing the member, because the member .roles attribute
                # will get updated after the edit. (singleton moment)
                roles_to_restore = [role.id for role in member.roles]

                await member.edit(roles=[*roles_to_keep, muted_role], reason=reason)

                await self.bot.create_timer(
                    time.dt,
                    'mute',
                    member.id,
                    guild.id,
                    roles=roles_to_restore,
                    done_message=f"Expiring mute set by {ctx.author} (ID: {ctx.author.id}) on {time.dt.strftime('%A, %B %#d %Y at %I:%M %p %Z')}",
                )

                query: str = """
                INSERT INTO guilds (guild_id, mutes) VALUES ($2, ARRAY[$1]::BIGINT[])
                ON CONFLICT (guild_id) DO UPDATE
                    SET mutes = ARRAY(SELECT DISTINCT * FROM UNNEST(guilds.mutes || excluded.mutes))
                """

                await connection.execute(query, member.id, guild.id)

    @command(name='selfmute', invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def selfmute(self, ctx: DuckContext, *, duration: ShortTime):
        """Temporarily mute yourself for up to 24 hours.

        Parameters
        ----------
        duration: str
            The time for which you wish to be muted (between 5m and 24h). Must be a short time, e.g. 5m, 1h, 1h30m.
        """

        await self._get_muted_role(ctx.guild)

        created_at = ctx.message.created_at
        if duration.dt > (created_at + datetime.timedelta(days=1)):
            return await ctx.send('Duration is too long. Must be at most 24 hours.')

        if duration.dt < (created_at + datetime.timedelta(minutes=5)):
            return await ctx.send('Duration is too short. Must be at least 5 minutes.')

        if not await ctx.confirm(
            f'Are you sure you want to be muted until {discord.utils.format_dt(duration.dt, style="R")}'
        ):
            return await ctx.send('Cancelled.')

        class MockUFT(NamedTuple):
            dt: datetime.datetime
            arg: str

        await ctx.send('Ok, be sure not to bother anyone about it.')

        await self._mute_member(ctx, ctx.author, MockUFT(dt=duration.dt, arg=f'Self-muted until {duration.dt}'))  # type: ignore

    @group(name='tempmute', aliases=['tm', 'mute'], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def tempmute(
        self, ctx: DuckContext, member: VerifiedMember, *, time: UserFriendlyTime
    ) -> Optional[discord.Message]:
        """Temporarily mute a member from speaking or connecting to channel(s) in the Discord. This is done through
        a role, which can be configured through the `db.muterole` command.

        Parameters
        ----------
        member: discord.Member
            The member to mute.
        time: str
            The total time and reason for the mute. For example, `1h`, `1h for being a jerk!`, `tomorrow at 2pm for being a jerk!`.
        """
        if not isinstance(time, UserFriendlyTime):
            return  # yay type hints!

        if ctx.invoked_subcommand:
            return

        await self._mute_member(ctx, member, time)

        return await ctx.send(f"{mdr(member, escape=True)} has been muted for {human_timedelta(time.dt)}")

    @tempmute.command(name='remove')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def tempmute_remove(self, ctx: DuckContext, member: discord.Member) -> Optional[discord.Message]:
        """Unmute a member that was muted.

        Parameters
        ----------
        member: discord.Member
            The member to unmute.
        """
        # Fuck me. This whole command. So bad.
        guild = ctx.guild

        async with self.bot.safe_connection() as conn:
            await conn.execute('UPDATE guilds SET mutes = ARRAY_REMOVE(mutes, $1) WHERE guild_id = $2', member.id, guild.id)
            # Let's find the timer(s)

            record = await conn.fetchrow(
                """
                DELETE FROM timers WHERE event = 'mute'
                
                    AND (extra->'args'->0)::bigint = $1 
                        -- arg at position 0 is the member id
                        
                    AND (extra->'args'->1)::bigint = $2
                        -- arg at position 1 is the guild id

                RETURNING *;
                """,
                member.id,
                guild.id,
            )

            if not record:
                raise MemberNotMuted(member)

            timer = Timer(record=record)

            async def message_sender(message: str, *fmt_args: str):
                await ctx.send(message % fmt_args)

            await self.expire_mute(
                *timer.args,
                **timer.kwargs,
                info_message_hook=message_sender,
                user_facing_message=True,
                conn=conn,
            )

            return await ctx.send(f"{mdr(member, escape=True)} has been unmuted.")

    @command(name='unmute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute(self, ctx: DuckContext, member: discord.Member) -> Optional[discord.Message]:
        """Unmute a member that was muted.

        Parameters
        ----------
        member: discord.Member
            The member to unmute.
        """
        return await ctx.invoke(self.tempmute_remove, member)

    @commands.Cog.listener('on_member_update')
    async def cache_validation(self, before: discord.Member, after: discord.Member) -> None:
        """A listener that updates the internal cache of muted members.

        This even gets called when the member's roles get updated, removing it from the DB.

        Parameters
        ----------
        before: discord.Member
            The member before the update.
        after: discord.Member
            The member after the update.
        """
        await asyncio.sleep(1)
        guild = before.guild
        data = await self.bot.pool.fetchrow("SELECT muted_role_id, mutes FROM guilds WHERE guild_id = $1;", guild.id)

        if not data:
            return

        role_id: int = data['muted_role_id']
        mutes: list[int] = data['mutes']

        if after.id not in mutes:
            # The user was not muted through DuckBot.
            return

        if not before.get_role(role_id) or after.get_role(role_id):
            # The muted role was not removed from the user.
            return

        query = """
            DELETE FROM timers WHERE event = 'mute'
            
                AND (extra->'args'->0)::bigint = $1 
                    -- arg at position 0 is the member id
                    
                AND (extra->'args'->1)::bigint = $2;
                    -- arg at position 1 is the guild id
        """
        await self.bot.pool.execute(query, after.id, guild.id)
        await self.bot.pool.execute(
            'UPDATE guilds SET mutes = array_remove(mutes, $1) WHERE guild_id = $2;', after.id, guild.id
        )
        # TODO: Maybe hook into a potential mod-log in the future to inform about this.

    @commands.Cog.listener('on_mute_timer_complete')
    async def mute_dispatcher(self, member_id: int, guild_id: int, *, roles: List[int], done_message: str) -> None:
        """
        A mute dispatcher that listens for when a timer expires. Once it does, it restores the member's roles
        back to what they were before the mute.

        Parameters
        ----------
        member_id: int
            The member ID.
        guild_id: int
            The guild ID.
        roles: List[int]
            A list of role IDS to restore to the member, because the timer system
            removes all roles that the user previously had.
        done_message: str
            The message that was given when the timer was scheduled.
            This contains information about who created this timer and when.
        """

        async def debug_logger(message: str, *fmt_args: str):
            log.debug(message, *fmt_args)

        async with self.bot.safe_connection() as conn:
            await self.expire_mute(
                member_id, guild_id, roles=roles, done_message=done_message, info_message_hook=debug_logger, conn=conn
            )

    async def expire_mute(
        self,
        member_id: int,
        guild_id: int,
        *,
        roles: List[int],
        done_message: str,
        info_message_hook: Callable[..., Awaitable[None]],  # Should be a callable protocol but this'll do for here.
        user_facing_message: bool = False,
        conn: Connection,
    ) -> None:
        if not user_facing_message:
            await info_message_hook(f'Mute timer for {member_id} in {guild_id} has expired. Restoring {len(roles)} roles.')

        mute_role_id: int | None = await conn.fetchval(
            'UPDATE guilds SET mutes = array_remove(mutes, $1) WHERE guild_id = $2 RETURNING muted_role_id',
            member_id,
            guild_id,
        )

        if not mute_role_id:
            if user_facing_message:
                raise NoMutedRole()
            else:
                await info_message_hook('Ignoring mute timer for guild %s, it has no muterole set anymore.', guild_id)
            return

        guild = self.bot.get_guild(guild_id)

        if guild is None:
            if not user_facing_message:
                return await info_message_hook('Ignoring mute timer for guild %s, it no longer exists.', guild_id)
            return

        if not guild.me.guild_permissions.manage_roles:
            return await info_message_hook(
                'Ignoring mute timer for guild %s, the bot no longer has the Manage Roles permission.', guild_id
            )

        try:
            member = guild.get_member(member_id) or await guild.fetch_member(member_id)
        except (discord.NotFound, discord.HTTPException):
            return await info_message_hook(
                'Ignoring mute timer for member %s, they are not in this server anymore.', member_id
            )

        roles_to_keep: list[discord.Role] = []

        for role_id in roles:
            if role_id == mute_role_id:
                continue

            role = guild.get_role(role_id)

            if role and (role.is_assignable() or member.get_role(role_id)):
                roles_to_keep.append(role)

        if set(r.id for r in member.roles) != set(r.id for r in roles_to_keep):
            try:
                await member.edit(roles=roles_to_keep, reason=done_message)
            except discord.HTTPException:
                await info_message_hook('Failed to restore roles for member %s', member)

    @group(name='mute-role', aliases=['muterole'], invoke_without_command=False)
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True, moderate_members=True)
    async def muterole(self, ctx: DuckContext):
        """Base command for managing mute roles. Run without a sub-command
        to view the current muted role configuration.
        """
        if ctx.invoked_subcommand:
            return

        async with ctx.typing():
            query: str = "SELECT muted_role_id, muted_role_mode FROM guilds WHERE guild_id = $1;"
            settings = await self.bot.pool.fetchrow(query, ctx.guild.id)

            if not settings or not settings['muted_role_id']:
                await ctx.send('This guild has no muted role set up.')
                return

            role_id: int = settings['muted_role_id']
            role = ctx.guild.get_role(role_id)

            if not role:
                await ctx.send(f'Previous mute role (ID: {role_id}) was not found. (it was probably deleted...)')
                return

            role_mode = RoleMode(settings['muted_role_mode'])

            embed = discord.Embed()
            embed.set_author(url=ctx.guild.icon.url if ctx.guild.icon else None, name=f'Mute Role settings for {ctx.guild}')
            embed.add_field(name='Role:', value=role.mention)

            toggles = ctx.bot.constants.TOGGLES
            cannot_view_channels = role_mode is RoleMode.no_view_channel

            message = f"{toggles[True]}**Users cannot send messages, connect, or speak.**\n"
            if cannot_view_channels:
                message += f"{toggles[True]}** Users cannot view channel(s).**"
            else:
                message += f"{toggles[False]}** Users __can__ view channel(s).**"

            embed.add_field(name='Role Permissions Configuration:', value=message, inline=False)

            channels_with_improper_permissions = [
                (channel, missing)
                for channel in ctx.guild.channels
                if (missing := self._get_missing_permissions_for(role, channel, role_mode))
            ]

            if channels_with_improper_permissions:
                missing = itertools.chain.from_iterable(pair[1] for pair in channels_with_improper_permissions)
                counter = collections.Counter(missing)

                fmt: list[str] = []

                for permission, amount in counter.items():
                    fmt.append(f'{amount} channel(s) have __{permission.replace("_", " ").title()}__ enabled.')

                embed.add_field(
                    name=f'\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {len(channels_with_improper_permissions)} channel(s) with incorrect permissions!',
                    value='\n'.join(fmt) + '\n**Click the button below for a full list.**\n**Use `db.muterole fix` to fix**',
                )

                source = WarningsPageSource(entries=channels_with_improper_permissions)
                view = ShowWarnings(page_source=source, context=ctx)
            else:
                view = None

            await ctx.send(embed=embed, view=view)

    @muterole.command(name='create')
    async def muterole_create(self, ctx: DuckContext):
        """Creates a mute role named Muted and sets up permissions for you.
        The bot requires manage roles permission in all channel(s).
        """
        query: str = "SELECT muted_role_id, muted_role_mode, mutes FROM guilds WHERE guild_id = $1;"
        settings = await self.bot.pool.fetchrow(query, ctx.guild.id)

        old_role: Optional[discord.Role] = None
        should_update: bool = False
        muted_members = []

        if settings and settings['muted_role_id']:
            role_id: int = settings['muted_role_id']
            old_role = ctx.guild.get_role(role_id)
            muted_members: list[int] = settings['mutes']

            if old_role:
                if not await ctx.confirm(f'Role is already configured ({old_role.name}). Overwrite it?'):
                    await ctx.send('Cancelled.')
                    return
                await ctx.send(F"Alright, overwriting the old muted role ({old_role.name})")

                if muted_members:
                    should_update = await ctx.confirm(
                        f'There are {len(settings["mutes"])} muted users, would you like to also give them the new role?',
                        labels=('yes', 'no'),
                        silent_on_timeout=True,
                    )

        # Break out of typing while we wait for a user's response.
        role_mode = await self._prompt_role_mode(ctx)

        await ctx.send('Please wait while I create the role and update permissions... This can take awhile.')

        async with ctx.typing():
            role, success, partial, skipped, failed = await self._create_muted_role(ctx.guild, role_mode=role_mode)

            query: str = """
            INSERT INTO guilds (guild_id, muted_role_id, muted_role_mode) VALUES ($1, $2, $3)
            ON CONFLICT (guild_id) DO UPDATE
                SET muted_role_id = $2, muted_role_mode = $3
            """
            await self.bot.pool.execute(query, ctx.guild.id, role.id, role_mode.value)

            total = success + partial + skipped + failed
            message = (
                f"**Successfully created a muted role: {role.mention}**"
                f"\n**Attempted to set permissions for __{total}__ channel(s):\n**"
                f"\nSuccessfully set permissions for __{success + partial} channel(s)__. Of which I set full permissions for {success} channel(s), and partial permissions for {partial} channel(s)."
                f"\nFailed to set permissions for {skipped+failed} channel(s). Of which I {skipped} channel(s) (missing permissions), "
                f"and failed to set permissions for {failed} channel(s) (discord error)."
            )

            if old_role and should_update:
                failed = 0
                success = 0
                skipped = 0

                for member_id in muted_members:
                    member = await self.bot.get_or_fetch_member(ctx.guild, member_id)
                    if not member:
                        skipped += 1
                        continue
                    role_ids = {role.id for role in member.roles}
                    role_ids.discard(old_role.id)
                    role_ids.add(role.id)
                    try:
                        await member.edit(
                            roles=[discord.Object(id=r_id) for r_id in role_ids],
                            reason=safe_reason(ctx.author, 'Auto-update (new mute role)'),
                        )
                        success += 1
                    except discord.HTTPException:
                        failed += 1
                message += (
                    f"\n\n\n**Updated muted members with the new role:**"
                    f"\nSuccess: {success}, Failed: {failed}, Skipped (not in server): {skipped}"
                )

            await ctx.send(message, allowed_mentions=discord.AllowedMentions.none())

    @muterole.command(name='sync', aliases=['fix'])
    async def muterole_fix(self, ctx: DuckContext):
        """Updates permissions for all channel(s), to correct for improper permissions."""

        async with self.bot.safe_connection() as conn:
            role = await self._get_muted_role(ctx.guild, conn=conn)

            role_mode = await self._prompt_role_mode(ctx, conn=conn)

            async with ctx.typing():
                success, partial, skipped, failed = await self._update_role_permissions(role=role, role_mode=role_mode)

                total = success + partial + skipped + failed
                await ctx.send(
                    f"\n**Attempted to set permissions for __{total}__ channel(s):\n**"
                    f"\nSuccessfully set permissions for __{success + partial} channel(s)__. Of which I set full permissions for {success} channel(s), and partial permissions for {partial} channel(s)."
                    f"\nFailed to set permissions for {skipped+failed} channel(s). Of which I {skipped} channel(s) (missing permissions), "
                    f"and failed to set permissions for {failed} channel(s) (discord error).",
                )

    @muterole.command(name='unbind')
    async def muterole_unbind(self, ctx: DuckContext):
        """Unbinds the muted role and cancels all mute timers."""
        await self._get_muted_role(ctx.guild)  # Raises NoMutedRole if not found.

        async with self.bot.safe_connection() as conn:
            timers = await conn.fetch(
                """
                SELECT * FROM timers WHERE event = 'mute'
                                
                    AND (extra->'args'->1)::bigint = $1;
                        -- arg at position 1 is the guild id
                """,
                ctx.guild.id,
            )

            spec = plural(len(timers))
            if not await ctx.confirm(
                "**Are you sure you want to unbind the muted role?**"
                "\nThis will cancel all timers for currently-muted members, but it will **not** remove the muted role from them. "
                "\nIt will not delete the role either, or change its permissions in the channels."
                f"\n:warning: this cannot be undone! (There {spec:is|are} {len(timers)} active {spec:timer})",
                timeout=60,
                silent_on_timeout=True,
            ):
                return await ctx.send('Cancelled.')

            await conn.execute(
                """
                DELETE FROM timers WHERE event = 'mute'

                AND (extra->'args'->1)::bigint = $1;
                    -- arg at position 1 is the guild id
                
                UPDATE guilds SET muted_role_id = NULL, muted = '{}'::BIGINT[] WHERE guild_id = $1;
                """,
                ctx.guild.id,
            )

            await ctx.send('Ok, this server no longer has a muted role.')

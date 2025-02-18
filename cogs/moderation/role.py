from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import DuckBot
from utils import (
    DeleteButton,
    DuckCog,
    DuckContext,
    VerifiedRole,
    View,
    constants,
    group,
    plural,
    ensure_chunked,
)
from utils.checks import hybrid_permissions_check
from utils.types import constants

"""
op-id
author
target-users
roles-to-add
cancellation-view
"""


class TaskCancelView(View):
    def __init__(self, owner: discord.abc.User, bot: DuckBot):
        super().__init__(bot=bot, author=owner, bypass_permissions=discord.Permissions(manage_roles=True))
        self.job: Optional[RoleActionJob] = None
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cancel(interaction.user, interaction)

    def stop(self) -> None:
        if self.job:
            self.job.active = False
        return super().stop()

    async def cancel(self, user: discord.abc.User, interaction: Optional[discord.Interaction] = None):
        self.stop()
        if interaction:
            await interaction.response.edit_message(content=f"Role job cancelled by {user}", view=None)
        elif self.message:
            await self.message.edit(
                content=f"Role job cancelled by {user.mention}",
                view=None,
                allowed_mentions=discord.AllowedMentions(users=True),
            )

    async def cancelled(self):
        if self.message and not self.is_finished():
            await self.message.edit(view=None, content="Role job cancelled")
        self.stop()

    async def done(self):
        self.stop()
        if self.message:
            if job := self.job:
                if len(job.roles) == 1:
                    roles = job.roles[0].name
                else:
                    roles = f"{len(job.roles)} roles"
                if len(job.targets) == 1:
                    target = job.targets[0].display_name
                else:
                    target = format(plural(len(job.targets) - job.failures), 'user')
                message = f"{'Removed' if job.remove else 'Added'} {roles} {'from' if job.remove else 'to'} {target}"
                if job.failures:
                    message += f"\n-# Failed to assign roles to {plural(job.failures):user}."
            else:
                message = "Finished role task."
            await self.message.edit(
                content=message,
                view=None,
                allowed_mentions=discord.AllowedMentions(users=True),
            )

    async def errored(self, error: Exception | str):
        self.stop()
        if self.message:
            await self.message.edit(
                content=f"Job assignment unexpectedly failed.\n-#{error}. Our developers have been notified.", view=None
            )
        if self.bot and isinstance(error, Exception):
            await self.bot.exceptions.add_error(error=error, display=f"bulk role task")


@dataclass(slots=True)
class RoleActionJob:
    author: discord.abc.User
    targets: Sequence[discord.Member]
    roles: Sequence[discord.Role]
    view: TaskCancelView
    active: bool = True
    remove: bool = False
    failures: int = 0


class Roles(DuckCog):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tasks: dict[int, tasks.Loop] = {}
        self.jobs: defaultdict[int, deque[RoleActionJob]] = defaultdict(deque)

    async def task(self, guild_id: int):
        try:
            jobs = self.jobs.get(guild_id)
            if not jobs:
                return self.tasks[guild_id].stop()

            job = jobs.popleft()
            for member in job.targets:
                if not job.active:
                    await job.view.cancelled()
                    break

                try:
                    reason = f"Role task initiated by {job.author} ({job.author.id})"
                    if all((role not in member.roles) == job.remove for role in job.roles):
                        return
                    await (member.remove_roles if job.remove else member.add_roles)(*job.roles, reason=reason)
                except discord.NotFound as error:
                    if error.code == 10011:
                        await job.view.errored("Tried assigning a role that does not exists.")
                        break
                    elif error.code == 10007:
                        job.failures += 1
                except discord.Forbidden:
                    await job.view.errored("Could not add a role due to missing permissions, or role hierarchy.")
                    break
                except Exception as error:
                    await job.view.errored(error)
                    break
            else:
                await job.view.done()
        except Exception as e:
            await self.bot.exceptions.add_error(error=e, display=f"Bulk role task for guild {guild_id}")

    def ensure_task(self, guild_id: int):
        try:
            task = self.tasks[guild_id]
            if not task.is_running():
                task.start(guild_id)
        except KeyError:
            task = tasks.loop()(self.task)
            task.start(guild_id)
            self.tasks[guild_id] = task

    async def enqueue_role_job(
        self,
        ctx: DuckContext,
        targets: Sequence[discord.Member],
        roles: Sequence[discord.Role],
        remove: bool = False,
    ):
        guild_id = ctx.guild.id
        view = TaskCancelView(owner=ctx.author, bot=self.bot)
        job = RoleActionJob(author=ctx.author, targets=targets, roles=roles, view=view, remove=remove)
        view.job = job
        self.jobs[guild_id].append(job)

        if len(roles) == 1:
            roles_text = roles[0].name
        else:
            roles_text = f"{len(roles)} roles"

        if len(job.targets) == 1:
            target = targets[0].display_name
        else:
            target = format(plural(len(targets)), 'user')

        message = f"{'Removing' if job.remove else 'Adding'} {roles_text} {'from' if job.remove else 'to'} {target}"

        view.message = await ctx.send(message, view=view)
        self.ensure_task(guild_id)

    @group(name='role', hybrid=True)
    @hybrid_permissions_check(manage_roles=True, bot_manage_roles=True)
    async def role(self, ctx: DuckContext, user: discord.Member, role: VerifiedRole):
        """Commands to manage roles."""
        if not ctx.invoked_subcommand:
            await self.enqueue_role_job(ctx, [user], [role])

    @role.group(name='add', fallback='user')
    async def role_add(self, ctx: DuckContext, user: discord.Member, role: VerifiedRole):
        """Add a role to a user.

        Parameters
        ----------
        user: discord.Member
            The user to target.
        role: discord.Role
            The role to add to user.
        """
        await self.enqueue_role_job(ctx, [user], [role])

    @role_add.command(name='all')
    @ensure_chunked()
    async def role_add_all(self, ctx: DuckContext, role: VerifiedRole):
        """Adds a role to all users.

        Parameters
        ----------
        role: discord.Role
            The role to add to all users.
        """
        await self.enqueue_role_job(ctx, ctx.guild.members, [role])

    @role_add.command(name='humans')
    async def role_add_humans(self, ctx: DuckContext, role: VerifiedRole):
        """Adds a role to all non-bot users.

        Parameters
        ----------
        role: discord.Role
            The role to add to all non-bots.
        """
        await self.enqueue_role_job(ctx, [m for m in ctx.guild.members if not m.bot], [role])

    @role_add.command(name='bots')
    async def role_add_bots(self, ctx: DuckContext, role: VerifiedRole):
        """Adds a role to all bots.

        Parameters
        ----------
        role: discord.Role
            The role to add to all bots.
        """
        await self.enqueue_role_job(ctx, [m for m in ctx.guild.members if m.bot], [role])

    @role_add.command(name='in')
    @app_commands.rename(to_add='to-add')
    async def role_add_in(self, ctx: DuckContext, base: discord.Role, to_add: VerifiedRole):
        """Adds a role to all users with <base> role.

        Parameters
        ----------
        base: discord.Role
            The role from which to grab all users.
        to_add: discord.Role
            The role to add to all users with <base>.
        """
        await self.enqueue_role_job(ctx, base.members, [to_add])

    @role.command(
        name='addmany',
        aliases=['multi-give'],
        ignore_extra=False,
        ignored_exceptions=(commands.TooManyArguments,),
    )
    async def role_addmany(
        self,
        ctx: DuckContext,
        users: commands.Greedy[discord.Member],
        roles: commands.Greedy[discord.Role],
    ):
        """Adds all specified <roles> to all specified <users>.

        Parameters
        ----------
        users: Greedy[discord.Member]
            All usersnames/ids/pings to give <roles> to, separated by a space.
        users: Greedy[discord.Role]
            All role names/ids/pings to give to <users>, separated by a space.
        """
        await self.enqueue_role_job(ctx, users, roles)

    @role_addmany.error
    async def role_addmany_eh(self, ctx: DuckContext, error: Exception):
        if isinstance(error, commands.TooManyArguments):
            await ctx.send("Some users or roles given were not recognised.")

    @role.command(name='clear')
    async def role_clear(self, ctx, user: discord.Member):
        """Removes all roles from a user.

        Parameters
        ----------
        user: discord.Member
            The user to remove all roles from.
        """
        await self.enqueue_role_job(ctx, [user], [r for r in user.roles if r.is_assignable()], remove=True)

    @role.group(name='remove', fallback='user')
    async def role_remove(self, ctx: DuckContext, user: discord.Member, role: VerifiedRole):
        """Removes a role from a user.

        Parameters
        ----------
        user: discord.Member
            The user to target.
        role: discord.Role
            The role to remove from user.
        """
        await self.enqueue_role_job(ctx, [user], [role], remove=True)

    @role_remove.command(name='all')
    async def role_remove_all(self, ctx: DuckContext, role: VerifiedRole):
        """Removes a role from all users.

        Parameters
        ----------
        role: discord.Role
            The role to remove from all users.
        """
        await self.enqueue_role_job(ctx, ctx.guild.members, [role], remove=True)

    @role_remove.command(name='humans')
    async def role_remove_humans(self, ctx: DuckContext, role: VerifiedRole):
        """Removes a role from all non-bot users.

        Parameters
        ----------
        role: discord.Role
            The role to remove from all non-bots.
        """
        await self.enqueue_role_job(ctx, [m for m in ctx.guild.members if not m.bot], [role], remove=True)

    @role_remove.command(name='bots')
    async def role_remove_bots(self, ctx: DuckContext, role: VerifiedRole):
        """Removes a role from all bots.

        Parameters
        ----------
        role: discord.Role
            The role to remove from all bots.
        """
        await self.enqueue_role_job(ctx, [m for m in ctx.guild.members if m.bot], [role], remove=True)

    @role_remove.command(name='in')
    @app_commands.rename(to_remove='to-remove')
    async def role_remove_in(self, ctx: DuckContext, base: discord.Role, to_remove: VerifiedRole):
        """Removes a role from all users with <base> role.

        Parameters
        ----------
        base: discord.Role
            The role from which to grab all users.
        to_remove: discord.Role
            The role to remove from all users with <base>.
        """
        await self.enqueue_role_job(ctx, base.members, [to_remove], remove=True)

    @role.command(name='info')
    async def role_info(self, ctx: DuckContext, role: discord.Role):
        """Provides information on a role.

        Parameters
        ----------
        role: discord.Role
            The role which information you need.
        """
        if not ctx.guild.chunked:
            await ctx.typing()
            await ctx.guild.chunk()

        embed = discord.Embed(
            color=role.color,
            title=f"Role Information",
            description=(
                f"**`Name:`** {role.mention}"
                f"\n**`Members:`** {len(role.members)}"
                f"\n**`Color:`** {role.color}"
                f"\n**`Created:`** {discord.utils.format_dt(role.created_at)}"
                f"\n**`ID:`** {role.id}"
                f"\n{f'**`Role Icon:`** {role.unicode_emoji}' if role.unicode_emoji else ''}"
            ),
        )
        names = sorted([k.replace('guild', 'server').replace('_', ' ').title() for k, v in role.permissions if v])
        embed.add_field(name=f"{constants.STORE_TAG} Permissions", value='`' + ('`, `'.join(names)) + '`')

        if role.icon:
            embed.set_thumbnail(url=role.icon.url)

        await ctx.send(embed=embed)

    @role.command(name='diagnose')
    @commands.max_concurrency(1, commands.BucketType.user)
    async def role_diagnose(self, ctx: DuckContext, role: discord.Role):
        """Provides diagnostics on a role, useful if a role failed to be added.

        Parameters
        ----------
        role: discord.Role
            The role to diagnose.
        """
        if not isinstance(ctx.author, discord.Member) or not isinstance(ctx.me, discord.Member):
            await ctx.send("Could not diagnose. Please try again later", ephemeral=True)
            if ctx.guild and not ctx.guild.chunked:
                await ctx.guild.chunk()
            return

        assignable = True
        fail_reason = ""
        if role.is_bot_managed():
            assignable = False
            fail_reason = "Role is managed by a bot."
        elif role.is_integration():
            assignable = False
            fail_reason = "Role is managed by an integration."
        elif role.is_premium_subscriber():
            assignable = False
            fail_reason = "Role is the server's premium (booster) role."

        text = [
            f"Specified role: {role.mention} (position **{role.position}**)",
            f"Your top role: {ctx.author.top_role.mention} (position **{ctx.author.top_role.position}**)",
            f"My top role: {ctx.me.top_role.mention} (position **{ctx.me.top_role.position}**)",
            ctx.tick(perms := ctx.permissions.manage_roles, "Manage roles for you."),
            ctx.tick(
                assignable and perms and (role < ctx.author.top_role or ctx.author.id == ctx.guild.owner_id),
                "You can assign.",
            ),
        ]
        if not assignable:
            text.append(f"-# {fail_reason}")
        elif role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            text.append(f"-# Role is higher than your top role.")

        text.append(ctx.tick(perms := ctx.bot_permissions.manage_roles, "Manage roles for me."))
        text.append(ctx.tick(role.is_assignable(), "I can assign."))
        if not assignable:
            text.append(f"-# {fail_reason}")
        elif not role.is_assignable():
            text.append(f"-# Role is higher than my top role.")

        embed = discord.Embed(color=self.bot.colour, title="Role diagnostics result", description="\n".join(text))
        await DeleteButton.send_to(ctx, author=ctx.author, embed=embed)

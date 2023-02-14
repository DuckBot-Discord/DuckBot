from __future__ import annotations
from datetime import datetime, timedelta

from typing import TYPE_CHECKING, Any, List, NamedTuple, Optional, SupportsInt

import discord
from discord.ext import commands, menus
from discord import AuditLogAction as AA, AuditLogDiff, ChannelType
from discord.utils import MISSING

from utils import command, DuckCog, DuckContext, mdr, human_join, paginators, human_timedelta, View
from utils.types import constants

if TYPE_CHECKING:
    from discord.audit_logs import TargetType
    from bot import DuckBot


class MockInteraction:
    class response:
        @classmethod
        def is_done(cls):
            return True


class LoadingView(View):
    @discord.ui.button(disabled=True, label='loading results... please wait.', style=discord.ButtonStyle.green)
    async def mock(self, interaction: discord.Interaction[DuckBot], button: discord.ui.Button):
        ...


class _DiffWrapper(AuditLogDiff):
    def __init__(self, ald: AuditLogDiff) -> None:
        self.__dict__ = ald.__dict__
        super().__init__()

    def __bool__(self):
        return all(self.__dict__.values())

    def __getattr__(self, item: str) -> Any:
        return MISSING


class ThreadDiff(_DiffWrapper):
    if TYPE_CHECKING:
        name: Optional[str]
        type: Optional[ChannelType]
        archived: Optional[bool]
        auto_archive_duration: Optional[int]
        slowmode_delay: Optional[int]
        applied_tags: Optional[List[SupportsInt]]
        flags: Optional[int]


def ts(dt: datetime, *, rel: bool = False) -> str:
    """Formats a datetime object into a discord-styled timestamp format.

    Parameters
    ----------
    dt: datetime
        The datetime to format.
    rel: bool
        Wether to include the relative dt too.

    Returns
    -------
    str
        The formatted string.
    """
    return f"{discord.utils.format_dt(dt)}" + (f" ({discord.utils.format_dt(dt, 'R')})" if rel else "")


def fmt_u(ent: TargetType, user: discord.User) -> str:
    if not ent or isinstance(ent, discord.Object):
        return '`Unknown`' if not ent else f'`Unknown (id={ent.id})`'
    bot = ''
    if isinstance(ent, discord.VoiceChannel):
        sep = constants.VOICE_CHANNEL
    elif isinstance(ent, discord.CategoryChannel):
        sep = constants.CATEGORY_CHANNEL
    elif isinstance(ent, discord.ForumChannel):
        sep = constants.FORUM_CHANNEL
    elif isinstance(ent, discord.abc.GuildChannel):
        sep = constants.TEXT_CHANNEL
    elif isinstance(ent, discord.Thread):
        sep = constants.TEXT_CHANNEL_WITH_THREAD
    elif isinstance(ent, (discord.Member, discord.User)):
        sep = '@'
        bot = f"{constants.BOT} " if ent.bot else ""
    elif isinstance(ent, discord.Role):
        sep = constants.ROLES_ICON
    else:
        sep = ''
    if ent == user:
        return f'{bot}__{sep}{mdr(ent, escape=True)}__'
    return f'{bot}{sep}{mdr(ent, escape=True)}'


class Field(NamedTuple):
    """Represents an embed's field.

    Parameters
    ----------
    name: str
        The field's name.
    value: str
        The field's value.
    inline: bool
        Wether this field is inlined.
    """

    name: str
    value: str
    inline: bool = False


class FieldsPageSource(menus.ListPageSource):
    """A ListPageSource that takes a list of Field to make an embed out of."""

    def __init__(self, entries: List[Field], *, targeted_user: discord.abc.User):
        """Initializes the class

        Parameters
        ----------
        entries: List[Field]
            All the fields to be formatted.
        author: discord.abc.User
            The user who requested this menu.
        """
        super().__init__(entries, per_page=5)
        self.targeted_user = targeted_user

    async def format_page(self, menu: paginators.ViewMenuPages, entries: List[Field]) -> discord.Embed:
        """Formats this page.

        Parameters
        ----------
        menu: paginators.ViewMenuPages
            The menu object this page source was passed to.
        entries: List[Field]
            The list of fields.

        Returns
        ------
        discord.Embed
            The formatted embed object.
        """
        embed = discord.Embed(color=discord.Color(0x000001))
        embed.set_author(name=f'Audit logs for @{self.targeted_user}', icon_url=self.targeted_user.display_avatar.url)
        for idx, field in enumerate(entries, start=(menu.current_page * self.per_page) + 1):
            embed.add_field(
                name=f"`{idx:>3}.` {field.name}",
                value=field.value + ("\n\u200b" if idx % len(entries) else ""),
                inline=field.inline,
            )
        embed.set_footer(text=f"page {menu.current_page + 1} / {self.get_max_pages()} ({len(self.entries)} entries)")
        return embed


class AuditLogViewer(DuckCog):
    """Audit log viewer."""

    @command(aliases=['al', 'audit', 'audinfo'])
    @commands.has_permissions(view_audit_log=True)
    @commands.bot_has_guild_permissions(view_audit_log=True)
    @commands.max_concurrency(1, commands.BucketType.member)
    async def auditlogs(self, ctx: DuckContext, *, user: discord.User):
        """Shows audit logs for the specified user.

        (audit logs only last up to 45 days... thanks discord.)
        """
        source = None
        pages = None

        info_embed = discord.Embed(
            title='Icon Legend:',
            description=(
                '\N{WOMANS BOOTS} -> Kick'
                '\n\N{POLICE CARS REVOLVING LIGHT} -> Ban'
                '\n\N{PAPERCLIP} -> Unban'
                '\n\N{HEAVY MINUS SIGN} -> Remove Roles'
                '\n\N{HEAVY PLUS SIGN} -> Add Roles'
                '\n\N{ROBOT FACE} -> Add Bot'
                '\n\N{WASTEBASKET} -> Prune Members'
                '\n\N{STOPWATCH} -> Edit Member Timeout'
                f'\n{constants.EDIT_NICKNAME} -> Edit Member Nickname'
                f'\n{constants.TEXT_CHANNEL_WITH_THREAD} -> Edit Thread'
            ),
            color=discord.Color(0x000001),
        )
        info_embed.set_author(name=f'Audit logs for @{user}', icon_url=user.display_avatar.url)
        info_embed.set_footer(text='Click any button to resume')

        fields: List[Field] = []
        typer = ctx.typing()
        async with typer:
            async for entry in ctx.guild.audit_logs(limit=None):
                if not ((entry.target and entry.target.id == user.id) or (entry.user and entry.user.id == user.id)):
                    continue

                target = fmt_u(entry.target, user)
                moderator = fmt_u(entry.user, user)
                fmt_date: str = ts(entry.created_at, rel=True)
                action = entry.action

                if action is AA.kick:
                    fields.append(
                        Field(
                            name=f'\N{WOMANS BOOTS} {moderator} kicked {target}',
                            value=f'`  At` {fmt_date}\n` For` `{mdr(entry.reason)}`',
                        )
                    )

                elif action is AA.ban:
                    fields.append(
                        Field(
                            name=f"\N{POLICE CARS REVOLVING LIGHT} {moderator} banned {target}",
                            value=f"`  At` {fmt_date}\n` For` `{mdr(entry.reason)}`",
                        )
                    )

                elif action is AA.unban:
                    fields.append(
                        Field(
                            name=f"\N{PAPERCLIP} {moderator} unbanned {target}",
                            value=f"`  At` {fmt_date}\n` For` `{mdr(entry.reason)}`",
                        )
                    )

                elif action is AA.member_role_update:
                    removed = list(map(lambda r: r.mention, set(entry.before.roles) - set(entry.after.roles)))
                    added = list(map(lambda r: r.mention, set(entry.after.roles) - set(entry.before.roles)))
                    extra = f"\n` For` `{mdr(entry.reason)}`" if entry.reason else ''
                    if removed:
                        fmt = human_join(
                            removed[0:10] + ([f'{len(removed[10:])} more...'] if removed[10:] else []), final='and'
                        )
                        fields.append(
                            Field(
                                name=f'\N{HEAVY MINUS SIGN} {moderator} removed roles from {target}',
                                value=f"`    ` {fmt}\n`  At` {fmt_date}{extra}",
                            )
                        )
                    if added:
                        fmt = human_join(added[0:10] + ([f'{len(added[10:])} more...'] if added[10:] else []), final='and')
                        fields.append(
                            Field(
                                name=f"\N{HEAVY PLUS SIGN} {moderator} added roles to {target}",
                                value=f"`    ` {fmt}\n`  At` {fmt_date}{extra}",
                            )
                        )

                elif action is AA.bot_add:
                    fields.append(Field(name=f'\N{ROBOT FACE} {moderator} added {target}', value=f"`  At` {fmt_date}"))

                elif action == AA.member_prune:
                    fields.append(
                        Field(
                            name=f'\N{WASTEBASKET}\N{VARIATION SELECTOR-16} {moderator} pruned members',
                            value=f'`  At` {fmt_date}',
                        )
                    )

                elif action == AA.member_update:
                    # Member timeout update:
                    before_timeout: Optional[datetime] = getattr(entry.before, 'timed_out_until', MISSING)
                    after_timeout: Optional[datetime] = getattr(entry.after, 'timed_out_until', MISSING)
                    if before_timeout is not MISSING and after_timeout is not MISSING:
                        # Timeout remove
                        if before_timeout and not after_timeout:
                            fields.append(
                                Field(
                                    name=f'\N{STOPWATCH}\N{VARIATION SELECTOR-16} {moderator} removed timeout for {target}',
                                    value=f'`  At` {fmt_date}\n` For` {entry.reason}',
                                )
                            )

                        # Timeout grant
                        elif not before_timeout and after_timeout:
                            fields.append(
                                Field(
                                    name=f'\N{STOPWATCH}\N{VARIATION SELECTOR-16} {moderator} timed out {target}',
                                    value=f'`    ` Until: {ts(after_timeout)}\n`  At` {fmt_date}\n` For` {entry.reason}',
                                )
                            )

                        # Timeout update
                        elif before_timeout and after_timeout:
                            fields.append(
                                Field(
                                    name=f'\N{STOPWATCH}\N{VARIATION SELECTOR-16} {moderator} updated timeout for {target}',
                                    value=(
                                        f'`   -` Until (old): {ts(before_timeout)}'
                                        f'\n`   +` Until (new): {ts(after_timeout)}'
                                        f'\n`  At` {fmt_date}'
                                        f'\n` For` {entry.reason}'
                                    ),
                                )
                            )

                    before_nick: Optional[str] = getattr(entry.before, 'nick', MISSING)
                    after_nick: Optional[str] = getattr(entry.after, 'nick', MISSING)

                    if before_nick is not MISSING and after_nick is not MISSING:
                        # Nick remove
                        if before_nick and not after_nick:
                            fields.append(
                                Field(
                                    name=f'{constants.EDIT_NICKNAME} {moderator} removed {target}\' nickname',
                                    value=f"`From` {before_nick}\n`  To`\n`  At` {fmt_date}",
                                )
                            )

                        # Nick add
                        if not before_nick and after_nick:
                            fields.append(
                                Field(
                                    name=f'{constants.EDIT_NICKNAME} {moderator} nicknamed {target}',
                                    value=f'`From`\n`  To` {after_nick}\n`  At` {fmt_date}',
                                )
                            )

                        # Nick update
                        if before_nick and after_nick:
                            fields.append(
                                Field(
                                    name=f'{constants.EDIT_NICKNAME} {moderator} edited {target}\'s nick',
                                    value=f'`From`{before_nick}\n`  To` {after_nick}\n`  At` {fmt_date}',
                                )
                            )

                # Thread Actions
                elif action in (AA.thread_create, AA.thread_delete, AA.thread_update):
                    thread_diff = ThreadDiff(entry.after)
                    if action in (AA.thread_create, AA.thread_delete):
                        fmt = [
                            f'`    ` Name: {mdr(thread_diff.name, escape=True)}',
                            f'`    ` Archived: {ctx.tick(thread_diff.archived or False)}',
                        ]

                        if thread_diff.auto_archive_duration:
                            delta = human_timedelta(
                                discord.utils.utcnow() + timedelta(seconds=thread_diff.auto_archive_duration), suffix=False
                            )
                            fmt.append(f'`    ` Auto archive duration: {delta}')

                        fmt.append(f'`  At` {fmt_date}')
                        act = "created" if action == AA.thread_create else "deleted"
                        fields.append(
                            Field(
                                name=f'{constants.TEXT_CHANNEL_WITH_THREAD} {moderator} {act} a thread', value='\n'.join(fmt)
                            )
                        )
                    else:
                        thread_before = ThreadDiff(entry.before)
                        fmt = []
                        if thread_before.name and thread_diff.name and thread_before.name != thread_diff.name:
                            fmt.extend([f'`-Old` Name: {mdr(thread_before.name)}', f'`+New` Name: {mdr(thread_diff.name)}'])
                        else:
                            fmt.append(f'`    ` Name: {target}')
                        if (
                            thread_diff.auto_archive_duration
                            and thread_before.auto_archive_duration
                            and thread_diff.auto_archive_duration != thread_before.auto_archive_duration
                        ):
                            dt = discord.utils.utcnow()
                            old = human_timedelta(dt + timedelta(seconds=thread_before.auto_archive_duration), suffix=False)
                            new = human_timedelta(dt + timedelta(seconds=thread_diff.auto_archive_duration), suffix=False)
                            fmt.extend([f'`-Old` Auto archive duration: {old}', f'`+New` Auto archive duration: {new}'])
                        fields.append(
                            Field(
                                name=f'{constants.TEXT_CHANNEL_WITH_THREAD} {moderator} updated a thread',
                                value='\n'.join(fmt),
                            )
                        )

                else:
                    continue

                if (first := (len(fields) == 5)) or (len(fields) % 20 == 0):
                    source = FieldsPageSource(fields, targeted_user=user)
                    if pages:
                        pages.update_source(source)
                        await pages.show_page(MockInteraction(), page_number=pages.current_page)
                    else:
                        pages = paginators.ViewMenuPages(source, ctx=ctx).add_info(info_embed)
                        await typer.__aexit__(None, None, None)
                        await pages.start()
                        if first and pages.message:
                            await pages.message.edit(view=LoadingView(timeout=1))

        if fields and not pages:
            source = FieldsPageSource(fields, targeted_user=user)
            pages = paginators.ViewMenuPages(source, ctx=ctx).add_info(info_embed)
            await pages.start()
        elif pages:
            source = FieldsPageSource(fields, targeted_user=user)
            pages.update_source(source)
            await pages.show_page(MockInteraction(), page_number=pages.current_page)
        else:
            await ctx.send('no matching records found.')

from __future__ import annotations
from datetime import datetime

from typing import TYPE_CHECKING, Any, List, NamedTuple, Optional

import discord
from discord.ext import commands, menus
from discord import AuditLogAction as AA
from discord.utils import MISSING

from utils import command, DuckCog, DuckContext, mdr, human_join, paginators

from bot import DuckBot
from utils.types import constants

if TYPE_CHECKING:
    from discord.audit_logs import TargetType


class WrapsWithMissing:
    """It wraps an object and returns a special
    value (MISSING) when an attribute is missing"""

    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, __name: str) -> Any:
        return getattr(self.obj, __name, MISSING)

    def __setattr__(self, __name: str, __value: Any) -> None:
        setattr(self.obj, __name, __value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} of {repr(self.obj)}>"


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

    def __init__(self, entries: List[Field], *, author: discord.abc.User):
        """Initializes the class

        Parameters
        ----------
        entries: List[Field]
            All the fields to be formatted.
        author: discord.abc.User
            The user who requested this menu.
        """
        super().__init__(entries, per_page=5)
        self.author = author

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
        embed.set_author(name=f'Audit logs for @{self.author}', icon_url=self.author.display_avatar.url)
        for idx, field in enumerate(entries, start=(menu.current_page * self.per_page) + 1):
            embed.add_field(
                name=f"`{idx:>3}.` {field.name}",
                value=field.value + ("\n\u200b" if idx % len(entries) else ""),
                inline=field.inline,
            )
        embed.set_footer(
            text=f"page {menu.current_page + 1} / {self.get_max_pages()} ({self.per_page * self.get_max_pages()} entries)"
        )
        return embed


class AuditLogViewer(DuckCog):
    """Audit log viewer."""

    def __init__(self, bot: DuckBot) -> None:
        """Initializes this class.

        Parameters
        ----------
        bot: DuckBot
            the bot
        """
        super().__init__(bot)

    @command(aliases=['al', 'audit', 'audinfo'])
    @commands.has_permissions(view_audit_log=True)
    @commands.bot_has_guild_permissions(view_audit_log=True)
    async def auditlogs(self, ctx: DuckContext, *, user: discord.User):
        """Shows audit logs for that user

        (audit logs only last up to 45 days... thanks discord.)
        """
        fields: List[Field] = []
        async with ctx.typing():
            async for entry in ctx.guild.audit_logs(limit=None):
                if not ((entry.target and entry.target.id == user.id) or (entry.user and entry.user.id == user.id)):
                    continue

                def fmt_u(ent: TargetType) -> str:
                    bot = ''
                    if isinstance(ent, discord.abc.GuildChannel):
                        sep = '#'
                    elif isinstance(ent, (discord.Member, discord.User)):
                        sep = '@'
                        bot = f"{constants.BOT} " if ent.bot else ""
                    elif isinstance(ent, discord.Role):
                        sep = '@'
                    else:
                        sep = ''
                    if ent == user:
                        return f'{bot}__{sep}{mdr(ent, escape=True)}__'
                    return f'{bot}{sep}{mdr(ent, escape=True)}'

                target: str = entry.target and fmt_u(entry.target) or '`Unknown`'
                moderator: str = entry.user and fmt_u(entry.user) or '`Unknown`'
                fmt_date: str = ts(entry.created_at, rel=True)

                action = entry.action

                if action is AA.kick:
                    fields.append(
                        Field(
                            name=f'\N{WOMANS BOOTS} {moderator} kicked {target}',
                            value=f'`  At` {fmt_date}\n`-For` `{mdr(entry.reason)}`',
                        )
                    )

                elif action is AA.ban:
                    fields.append(
                        Field(
                            name=f"\N{POLICE CARS REVOLVING LIGHT} {moderator} banned {target}",
                            value=f"`  At` {fmt_date}\n`-For` `{mdr(entry.reason)}`",
                        )
                    )

                elif action is AA.unban:
                    fields.append(
                        Field(
                            name=f"\N{PAPERCLIP} {moderator} unbanned {target}",
                            value=f"`  At` {fmt_date}\n`-For` `{mdr(entry.reason)}`",
                        )
                    )

                elif action is AA.member_role_update:
                    removed = list(map(lambda r: r.mention, set(entry.before.roles) - set(entry.after.roles)))
                    added = list(map(lambda r: r.mention, set(entry.after.roles) - set(entry.before.roles)))
                    extra = f"\n`-For` `{mdr(entry.reason)}`" if entry.reason else ''
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
                    before: Optional[datetime] = getattr(entry.before, 'timed_out_until', MISSING)
                    after: Optional[datetime] = getattr(entry.after, 'timed_out_until', MISSING)
                    if before is not MISSING and after is not MISSING:

                        # Timeout remove
                        if before and not after:
                            fields.append(
                                Field(
                                    name=f'\N{STOPWATCH}\N{VARIATION SELECTOR-16} {moderator} removed timeout for {target}',
                                    value=f'`  At` {fmt_date}\n` For` {entry.reason}',
                                )
                            )

                        # Timeout grant
                        elif not before and after:
                            fields.append(
                                Field(
                                    name=f'\N{STOPWATCH}\N{VARIATION SELECTOR-16} {moderator} timed out {target}',
                                    value=f'`    ` Until: {ts(after)}\n`  At` {fmt_date}\n` For` {entry.reason}',
                                )
                            )

                        # Timeout update
                        elif before and after:
                            fields.append(
                                Field(
                                    name=f'\N{STOPWATCH}\N{VARIATION SELECTOR-16} {moderator} updated timeout for {target}',
                                    value=(
                                        f'`   -` Until (old): {ts(before)}'
                                        f'\n`   +` Until (new): {ts(after)}'
                                        f'\n`  At` {fmt_date}'
                                        f'\n` For` {entry.reason}'
                                    ),
                                )
                            )

                    if ... is not MISSING and ... is not MISSING:

                        # Nick remove
                        if ... and not ...:
                            ...

        if fields:
            source = FieldsPageSource(fields, author=ctx.author)
            pages = paginators.ViewMenuPages(source, ctx=ctx)
            await pages.start()
        else:
            await ctx.send('no matching records found.')

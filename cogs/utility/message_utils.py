from dis import disco
import re
import re
import typing
import unicodedata
from inspect import Parameter
from typing import Optional

import discord
from discord.ext import commands, menus

from bot import CustomContext
from helpers import paginator
from ._base import UtilityBase


class MessageUtils(UtilityBase):
    @commands.command(name='charinfo')
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def character_info(self, ctx: CustomContext, *, characters: str):
        """Shows you information about a number of characters."""

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return (
                f'`\\U{digit:>08}`: {name} - **{c}** \N{EM DASH} ' f'<http://www.fileformat.info/info/unicode/char/{digit}>'
            )

        msg = '\n'.join(map(to_string, characters))

        menu = menus.MenuPages(
            paginator.CharacterInformationPageSource(msg.split("\n"), per_page=20), delete_message_after=True
        )
        await menu.start(ctx)

    @commands.command(aliases=['s', 'send'])
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    async def say(self, ctx: CustomContext, *, msg: str) -> Optional[discord.Message]:
        """Relays the given content to the current channel."""
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await ctx.message.delete(delay=0)  # passing delay schedules it as a task.

        await ctx.send(
            msg[0:2000],
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=True),
            reference=ctx.message.reference,  # type: ignore
            reply=False,
            reminders=False,
        )

    @commands.command(aliases=['a', 'an', 'announce'])
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    async def echo(
        self, ctx: CustomContext, channel: discord.abc.GuildChannel, *, content: Optional[str]
    ) -> discord.Message:
        """Echoes the given content to the other channel.

        You must have both Send Messages and Manage Messages in the other channel.
        You can also reply to another message to echo its content instead.
        """
        required = discord.Permissions(send_messages=True, manage_messages=True)
        check = channel.guild == ctx.guild and channel.permissions_for(ctx.author).is_superset(required)
        check = check or await self.bot.is_owner(ctx.author)

        if not check:
            await ctx.send("You cannot send messages in that channel.")

        if not isinstance(channel, discord.abc.Messageable) or not channel.permissions_for(ctx.me).send_messages:
            raise commands.BadArgument("I cannot message that channel.")

        if content is None:
            if ctx.message.reference and isinstance(ctx.message.reference.resolved, discord.Message):
                content = ctx.message.reference.resolved.content
            else:
                raise commands.MissingRequiredArgument(commands.Parameter(name='message', kind=Parameter.POSITIONAL_ONLY))

        return await channel.send(
            content[0:2000], allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)
        )

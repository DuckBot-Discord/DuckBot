import re
import re
import typing
import unicodedata
from inspect import Parameter
from typing import Optional

import discord
from discord.ext import commands, menus

from DuckBot import errors
from DuckBot.__main__ import CustomContext
from DuckBot.helpers import paginator
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

    @commands.command(aliases=['s', 'send'], help="Speak as if you were me. # URLs/Invites not allowed!")
    @commands.check_any(commands.bot_has_permissions(send_messages=True), commands.is_owner())
    async def say(self, ctx: CustomContext, *, msg: str) -> Optional[discord.Message]:

        results = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|)+", msg)  # HTTP/HTTPS URL regex
        results2 = re.findall(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", msg
        )  # Discord invite regex
        if results or results2:
            await ctx.send(f"hey, {ctx.author.mention}. Urls or invites aren't allowed!", delete_after=10)
            return await ctx.message.delete(delay=10)

        await ctx.message.delete(delay=0)
        if ctx.channel.permissions_for(ctx.author).manage_messages:
            allowed = True
        else:
            allowed = False

        return await ctx.send(
            msg[0:2000],
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=allowed),
            reference=ctx.message.reference,
            reply=False,
            reminders=False,
        )

    @commands.command(aliases=['a', 'an', 'announce'], usage="<channel> <message_or_reply>")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def echo(
        self, ctx: CustomContext, channel: typing.Union[discord.TextChannel, int], *, message_or_reply: str = None
    ) -> discord.Message:
        """ "
        Echoes a message to another channel
        # If a message is quoted, it will echo the quoted message's content.
        """
        if isinstance(channel, int) and self.bot.is_owner(ctx.author):
            channel = self.bot.get_channel(channel)
        if not channel:
            raise commands.MissingRequiredArgument(Parameter(name='channel', kind=Parameter.POSITIONAL_ONLY))
        if not ctx.message.reference and not message_or_reply:
            raise commands.MissingRequiredArgument(Parameter(name='message_or_reply', kind=Parameter.POSITIONAL_ONLY))
        elif ctx.message.reference:
            message_or_reply = ctx.message.reference.resolved.content
        return await channel.send(
            message_or_reply[0:2000], allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)
        )

    @commands.command(aliases=['e', 'edit'], name='edit-message', usage="[new message] [--d|--s]")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def edit_message(self, ctx: CustomContext, *, new: typing.Optional[str] = '--d'):
        """Quote a bot message to edit it.
        # Append --s at the end to suppress embeds and --d to delete the message
        """
        if ctx.reference:
            if ctx.reference.author != self.bot.user:
                return
            if new.endswith("--s"):
                await ctx.reference.edit(content=f"{new[:-3]}", suppress=True)
            elif new.endswith('--d'):
                await ctx.reference.delete()
            else:
                await ctx.reference.edit(content=new, suppress=False)
            await ctx.message.delete(delay=0.1)
        else:
            raise errors.NoQuotedMessage

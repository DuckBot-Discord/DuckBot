import typing

import discord
from discord.ext import commands

from helpers.context import CustomContext
from ._base import ModerationBase, BannedMember


class BasicModCommands(ModerationBase):
    @commands.command(help="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, kick_members=True)
    async def kick(self, ctx: CustomContext, member: discord.Member, *, reason: typing.Optional[str] = None):
        self.bot_can_execute_action(ctx, member)
        if not self.can_execute_action(ctx, ctx.author, member):
            raise commands.BadArgument('You cannot kick this member.')
        await member.kick(reason=f"Kicked by {ctx.author} ({ctx.author.id}) " + (f" for {reason}" if reason else ""))
        await ctx.send(f'👢 **|** **{ctx.author}** kicked **{member}**' + (f"\nFor {reason}" if reason else ""))

    @commands.command(help="Bans a member from the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    async def ban(
        self,
        ctx: CustomContext,
        user: typing.Union[discord.Member, discord.User],
        delete_days: typing.Optional[int] = 1,
        *,
        reason: str = None,
    ):
        if delete_days and not 8 > delete_days > -1:
            raise commands.BadArgument("**delete_days** must be between 0 and 7 days")

        self.bot_can_execute_action(ctx, user)

        if self.can_execute_action(ctx, ctx.author, user):
            await ctx.guild.ban(
                user,
                reason=f"Banned by {ctx.author} ({ctx.author.id})" + (f'for {reason}' if reason else ''),
                delete_message_days=delete_days,
            )  # noqa
            return await ctx.send(
                f'🔨 **|** banned **{discord.utils.escape_markdown(str(user))}**' + (f' for {reason}' if reason else '')
            )
        await ctx.send('Sorry, but you can\'t ban that member')

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    async def softban(
        self,
        ctx: CustomContext,
        user: typing.Union[discord.Member, discord.User],
        delete_days: typing.Optional[int] = 1,
        *,
        reason: str = None,
    ):
        """Soft-bans a member from the server.
        What is soft ban?
        """
        if delete_days and not 8 > delete_days > -1:
            raise commands.BadArgument("**delete_days** must be between 0 and 7 days")

        self.bot_can_execute_action(ctx, user)

        if self.can_execute_action(ctx, ctx.author, user):
            await ctx.guild.ban(
                user,
                reason=f"Soft-banned by {ctx.author} ({ctx.author.id})" + (f'for {reason}' if reason else ''),
                delete_message_days=delete_days,
            )  # noqa
            await ctx.guild.unban(
                user, reason=f"Soft-banned by {ctx.author} ({ctx.author.id})" + (f'for {reason}' if reason else '')
            )
            return await ctx.send(
                f'🔨 **|** soft-banned **{discord.utils.escape_markdown(str(user))}**' + (f' for {reason}' if reason else '')
            )
        await ctx.send('Sorry, but you can\'t ban that member')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx: CustomContext, *, user: BannedMember):
        """unbans a user from this server.
        Can search by:
        - `user ID` (literal - number)
        - `name#0000` (literal - case insensitive)
        - `name` (literal - case insensitive)
        - `name` (close matches - will prompt to confirm)
        """
        user: discord.guild.BanEntry
        await ctx.guild.unban(user.user, reason=f"Unban by {ctx.author} ({ctx.author.id})")
        extra = f"Previously banned for: {user.reason}" if user.reason else ''
        return await ctx.send(f"Unbanned **{discord.utils.escape_markdown(str(user.user))}**\n{extra}")

    @commands.command(aliases=['sn', 'nick'])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(send_messages=True, manage_nicknames=True)
    async def setnick(
        self, ctx: CustomContext, member: discord.Member, *, new: str = None
    ) -> typing.Optional[discord.Message]:
        """
        Removes someone's nickname. Don't send a new nickname to remove it.
        """
        new = new or member.name
        old = member.display_name
        if len(new) > 32:
            raise commands.BadArgument(f'Nickname too long. {len(new)}/32')
        self.bot_can_execute_action(ctx, member)
        if not self.can_execute_action(ctx, ctx.author, member) and ctx.guild.id != 745059550998298756:
            raise commands.MissingPermissions(['role_hierarchy'])

        await member.edit(nick=new)
        return await ctx.send(
            f"✏ {ctx.author.mention} edited {member.mention}" f"\nnickname: **`{old}`** -> **`{new}`**",
            allowed_mentions=discord.AllowedMentions().none(),
        )

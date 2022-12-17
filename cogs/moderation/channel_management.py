import datetime
import typing

import discord
from discord.ext import commands

from DuckBot.__main__ import CustomContext
from DuckBot.helpers import time_inputs as helpers
from ._base import ModerationBase


class ChannelManagementCommands(ModerationBase):
    @commands.command(aliases=['lock', 'ld'])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def lockdown(self, ctx, channel: typing.Optional[discord.TextChannel], role: typing.Optional[discord.Role]):
        """
        Locks down the channel. Optionally, you can specify a channel and role to lock lock down.
        Channel: You and the bot must have manage roles permission in the channel.
        Role: The specified role must be lower than yours and the bots top role.
        """

        role = (
            role
            if role and (role < ctx.me.top_role or ctx.author == ctx.guild.owner) and role < ctx.author.top_role
            else ctx.guild.default_role
        )

        channel = (
            channel
            if channel and channel.permissions_for(ctx.author).manage_roles and channel.permissions_for(ctx.me).manage_roles
            else ctx.channel
        )

        perms = channel.overwrites_for(ctx.me)
        perms.update(send_messages=True, add_reactions=True, create_public_threads=True, create_private_threads=True)

        await channel.set_permissions(ctx.me, overwrite=perms, reason=f'Channel lockdown by {ctx.author} ({ctx.author.id})')

        perms = channel.overwrites_for(role)
        perms.update(send_messages=False, add_reactions=False, create_public_threads=False, create_private_threads=False)

        await channel.set_permissions(
            role, overwrite=perms, reason=f'Channel lockdown for {role.name} by {ctx.author} ({ctx.author.id})'
        )
        await ctx.send(
            f"Locked down **{channel.name}** for **{role.name}**", allowed_mentions=discord.AllowedMentions().none()
        )

    @commands.command(aliases=['unlockdown', 'uld'])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unlock(self, ctx, channel: typing.Optional[discord.TextChannel], role: typing.Optional[discord.Role]):
        """
        Unlocks the channel. Optionally, you can specify a channel and role to lock lock down.
        Channel: You must have manage roles permission, and the bot must do so too.
        Role: The specified role must be lower than yours and the bots top role.
        """

        role = (
            role
            if role and (role < ctx.me.top_role or ctx.author == ctx.guild.owner) and role < ctx.author.top_role
            else ctx.guild.default_role
        )

        channel = (
            channel
            if channel and channel.permissions_for(ctx.author).manage_roles and channel.permissions_for(ctx.me).manage_roles
            else ctx.channel
        )

        perms = channel.overwrites_for(ctx.guild.default_role)
        perms.update(send_messages=None, add_reactions=None, create_public_threads=None, create_private_threads=None)

        await channel.set_permissions(
            role, overwrite=perms, reason=f'Channel lockdown for {role.name} by {ctx.author} ({ctx.author.id})'
        )

        await ctx.send(f"Unlocked **{channel.name}** for **{role.name}**", allowed_mentions=discord.AllowedMentions().none())

    @commands.command(usage="[channel] <duration|reset>")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(
        self, ctx: CustomContext, channel: typing.Optional[discord.TextChannel], *, duration: helpers.ShortTime = None
    ) -> discord.Message:
        """
        Sets the current slow mode to a delay between 1s and 6h. If specified, sets it for another channel.
        # Duration must be a short time, for example: 1s, 5m, 3h, or a combination of those, like 3h5m25s.
        # To reset the slow mode, execute command without specifying a duration.
        Channel: You must have manage channel permission, and the bot must do so too.
        """

        channel = (
            channel
            if channel
            and channel.permissions_for(ctx.author).manage_channels
            and channel.permissions_for(ctx.me).manage_channels
            else ctx.channel
        )

        if not duration:
            await channel.edit(slowmode_delay=0)
            return await ctx.send(f"Messages in **{channel.name}** can now be sent without slow mode")

        created_at = ctx.message.created_at
        delta: datetime.timedelta = duration.dt > (created_at + datetime.timedelta(hours=6))
        if delta:
            return await ctx.send('Duration is too long. Must be at most 6 hours.')
        seconds = (duration.dt - ctx.message.created_at).seconds
        await channel.edit(slowmode_delay=int(seconds))

        human_delay = helpers.human_timedelta(duration.dt, source=created_at)
        return await ctx.send(f"Messages in **{channel.name}** can now be sent **every {human_delay}**")

    @commands.command()
    async def archive(self, ctx, channel: typing.Optional[discord.Thread], *, reason: str = None):
        """
        Archives the current thread, or any thread mentioned.
        # Optionally, input a reason to be displayed in the message.
        """
        channel = channel or ctx.channel
        if not isinstance(channel, discord.Thread):
            return await ctx.send("That's not a thread!")

        await channel.send(f"Thread archived by **{ctx.author}**" f"\n{f'**With reason:** {reason}' if reason else ''}")
        await channel.edit(archived=True)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def block(self, ctx, *, member: discord.Member):
        """Blocks a user from your channel."""

        if not self.can_execute_action(ctx, ctx.author, member):
            return await ctx.send('You are not high enough in role hierarchy to do that!')

        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        try:
            await ctx.channel.set_permissions(
                member,
                reason=reason,
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
            )
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send('Something went wrong...')
        else:
            await ctx.send(f'✅ **|** Blocked **{discord.utils.remove_markdown(str(member))}** from **{ctx.channel}**')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unblock(self, ctx, *, member: discord.Member):
        """Unblocks a user from your channel."""

        if not self.can_execute_action(ctx, ctx.author, member):
            return await ctx.send('You are not high enough in role hierarchy to do that!')

        reason = f'Unblock by {ctx.author} (ID: {ctx.author.id})'

        try:
            await ctx.channel.set_permissions(
                member,
                reason=reason,
                send_messages=None,
                add_reactions=None,
                create_public_threads=None,
                create_private_threads=None,
                send_messages_in_threads=None,
            )
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send('Something went wrong...')
        else:
            await ctx.send(f'✅ **|** Unblocked **{discord.utils.remove_markdown(str(member))}** from **{ctx.channel}**')

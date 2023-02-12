import asyncio
import difflib
import typing

import discord
from discord.ext import commands

import errors
from bot import DuckBot, CustomContext
from helpers.helper import LoggingEventsFlags
from ._base import ConfigBase


async def get_wh(channel: discord.TextChannel):
    if channel.permissions_for(channel.guild.me).manage_webhooks:
        webhooks = await channel.webhooks()
        for w in webhooks:
            if w.user == channel.guild.me:
                return w.url
        else:
            return (await channel.create_webhook(name="DuckBot Logging", avatar=await channel.guild.me.avatar.read())).url
    else:
        raise commands.BadArgument("Cannot create webhook!")


class ChannelsView(discord.ui.View):
    # TODO optimize this piece of shit code.
    def __init__(self, ctx: CustomContext):
        super().__init__()
        self.message: discord.Message = None
        self.ctx = ctx
        self.bot: DuckBot = ctx.bot
        self.lock = asyncio.Lock()
        self.valid_channels = [
            "default",
            "message",
            "member",
            "join_leave",
            "voice",
            "server",
        ]

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="♾", row=0)
    async def default(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send("Please send a channel to change the **Message Events Channel**")
            to_delete.append(m)

            def check(msg: discord.Message):
                if msg.channel == self.ctx.channel and msg.author == self.ctx.author:
                    to_delete.append(msg)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for("message", check=check)
                if message.content == "cancel":
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction("✅")
            channel_string = message.content
            if channel_string.lower() == "cancel":
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        "UPDATE log_channels SET default_channel = $2, default_chid = $3 WHERE guild_id = $1",
                        self.ctx.guild.id,
                        webhook_url,
                        channel.id,
                    )
                    self.bot.update_log("default", webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send(
                        "Could not create a webhook in that channel!\n" "Do i have **Manage Webhooks** permissions there?"
                    )
                except discord.HTTPException:
                    await self.ctx.send("Something went wrong while creating a webhook...")
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)  # type: ignore
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="📨", row=0)
    async def message(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True  # type: ignore
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send("Please send a channel to change the **Message Events Channel**")
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for("message", check=check)
                if message.content == "cancel":
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction("✅")
            channel_string = message.content
            if channel_string.lower() == "cancel":
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        "UPDATE log_channels SET message_channel = $2, message_chid = $3 WHERE guild_id = $1",
                        self.ctx.guild.id,
                        webhook_url,
                        channel.id,
                    )
                    self.bot.update_log("message", webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send(
                        "Could not create a webhook in that channel!\n" "Do i have **Manage Webhooks** permissions there?"
                    )
                except discord.HTTPException:
                    await self.ctx.send("Something went wrong while creating a webhook...")
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="👋", row=1)
    async def join_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send("Please send a channel to change the **Join and Leave Events Channel**")
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for("message", check=check)
                if message.content == "cancel":
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction("✅")
            channel_string = message.content
            if channel_string.lower() == "cancel":
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        "UPDATE log_channels SET join_leave_channel = $2, join_leave_chid = $3 WHERE guild_id = $1",
                        self.ctx.guild.id,
                        webhook_url,
                        channel.id,
                    )
                    self.bot.update_log("join_leave", webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send(
                        "Could not create a webhook in that channel!\n" "Do i have **Manage Webhooks** permissions there?"
                    )
                except discord.HTTPException:
                    await self.ctx.send("Something went wrong while creating a webhook...")
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="👤", row=0)
    async def member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send('Please send a channel to change the **Member Events Channel**\nSend "cancel" to cancel')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for("message", check=check)
                if message.content == "cancel":
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction("✅")
            channel_string = message.content
            if channel_string.lower() == "cancel":
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        "UPDATE log_channels SET member_channel = $2, member_chid = $3 WHERE guild_id = $1",
                        self.ctx.guild.id,
                        webhook_url,
                        channel.id,
                    )
                    self.bot.update_log("member", webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send(
                        "Could not create a webhook in that channel!\n" "Do i have **Manage Webhooks** permissions there?"
                    )
                except discord.HTTPException:
                    await self.ctx.send("Something went wrong while creating a webhook...")
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="⚙", row=1)
    async def server(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send("Please send a channel to change the **Server Events Channel**")
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for("message", check=check)
                if message.content == "cancel":
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction("✅")
            channel_string = message.content
            if channel_string.lower() == "cancel":
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        "UPDATE log_channels SET server_channel = $2, server_chid = $3 WHERE guild_id = $1",
                        self.ctx.guild.id,
                        webhook_url,
                        channel.id,
                    )
                    self.bot.update_log("server", webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send(
                        "Could not create a webhook in that channel!\n" "Do i have **Manage Webhooks** permissions there?"
                    )
                except discord.HTTPException:
                    await self.ctx.send("Something went wrong while creating a webhook...")
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="🎙", row=1)
    async def voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send(
                "Please send a channel to change the **Voice Events Channel**" '\n_Send "cancel" to cancel_'
            )
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for("message", check=check)
                if message.content == "cancel":
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction("✅")
            channel_string = message.content
            if channel_string.lower() == "cancel":
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        "UPDATE log_channels SET voice_channel = $2, voice_chid = $3 WHERE guild_id = $1",
                        self.ctx.guild.id,
                        webhook_url,
                        channel.id,
                    )
                    self.bot.update_log("voice", webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send(
                        "Could not create a webhook in that channel!\n" "Do i have **Manage Webhooks** permissions there?"
                    )
                except discord.HTTPException:
                    await self.ctx.send("Something went wrong while creating a webhook...")
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.red, label="stop", row=2)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lock.locked():
            return await interaction.response.send_message("Can't do that while waiting for a message!", ephemeral=True)
        await interaction.response.defer()
        await self.on_timeout()

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
            child.style = discord.ButtonStyle.grey
        await self.message.edit(view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(f"This menu belongs to **{self.ctx.author}**, sorry! 💖", ephemeral=True)
        return False

    async def update_message(self, edit: bool = True):
        channels = await self.bot.db.fetchrow("SELECT * FROM log_channels WHERE guild_id = $1", self.ctx.guild.id)
        embed = discord.Embed(
            title="Logging Channels",
            colour=discord.Colour.blurple(),
            timestamp=self.ctx.message.created_at,
        )
        default = self.bot.get_channel(channels["default_chid"] or 1)
        message = self.bot.get_channel(channels["message_chid"] or 1)
        join_leave = self.bot.get_channel(channels["join_leave_chid"] or 1)
        member = self.bot.get_channel(channels["member_chid"] or 1)
        server = self.bot.get_channel(channels["server_chid"] or 1)
        voice = self.bot.get_channel(channels["voice_chid"] or 1)
        embed.description = (
            f"**♾ Default channel:** {default.mention}"
            f"\n**📨 Message events:** {message.mention if message else ''}"
            f"\n**👋 Joining and Leaving:** {join_leave.mention if join_leave else ''}"
            f"\n**👤 Member events:** {member.mention if member else ''}"
            f"\n**⚙ Server events:** {server.mention if server else ''}"
            f"\n**🎙 Voice events:** {voice.mention if voice else ''}"
            f"\n"
            f"\n_Channels not shown here will be_"
            f"\n_delivered to the default channel._"
        )
        loggings = self.bot.guild_loggings[self.ctx.guild.id]
        enabled = [x for x, y in set(loggings) if y is True]
        embed.set_footer(text=f"{len(enabled)}/{len(set(loggings))} events enabled.")
        for child in self.children:
            child.disabled = False
            if child.row < 2:
                child.style = discord.ButtonStyle.grey
            else:
                child.style = discord.ButtonStyle.red
        if edit:
            await self.message.edit(embed=embed, view=self)
        else:
            return await self.ctx.send(embed=embed, view=self)

    async def start(self):
        self.message = await self.update_message(edit=False)


# noinspection PyProtocol
class ValidEventConverter(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):
        new = argument.replace("-", "_").replace(" ", "_").lower()
        all_events = dict(LoggingEventsFlags.all())
        if new in all_events:
            return new
        maybe_events = difflib.get_close_matches(argument, all_events)
        if maybe_events:
            c = await ctx.confirm(
                f"Did you mean... **`{maybe_events[0]}`**?",
                delete_after_confirm=True,
                delete_after_timeout=False,
                buttons=(
                    ("☑", None, discord.ButtonStyle.blurple),
                    ("🗑", None, discord.ButtonStyle.gray),
                ),
            )
            if c:
                return maybe_events[0]
            elif c is None:
                raise errors.NoHideout()
        raise commands.BadArgument(f"`{argument[0:100]}` is not a valid logging event.")


styles = {
    True: discord.ButtonStyle.green,
    False: discord.ButtonStyle.gray,
    None: discord.ButtonStyle.grey,
}


class EventToggle(discord.ui.Button["AllEvents"]):
    def __init__(self, event: str, enabled: bool):
        super().__init__(
            label=event.title().replace("_", " ").replace("guild", "server"),
            style=styles[enabled],
        )
        self.emoji = CustomContext.default_tick(enabled)
        self.event = event
        self.enabled = enabled

    async def callback(self, interaction: discord.Interaction):
        self.enabled = not self.enabled
        q = await self.view.ctx.bot.db.fetch(
            f"UPDATE logging_events SET {self.event} = $1 WHERE guild_id = $2 RETURNING {self.event}",
            self.enabled,
            self.view.ctx.guild.id,
        )
        if not q:
            await interaction.response.send_message("For some reason logging is not set up anymore.")
            self.view.stop()
            return
        self.style = styles[self.enabled]
        self.emoji = self.view.ctx.default_tick(self.enabled)
        setattr(
            self.view.ctx.bot.guild_loggings[self.view.ctx.guild.id],
            self.event,
            self.enabled,
        )
        setattr(self.view.events, self.event, self.enabled)
        await interaction.response.edit_message(embed=await self.view.async_update_event(), view=self.view)


class AllEvents(discord.ui.View):
    def __init__(self, ctx: CustomContext, events: LoggingEventsFlags):
        super().__init__()
        self.ctx = ctx
        self.events = events

    async def start(self):
        self.prepare()
        embed = await self.async_update_event()
        await self.ctx.send(embed=embed, view=self)

    def prepare(self):
        events = {
            "message": "📨",
            "join_leave": "👋",
            "member": "👤",
            "voice": "🎙",
            "server": "⚙",
        }
        for event, emoji in events.items():
            self.select_category.options.append(
                discord.SelectOption(label=f"{event.title()} events", value=event, emoji=emoji)
            )
        option = "message"
        options: typing.List[str, bool] = [o for o, v in getattr(LoggingEventsFlags, option)() if v is True]
        opts = {k: v for k, v in self.events if k in options}
        for option, value in opts.items():
            self.add_item(EventToggle(option, value))

    def update_embed(self):
        events = self.events
        ctx = self.ctx
        embed = discord.Embed(
            title="Logging events for this server",
            colour=discord.Colour.blurple(),
            timestamp=ctx.message.created_at,
        )
        message_events = [
            ctx.default_tick(events.message_delete, "Message Delete"),
            ctx.default_tick(events.message_edit, "Message Edit"),
            ctx.default_tick(events.message_purge, "Message Purge"),
        ]
        embed.add_field(name="Message Events", value="\n".join(message_events))
        join_leave_events = [
            ctx.default_tick(events.member_join, "Member Join"),
            ctx.default_tick(events.member_leave, "Member Leave"),
        ]
        subtract = 0
        if not ctx.me.guild_permissions.manage_channels:
            if events.invite_create:
                join_leave_events.append("⚠ Invite Create" "\n╰ Manage Channels")
                subtract += 1
            else:
                join_leave_events.append(ctx.default_tick(events.invite_create, "Invite Create"))
            if events.invite_delete:
                join_leave_events.append("⚠ Invite Delete" "\n╰ Manage Channels")
                subtract += 1
            else:
                join_leave_events.append(ctx.default_tick(events.invite_delete, "Invite Create"))
        else:
            join_leave_events.append(ctx.default_tick(events.invite_create, "Invite Create"))
            join_leave_events.append(ctx.default_tick(events.invite_delete, "Invite Delete"))
        embed.add_field(name="Join Leave Events", value="\n".join(join_leave_events))
        member_update_evetns = [
            ctx.default_tick(events.member_update, "Member Update"),
            ctx.default_tick(events.user_update, "User Update"),
            ctx.default_tick(events.user_ban, "User Ban"),
            ctx.default_tick(events.user_unban, "User Unban"),
        ]
        embed.add_field(name="Member Events", value="\n".join(member_update_evetns))
        voice_events = [
            ctx.default_tick(events.voice_join, "Voice Join"),
            ctx.default_tick(events.voice_leave, "Voice Leave"),
            ctx.default_tick(events.voice_move, "Voice Move"),
            ctx.default_tick(events.voice_mod, "Voice Mod"),
            ctx.default_tick(events.stage_open, "Stage Open"),
            ctx.default_tick(events.stage_close, "Stage Close"),
        ]
        embed.add_field(name="Voice Events", value="\n".join(voice_events))
        server_events = [
            ctx.default_tick(events.channel_create, "Channel Create"),
            ctx.default_tick(events.channel_delete, "Channel Delete"),
            ctx.default_tick(events.channel_edit, "Channel Edit"),
            ctx.default_tick(events.role_create, "Role Create"),
            ctx.default_tick(events.role_delete, "Role Delete"),
            ctx.default_tick(events.role_edit, "Role Edit"),
            ctx.default_tick(events.server_update, "Server Update"),
            ctx.default_tick(events.emoji_create, "Emoji Create"),
            ctx.default_tick(events.emoji_delete, "Emoji Delete"),
            ctx.default_tick(events.emoji_update, "Emoji Update"),
            ctx.default_tick(events.sticker_create, "Sticker Create"),
            ctx.default_tick(events.sticker_delete, "Sticker Delete"),
            ctx.default_tick(events.sticker_update, "Sticker Update"),
        ]
        embed.add_field(name="Server Events", value="\n".join(server_events))
        embed.description = "✅ Enabled • ❌ Disabled • ⚠ Missing Perms"
        enabled = [x for x, y in set(events) if y is True]
        amount_enabled = len(enabled) - subtract
        embed.set_footer(text=f"{amount_enabled}/{len(set(events))} events enabled.")
        return embed

    async def async_update_event(self):
        return await self.ctx.bot.loop.run_in_executor(None, self.update_embed)

    @discord.ui.select(placeholder="Select an event category to view")
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        option = select.values[0]
        options: typing.List[str, bool] = [o for o, v in getattr(LoggingEventsFlags, option)() if v is True]
        opts = {k: v for k, v in self.events if k in options}  # type: ignore
        self.clear_items()
        self.add_item(select)
        self.add_item(self.delete)
        for option, value in opts.items():
            self.add_item(EventToggle(option, value))
        await interaction.response.edit_message(embed=await self.async_update_event(), view=self)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red, emoji="🗑", row=4)
    async def delete(self, interaction: discord.Interaction, _):
        await interaction.message.delete()
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author and interaction.user.guild_permissions.manage_guild


class Logging(ConfigBase):
    @commands.group(aliases=["logging", "logger"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log(self, ctx: CustomContext):
        """Base command to manage the logging events.

        Run this command without sub-commands to show more detailed information on the logging module"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="DuckBot Logging Module",
                colour=discord.Colour.yellow(),
                description="**What is this?**\n"
                "The Logging module is a fully customizable logger for different server events. "
                "It can be configured to log up to 30 unique events, and for those events to be "
                "delivered into 5 different channels.\n"
                "**Available commands:**\n"
                f"\n`{ctx.clean_prefix}log enable <channel>` Enables logging for this server."
                f"\n`{ctx.clean_prefix}log disable` Disables logging for this server."
                f"\n`{ctx.clean_prefix}log channels` Shows the current channel settings."
                f"\n`{ctx.clean_prefix}log edit-channels` Modifies the log channels (interactive menu)."
                f"\n`{ctx.clean_prefix}log all-events` Shows all events, disabled and enabled."
                f"\n`{ctx.clean_prefix}log enable-event <event>` Enables a specific event from the list."
                f"\n`{ctx.clean_prefix}log disable-event <event>` Disables a specific event from the list."
                f"\n`{ctx.clean_prefix}log auto-setup` Creates a logging category with different channels."
                f"\n"
                f"\nFor more info on a specific command, run the `help` command with it, E.G:"
                f"\n`db.help log enable-event`",
            )
            await ctx.send(embed=embed)

    @log.command(
        name="enable",
        aliases=["set-default"],
        preview="https://i.imgur.com/SYOrcfG.gif",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_enable(self, ctx: CustomContext, channel: discord.TextChannel):
        """Enables the logging module to deliver to one channel.

        If logging is already enabled, it will set the default logging channel to the one specified.
        _Note: This will not modify your enabled/disabled events, if any._"""
        if ctx.guild.id in self.bot.log_channels:
            raise commands.BadArgument("This server already has a logging enabled.")
        if not channel.permissions_for(ctx.me).manage_webhooks and not channel.permissions_for(ctx.me).send_messages:
            raise commands.BadArgument(f"I'm missing the Manage Webhooks permission in {channel.mention}")
        await ctx.typing()

        try:
            webhooks = await channel.webhooks()
        except (discord.Forbidden, discord.HTTPException):
            raise commands.BadArgument(
                f"I was unable to get the list of webhooks in {channel.mention}. (Missing Permissions - Manage Webhooks)"
            )
        for w in webhooks:
            if w.user == self.bot.user:
                webhook_url = w.url
                break
        else:
            if len(webhooks) == 10:
                raise commands.BadArgument(f"{channel.mention} has already the max number of webhooks! (10 webhooks)")
            try:
                w = await channel.create_webhook(
                    name="DuckBot logging",
                    avatar=await ctx.me.avatar.read(),
                    reason="DuckBot logging",
                )
                webhook_url = w.url
            except discord.Forbidden:
                raise commands.BadArgument(
                    f"I couldn't create a webhook in {channel.mention}(Missing Permissions - Manage Webhooks)"
                )
            except discord.HTTPException:
                raise commands.BadArgument(
                    f"There was an unexpected error while creating a webhook in {channel.mention} (HTTP exception) - Perhaps try again?"
                )
        await self.bot.db.execute(
            "INSERT INTO guilds (guild_id) VALUES ($1) " "ON CONFLICT (guild_id) DO NOTHING",
            ctx.guild.id,
        )
        await self.bot.db.execute(
            "INSERT INTO log_channels(guild_id, default_channel, default_chid) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id) DO UPDATE SET default_channel = $2, default_chid = $3",
            ctx.guild.id,
            webhook_url,
            channel.id,
        )
        await self.bot.db.execute(
            "INSERT INTO logging_events(guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
            ctx.guild.id,
        )
        self.bot.guild_loggings[ctx.guild.id] = LoggingEventsFlags.all()
        try:
            self.bot.log_channels[ctx.guild.id]._replace(default=webhook_url)
        except KeyError:
            self.bot.log_channels[ctx.guild.id] = self.bot.log_webhooks(
                default=webhook_url,
                voice=None,
                message=None,
                member=None,
                server=None,
                join_leave=None,
            )
        await ctx.send(
            f"Successfully set the logging channel to {channel.mention}"
            f"\n_see `{ctx.clean_prefix}help log` for more customization commands!_"
        )

    @log.command(name="disable", aliases=["disable-logging"])
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_disable(self, ctx: CustomContext):
        """Disables logging for this server, and deletes all the bots logging webhooks."""
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument("Logging is not enabled for this server!")
        confirm = await ctx.confirm(
            "**Are you sure you want to disable logging?**"
            "\nThis will overwrite and disable **all** delivery channels, and delete all my webhooks.",
            delete_after_confirm=True,
            delete_after_timeout=False,
        )
        if not confirm:
            return
        async with ctx.typing():
            try:
                self.bot.log_channels.pop(ctx.guild.id)
            except KeyError:
                pass
            channels = await self.bot.db.fetchrow("DELETE FROM log_channels WHERE guild_id = $1 RETURNING *", ctx.guild.id)

            channel_ids = (
                channels["default_chid"],
                channels["message_chid"],
                channels["join_leave_chid"],
                channels["member_chid"],
                channels["voice_chid"],
                channels["server_chid"],
            )
            failed = 0
            success = 0
            for channel in channel_ids:
                channel = self.bot.get_channel(channel)
                if isinstance(channel, discord.TextChannel):
                    try:
                        webhooks = await channel.webhooks()
                        for webhook in webhooks:
                            if webhook.user == ctx.me:
                                await webhook.delete()
                                success += 1
                    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                        failed += 1
            await ctx.send(
                "✅ **Successfully unset all logging channels!**"
                f"\n_Deleted {success} webhooks. {failed} failed to delete._"
            )

    @log.command(name="channels")
    @commands.has_permissions(manage_guild=True)
    async def log_channels(self, ctx: CustomContext):
        """Shows this server's logging channels"""
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument("This server doesn't have logging enabled.")
        channels = await self.bot.db.fetchrow("SELECT * FROM log_channels WHERE guild_id = $1", ctx.guild.id)
        embed = discord.Embed(
            title="Logging Channels",
            colour=discord.Colour.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        default = self.bot.get_channel(channels["default_chid"] or 1)
        message = self.bot.get_channel(channels["message_chid"] or 1)
        join_leave = self.bot.get_channel(channels["join_leave_chid"] or 1)
        member = self.bot.get_channel(channels["member_chid"] or 1)
        server = self.bot.get_channel(channels["server_chid"] or 1)
        voice = self.bot.get_channel(channels["voice_chid"] or 1)
        embed.description = (
            f"**Default channel:** {default.mention}"
            f"\n**Message events:** {message.mention if message else ''}"
            f"\n**Joining and Leaving:** {join_leave.mention if join_leave else ''}"
            f"\n**Member events:** {member.mention if member else ''}"
            f"\n**Server events:** {server.mention if server else ''}"
            f"\n**Voice events:** {voice.mention if voice else ''}"
            f"\n"
            f"\n_Channels not shown here will be_"
            f"\n_delivered to the default channel._"
        )
        loggings = self.bot.guild_loggings[ctx.guild.id]
        enabled = [x for x, y in set(loggings) if y is True]
        embed.set_footer(text=f"{len(enabled)}/{len(set(loggings))} events enabled.")
        await ctx.send(embed=embed)

    @log.command(name="disable-event", aliases=["disable_event", "de"])
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_disable_event(self, ctx, *, event: ValidEventConverter):
        """**Disables a logging event, which can be one of the following:**
        `message_delete`, `message_purge`, `message_edit`, `member_join`, `member_leave`, `member_update`, `user_ban`, `user_unban`, `user_update`, `invite_create`, `invite_delete`, `voice_join`, `voice_leave`, `voice_move`, `voice_mod`, `emoji_create`, `emoji_delete`, `emoji_update`, `sticker_create`, `sticker_delete`, `sticker_update`, `server_update`, `stage_open`, `stage_close`, `channel_create`, `channel_delete`, `channel_edit`, `role_create`, `role_delete`, `role_edit`

        You can either use underscore `_` or dash `-` when specifying the event.
        _Note that the command will attempt to auto-complete to the closest match, if not specified._
        """
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument("This server doesn't have logging enabled.")
        arg = getattr(self.bot.guild_loggings[ctx.guild.id], event, None)
        if arg is False:
            raise commands.BadArgument(f'❌ **|** **{str(event).replace("_", " ").title()} Events** are already disabled!')
        await self.bot.db.execute(
            f"UPDATE logging_events SET {event} = $2 WHERE guild_id = $1",
            ctx.guild.id,
            False,
        )
        setattr(self.bot.guild_loggings[ctx.guild.id], event, False)
        await ctx.send(f'✅ **|** Successfully disabled **{str(event).replace("_", " ").title()} Events**')

    @log.command(name="enable-event", aliases=["enable_event", "ee"])
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_enable_event(self, ctx: CustomContext, *, event: ValidEventConverter):
        """**Enables a logging event, which can be one of the following:**
        `message_delete`, `message_purge`, `message_edit`, `member_join`, `member_leave`, `member_update`, `user_ban`, `user_unban`, `user_update`, `invite_create`, `invite_delete`, `voice_join`, `voice_leave`, `voice_move`, `voice_mod`, `emoji_create`, `emoji_delete`, `emoji_update`, `sticker_create`, `sticker_delete`, `sticker_update`, `server_update`, `stage_open`, `stage_close`, `channel_create`, `channel_delete`, `channel_edit`, `role_create`, `role_delete`, `role_edit`

        You can either use underscore `_` or dash `-` when specifying the event.
        _Note that the command will attempt to auto-complete to the closest match, if not specified._
        """
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument("This server doesn't have logging enabled.")
        arg = getattr(self.bot.guild_loggings[ctx.guild.id], event, None)
        if arg is True:
            raise commands.BadArgument(f'❌ **|** **{str(event).replace("_", " ").title()} Events** are already enabled!')
        await self.bot.db.execute(
            f"UPDATE logging_events SET {event} = $2 WHERE guild_id = $1",
            ctx.guild.id,
            True,
        )
        setattr(self.bot.guild_loggings[ctx.guild.id], event, True)
        await ctx.send(f'✅ **|** Successfully enabled **{str(event).replace("_", " ").title()} Events**')

    @log.command(
        name="edit-channels",
        aliases=["edit_channels", "ec"],
        preview="https://i.imgur.com/FO9e9VC.gif",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_edit_channels(self, ctx):
        """Shows an interactive menu to modify the server's logging channels."""
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument("This server doesn't have logging enabled.")
        view = ChannelsView(ctx)
        await view.start()
        await view.wait()

    @commands.max_concurrency(1, commands.BucketType.guild)
    @log.command(name="events", aliases=["all-events", "ae"])
    @commands.has_permissions(manage_guild=True)
    async def log_all_events(self, ctx: CustomContext):
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument("This server doesn't have logging enabled.")
        await ctx.typing()
        events = self.bot.guild_loggings[ctx.guild.id]
        view = AllEvents(ctx, events)
        await view.start()
        await view.wait()

    @log.command(name="auto-setup")
    @commands.has_permissions(administrator=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.bot_has_guild_permissions(manage_channels=True, manage_webhooks=True)
    async def log_auto_setup(self, ctx: CustomContext):
        """Creates a Logging category, with channels for each event to be delivered.
        The channels would be the following (inside a logging category):
        `#join-leave-log`
        `#message-log`
        `#voice-log`
        `#member-log`
        `#server-log`
        """
        if ctx.guild in self.bot.log_channels:
            raise commands.BadArgument("This server already has Logging Set up!")
        c = await ctx.confirm(
            "**Do you want to proceed?**"
            "\nThis command will set up logging for you,"
            "\nBy creating the followinc category:"
            "\n"
            f"\n`#logging` (category)"
            f"\n- `#join-leave-log`"
            f"\n- `#message-log`"
            f"\n- `#voice-log`"
            f"\n- `#member-log`",
            delete_after_timeout=False,
            delete_after_cancel=False,
            delete_after_confirm=True,
        )
        if not c:
            return
        async with ctx.typing():
            try:
                over = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.me: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_channels=True,
                        manage_webhooks=True,
                    ),
                }
                avatar = await ctx.me.display_avatar.read()
                cat = await ctx.guild.create_category(name="logging", overwrites=over)
                join_leave_channel = await cat.create_text_channel(name="join-leave-log")
                join_leave_webhook = await join_leave_channel.create_webhook(name="DuckBot logging", avatar=avatar)
                message_channel = await cat.create_text_channel(name="message-log")
                message_webhook = await message_channel.create_webhook(name="DuckBot logging", avatar=avatar)
                voice_channel = await cat.create_text_channel(name="voice-log")
                voice_webhook = await voice_channel.create_webhook(name="DuckBot logging", avatar=avatar)
                member_channel = await cat.create_text_channel(name="member-log")
                member_webhook = await member_channel.create_webhook(name="DuckBot logging", avatar=avatar)
                server_channel = await cat.create_text_channel(name="server-log")
                server_webhook = await server_channel.create_webhook(name="DuckBot logging", avatar=avatar)
                self.bot.log_channels[ctx.guild.id] = self.bot.log_webhooks(
                    join_leave=join_leave_webhook.url,
                    server=server_webhook.url,
                    default=server_webhook.url,
                    message=message_webhook.url,
                    member=member_webhook.url,
                    voice=voice_webhook.url,
                )
                self.bot.guild_loggings[ctx.guild.id] = LoggingEventsFlags.all()
                await self.bot.db.execute(
                    "INSERT INTO guilds (guild_id) VALUES ($1) " "ON CONFLICT (guild_id) DO NOTHING",
                    ctx.guild.id,
                )
                await self.bot.db.execute(
                    """
                INSERT INTO log_channels(guild_id, default_channel, default_chid, message_channel, message_chid, 
                                         join_leave_channel, join_leave_chid, member_channel, member_chid,
                                         voice_channel, voice_chid, server_channel, server_chid) 
                                         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                    ON CONFLICT (guild_id) DO UPDATE SET
                                        default_channel = $2, default_chid = $3, message_channel = $4, message_chid = $5, 
                                        join_leave_channel = $6, join_leave_chid = $7, member_channel = $8, member_chid = $9,
                                        voice_channel = $10, voice_chid = $11, server_channel = $12, server_chid = $13; """,
                    ctx.guild.id,
                    server_webhook.url,
                    server_channel.id,
                    message_webhook.url,
                    message_channel.id,
                    join_leave_webhook.url,
                    join_leave_channel.id,
                    member_webhook.url,
                    member_channel.id,
                    voice_webhook.url,
                    voice_channel.id,
                    server_webhook.url,
                    server_channel.id,
                )
                await self.bot.db.execute(
                    "INSERT INTO logging_events(guild_id) VALUES ($1)" "ON CONFLICT (guild_id) DO NOTHING",
                    ctx.guild.id,
                )
                try:
                    embed = discord.Embed(
                        title="Successfully set up!",
                        colour=discord.Colour.blurple(),
                        description=f"{join_leave_channel.mention}"
                        f"\n{message_channel.mention}"
                        f"\n{voice_channel.mention}"
                        f"\n{server_channel.mention}",
                    )
                    await ctx.send(embed=embed, mention_author=True)
                except (discord.Forbidden, discord.HTTPException):
                    pass
            except discord.Forbidden:
                await ctx.send(
                    "For some reason, I didn't have the necessary permissions to do that."
                    "\nTry assigning me a role with `Administrator` permissions"
                )
            except discord.HTTPException:
                await ctx.send("Something went wrong, ups!")

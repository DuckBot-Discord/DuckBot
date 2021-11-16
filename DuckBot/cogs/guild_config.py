"""
MIT License
Copyright (c) 2020-2021 cyrus01337, XuaTheGrate
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

https://github.com/cyrus01337/invites/
"""

import asyncio
import collections
import contextlib
import datetime
import difflib
import operator
import random
import time
from types import SimpleNamespace
from typing import Dict, Optional
from collections import deque

import asyncpg.exceptions
import discord
import tabulate
from discord.ext import commands, tasks

from DuckBot import errors
from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.cogs.management import UnicodeEmoji
from DuckBot.helpers.helper import LoggingEventsFlags

default_message = "**{inviter}** just added **{user}** to **{server}** (They're the **{count}** to join)"

POLL_PERIOD = 25


def setup(bot: commands.Bot):
    bot.add_cog(GuildSettings(bot))


async def get_wh(channel: discord.TextChannel):
    if channel.permissions_for(channel.guild.me).manage_webhooks:
        webhooks = await channel.webhooks()
        for w in webhooks:
            if w.user == channel.guild.me:
                return w.url
        else:
            return (
                await channel.create_webhook(name='DuckBot Logging', avatar=await channel.guild.me.avatar.read())).url
    else:
        raise commands.BadArgument('Cannot create webhook!')


def make_ordinal(n):
    """
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    """
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return str(n) + suffix


class ChannelsView(discord.ui.View):
    def __init__(self, ctx: CustomContext):
        super().__init__()
        self.message: discord.Message = None
        self.ctx = ctx
        self.bot: DuckBot = ctx.bot
        self.lock = asyncio.Lock()
        self.valid_channels = ['default', 'message', 'member', 'join_leave', 'voice', 'server']

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji='♾', row=0)
    async def default(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send('Please send a channel to change the **Message Events Channel**')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for('message', check=check)
                if message.content == 'cancel':
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction('✅')
            channel_string = message.content
            if channel_string.lower() == 'cancel':
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        'UPDATE log_channels SET default_channel = $2, default_chid = $3 WHERE guild_id = $1',
                        self.ctx.guild.id, webhook_url, channel.id)
                    self.bot.update_log('default', webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send('Could not create a webhook in that channel!\n'
                                        'Do i have **Manage Webhooks** permissions there?')
                except discord.HTTPException:
                    await self.ctx.send('Something went wrong while creating a webhook...')
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji='📨', row=0)
    async def message(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send('Please send a channel to change the **Message Events Channel**')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for('message', check=check)
                if message.content == 'cancel':
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction('✅')
            channel_string = message.content
            if channel_string.lower() == 'cancel':
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        'UPDATE log_channels SET message_channel = $2, message_chid = $3 WHERE guild_id = $1',
                        self.ctx.guild.id, webhook_url, channel.id)
                    self.bot.update_log('message', webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send('Could not create a webhook in that channel!\n'
                                        'Do i have **Manage Webhooks** permissions there?')
                except discord.HTTPException:
                    await self.ctx.send('Something went wrong while creating a webhook...')
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji='👋', row=1)
    async def join_leave(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send('Please send a channel to change the **Join and Leave Events Channel**')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for('message', check=check)
                if message.content == 'cancel':
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction('✅')
            channel_string = message.content
            if channel_string.lower() == 'cancel':
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        'UPDATE log_channels SET join_leave_channel = $2, join_leave_chid = $3 WHERE guild_id = $1',
                        self.ctx.guild.id, webhook_url, channel.id)
                    self.bot.update_log('join_leave', webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send('Could not create a webhook in that channel!\n'
                                        'Do i have **Manage Webhooks** permissions there?')
                except discord.HTTPException:
                    await self.ctx.send('Something went wrong while creating a webhook...')
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji='👤', row=0)
    async def member(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send(
                'Please send a channel to change the **Member Events Channel**\nSend "cancel" to cancel')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for('message', check=check)
                if message.content == 'cancel':
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction('✅')
            channel_string = message.content
            if channel_string.lower() == 'cancel':
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        'UPDATE log_channels SET member_channel = $2, member_chid = $3 WHERE guild_id = $1',
                        self.ctx.guild.id, webhook_url, channel.id)
                    self.bot.update_log('member', webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send('Could not create a webhook in that channel!\n'
                                        'Do i have **Manage Webhooks** permissions there?')
                except discord.HTTPException:
                    await self.ctx.send('Something went wrong while creating a webhook...')
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji='⚙', row=1)
    async def server(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send('Please send a channel to change the **Server Events Channel**')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for('message', check=check)
                if message.content == 'cancel':
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction('✅')
            channel_string = message.content
            if channel_string.lower() == 'cancel':
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        'UPDATE log_channels SET server_channel = $2, server_chid = $3 WHERE guild_id = $1',
                        self.ctx.guild.id, webhook_url, channel.id)
                    self.bot.update_log('server', webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send('Could not create a webhook in that channel!\n'
                                        'Do i have **Manage Webhooks** permissions there?')
                except discord.HTTPException:
                    await self.ctx.send('Something went wrong while creating a webhook...')
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji='🎙', row=1)
    async def voice(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.defer()

        async with self.lock:
            button.style = discord.ButtonStyle.green
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            to_delete = []
            m = await self.ctx.send('Please send a channel to change the **Voice Events Channel**'
                                    '\n_Send "cancel" to cancel_')
            to_delete.append(m)

            def check(message: discord.Message):
                if message.channel == self.ctx.channel and message.author == self.ctx.author:
                    to_delete.append(message)
                    return True
                return False

            while True:
                message: discord.Message = await self.bot.wait_for('message', check=check)
                if message.content == 'cancel':
                    break
                else:
                    try:
                        channel = await commands.TextChannelConverter().convert(self.ctx, message.content)
                        break
                    except commands.ChannelNotFound:
                        pass

            await message.add_reaction('✅')
            channel_string = message.content
            if channel_string.lower() == 'cancel':
                pass
            else:
                try:
                    webhook_url = await get_wh(channel)
                    await self.bot.db.execute(
                        'UPDATE log_channels SET voice_channel = $2, voice_chid = $3 WHERE guild_id = $1',
                        self.ctx.guild.id, webhook_url, channel.id)
                    self.bot.update_log('voice', webhook_url, message.guild.id)
                except commands.ChannelNotFound:
                    pass
                except (commands.BadArgument, discord.Forbidden):
                    await self.ctx.send('Could not create a webhook in that channel!\n'
                                        'Do i have **Manage Webhooks** permissions there?')
                except discord.HTTPException:
                    await self.ctx.send('Something went wrong while creating a webhook...')
            await self.update_message()
            try:
                await self.ctx.channel.delete_messages(to_delete)
            except:
                pass

    @discord.ui.button(style=discord.ButtonStyle.red, label='stop', row=2)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.lock.locked():
            return await interaction.response.send_message('Can\'t do that while waiting for a message!',
                                                           ephemeral=True)
        await interaction.response.defer()
        await self.on_timeout()

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
            child.style = discord.ButtonStyle.grey
        await self.message.edit(view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id in (self.ctx.bot.owner_id, self.ctx.author.id):
            return True
        await interaction.response.send_message(f'This menu belongs to **{self.ctx.author}**, sorry! 💖',
                                                ephemeral=True)
        return False

    async def update_message(self, edit: bool = True):
        channels = await self.bot.db.fetchrow('SELECT * FROM log_channels WHERE guild_id = $1', self.ctx.guild.id)
        embed = discord.Embed(title='Logging Channels', colour=discord.Colour.blurple(),
                              timestamp=self.ctx.message.created_at)
        default = self.bot.get_channel(channels['default_chid'] or 1)
        message = self.bot.get_channel(channels['message_chid'] or 1)
        join_leave = self.bot.get_channel(channels['join_leave_chid'] or 1)
        member = self.bot.get_channel(channels['member_chid'] or 1)
        server = self.bot.get_channel(channels['server_chid'] or 1)
        voice = self.bot.get_channel(channels['voice_chid'] or 1)
        embed.description = f"**♾ Default channel:** {default.mention}" \
                            f"\n**📨 Message events:** {message.mention if message else ''}" \
                            f"\n**👋 Joining and Leaving:** {join_leave.mention if join_leave else ''}" \
                            f"\n**👤 Member events:** {member.mention if member else ''}" \
                            f"\n**⚙ Server events:** {server.mention if server else ''}" \
                            f"\n**🎙 Voice events:** {voice.mention if voice else ''}" \
                            f"\n" \
                            f"\n_Channels not shown here will be_" \
                            f"\n_delivered to the default channel._"
        loggings = self.bot.guild_loggings[self.ctx.guild.id]
        enabled = [x for x, y in set(loggings) if y is True]
        embed.set_footer(text=f'{len(enabled)}/{len(set(loggings))} events enabled.')
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


class ValidEventConverter(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):
        new = argument.replace('-', '_')
        all_events = dict(LoggingEventsFlags.all())
        if new in all_events:
            return new
        maybe_events = difflib.get_close_matches(argument, all_events)
        if maybe_events:
            c = await ctx.confirm(f'Did you mean... **`{maybe_events[0]}`**?', delete_after_confirm=True,
                                  delete_after_timeout=False,
                                  buttons=(
                                  ('☑', None, discord.ButtonStyle.blurple), ('🗑', None, discord.ButtonStyle.gray)))
            if c:
                return maybe_events[0]
            elif c is None:
                raise errors.NoHideout()
        raise commands.BadArgument(f'`{argument[0:100]}` is not a valid logging event.')


class GuildSettings(commands.Cog, name='Guild Settings'):
    """
    👋 Commands and stuff about logging, welcome channels, ect.
    """

    def __init__(self, bot: commands.Bot):
        self.bot: DuckBot = bot
        self._invites_ready = asyncio.Event()
        self._dict_filled = asyncio.Event()

        self.select_emoji = '⚙'
        self.select_brief = 'Manage Bot Settings, Like Prefix, Logs, etc.'

        self.bot.invites = {}
        self.bot.get_invite = self.get_invite
        self.bot.wait_for_invites = self.wait_for_invites

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        # wait until the bots internal cache is ready
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            fetched = await self.fetch_invites(guild)
            invites = self.bot.invites[guild.id] = fetched or {}

            if "VANITY_URL" in guild.features:
                with contextlib.suppress(discord.HTTPException):
                    vanity = await guild.vanity_invite()
                    invites["VANITY"] = invites[vanity.code] = vanity
        self.update_invite_expiry.start()
        self.delete_expired.start()

    def cog_unload(self):
        self.update_invite_expiry.cancel()
        self.delete_expired.cancel()

    async def update_rewards(self, *, guild: discord.Guild, reward_number: int, message: str = None,
                             role: discord.Role = None, reaction: str = None):
        if not any([message, role, reaction]):
            await self.bot.db.execute("DELETE FROM counting WHERE (guild_id, reward_number) = ($1, $2)", guild.id,
                                      reward_number)
            try:
                self.bot.counting_rewards[guild.id].remove(reward_number)
            except KeyError:
                pass
            return reward_number
        await self.bot.db.execute('INSERT INTO counting (guild_id, reward_number, reward_message, '
                                  'role_to_grant, reaction_to_add) VALUES ($1, $2, $3, $4, $5) '
                                  'ON CONFLICT (guild_id, reward_number) DO UPDATE SET '
                                  'reward_message = $3, role_to_grant = $4, reaction_to_add = $5',
                                  guild.id, reward_number, message, getattr(role, 'id', None), reaction)
        try:
            self.bot.counting_rewards[guild.id].add(reward_number)
        except KeyError:
            self.bot.counting_rewards[guild.id] = {reward_number}
        return reward_number

    @tasks.loop()
    async def delete_expired(self):
        if not self.bot.expiring_invites:
            await self._dict_filled.wait()
        invites = self.bot.expiring_invites
        expiry_time = min(invites.keys())
        inv = invites[expiry_time]
        sleep_time = expiry_time - (int(time.time()) - self.bot.last_update)
        self.bot.shortest_invite = expiry_time
        await asyncio.sleep(sleep_time)
        # delete invite from cache
        self.delete_invite(inv)
        # delete invite from expiring invite list
        # bot.shortest_invite is updated in update_invite_expiry
        # and since the expiring_invites dict is also updated
        # so the time goes down we use this instead
        self.bot.expiring_invites.pop(self.bot.shortest_invite, None)

    @delete_expired.before_loop
    async def wait_for_list(self):
        await self.wait_for_invites()

    @tasks.loop(minutes=POLL_PERIOD)
    async def update_invite_expiry(self):
        # flatten all the invites in the cache into one single list
        flattened = [invite for inner in self.bot.invites.values() for invite in inner.values()]
        # get current posix time
        current = time.time()
        self.bot.expiring_invites = {
            inv.max_age - int(current - inv.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()): inv
            for inv in flattened if inv.max_age != 0}

        exists = True

        # update self.bot.shortest_invite
        # so we can compare it with invites
        # that were just created
        try:  # self.bot.shortest_invite might not exist
            self.bot.shortest_invite = self.bot.shortest_invite - int(time.time() - self.bot.last_update)
        except AttributeError:
            exists = False

        if self.update_invite_expiry.current_loop == 0:
            # this needs to be updated before
            # setting self._invites_ready
            self.bot.last_update = int(current)
            self._invites_ready.set()
        # we need to check that expiring_invites
        # is truthy otherwise this conditional will
        # raise an error because we passed an
        # empty sequence to min()
        elif exists and self.bot.expiring_invites and self.bot.shortest_invite > min(self.bot.expiring_invites.keys()):
            # this conditional needs to run before we
            # update self._last_update
            self.delete_expired.restart()
            self.bot.last_update = int(current)
        else:
            # the last update needs to be updated regardless or
            # it will cause updates getting deleted from the cache
            # too early because the expiring_invites list will be
            # updated with new times but delete_expired will think
            # that the last update was ages ago and will deduct a huge
            # amount of seconds from the expiry time to form the sleep_time
            self.bot.last_update = int(current)
        # set the event so if the delete_expired
        # task is cancelled it will start again
        if self.bot.expiring_invites:
            self._dict_filled.set()
            self._dict_filled.clear()

    def delete_invite(self, invite: discord.Invite) -> None:
        entry_found = self.get_invites(invite.guild.id)
        entry_found.pop(invite.code, None)

    def get_invite(self, code: str) -> Optional[discord.Invite]:
        for invites in self.bot.invites.values():
            find = invites.get(code)

            if find:
                return find
        return None

    def get_invites(self, guild_id: int) -> Optional[Dict[str, discord.Invite]]:
        return self.bot.invites.get(guild_id, None)

    async def wait_for_invites(self) -> None:
        if not self._invites_ready.is_set():
            await self._invites_ready.wait()

    async def fetch_invites(self, guild: discord.Guild) -> Optional[Dict[str, discord.Invite]]:
        try:
            invites = await guild.invites()
        except discord.HTTPException:
            return None
        else:
            return {invite.code: invite for invite in invites}

    async def _schedule_deletion(self, guild: discord.Guild) -> None:
        seconds_passed = 0

        while seconds_passed < 300:
            seconds_passed += 1

            if guild in self.bot.guilds:
                return
            await asyncio.sleep(1)

        if guild not in self.bot.guilds:
            self.bot.invites.pop(guild.id, None)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        cached = self.bot.invites.get(invite.guild.id, None)
        if cached:
            cached[invite.code] = invite

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        self.delete_invite(invite)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        invites = self.bot.invites.get(channel.guild.id)

        if invites:
            for invite in list(invites.values()):
                # changed to use id because of doc warning
                if invite.channel.id == channel.id:
                    invites.pop(invite.code)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        invites = await self.fetch_invites(guild) or {}
        self.bot.invites[guild.id] = invites

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        # reload all invites in case they changed during
        # the time that the guilds were unavailable
        self.bot.invites[guild.id] = await self.fetch_invites(guild) or {}

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.id != self.bot.user.id:
            return
        if not before.guild_permissions.manage_channels and after.guild_permissions.manage_channels:
            self.bot.invites[before.guild.id] = await self.fetch_invites(before.guild) or {}
        if before.guild_permissions.manage_guild and not after.guild_permissions.manage_guild:
            self.bot.invites.pop(before.guild.id, None)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        self.bot.loop.create_task(self._schedule_deletion(guild))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        invites = await self.fetch_invites(member.guild)
        dispatched: bool = False
        if invites:
            # we sort the invites to ensure we are comparing
            # A.uses == A.uses
            invites = sorted(invites.values(), key=lambda i: i.code)
            cached = sorted(self.bot.invites[member.guild.id].values(),
                            key=lambda i: i.code)

            # zipping is the easiest way to compare each in order, and
            # they should be the same size? if we do it properly
            for old, new in zip(cached, invites):
                if old.uses < new.uses:
                    self.bot.invites[member.guild.id][old.code] = new
                    self.bot.dispatch("invite_update", member, new)
                    dispatched = True
                    break

        if dispatched is False:
            self.bot.dispatch("invite_update", member, None)

    # if you want to use this command you
    # might want to make a error handler
    # to handle commands.NoPrivateMessage
    @commands.guild_only()
    @commands.command(usage=None)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def invitestats(self, ctx: CustomContext, *, _=None, return_embed: bool = False, guild_id: int = None) -> \
    Optional[discord.Embed]:
        """Displays the top 10 most used invites in the guild, and the top 10 inviters."""
        max_table_length = 10
        # PEP8 + same code, more readability
        invites = self.bot.invites.get(guild_id or ctx.guild.id, None)

        # falsey check for None or {}
        if not invites:
            # if there is no invites send this information
            # in an embed and return
            if return_embed:
                embed = discord.Embed(
                    title="Something Went Wrong...",
                    description="No invites found."
                                "\nDo I have `Manage Server` permissions?",
                    colour=discord.Colour.red())
                return embed
            raise commands.BadArgument('I couldn\'t find any Invites. (try again?)')

        # if you got here there are invites in the cache
        if return_embed is not True:
            embed = discord.Embed(colour=discord.Colour.green(), title=f'{ctx.guild.name}\'s invite stats')
        else:
            embed = discord.Embed(colour=ctx.colour, title=f'{ctx.guild.name}', timestamp=ctx.message.created_at)
        # sort the invites by the amount of uses
        # by default this would make it in increasing
        # order so we pass True to the reverse kwarg
        invites = sorted(invites.values(), key=lambda i: i.uses, reverse=True)
        # if there are 10 or more invites in the cache we will
        # display 10 invites, otherwise display the amount
        # of invites
        amount = max_table_length if len(invites) >= max_table_length else len(invites)
        # list comp on the sorted invites and then
        # join it into one string with str.join
        description = f'**__Top server {amount} invites__**\n```py\n' + tabulate.tabulate(
            [(f'{i + 1}. [{invites[i].code if return_embed is False else "*"*(len(invites[i].code)-4)}] {invites[i].inviter.name}',
              f'{invites[i].uses}') for i in range(amount)],
            headers=['Invite', 'Uses']) + (
                          f'\n``` ___There are {len(invites) - max_table_length} more invites in this server.___\n' if len(
                              invites) > max_table_length else '\n```')

        inv = collections.defaultdict(int)
        for t in [(invite.inviter.name, invite.uses) for invite in invites]:
            inv[t[0]] += t[1]
        invites = dict(inv)
        invites = sorted(invites.items(), key=operator.itemgetter(1), reverse=True)
        value = max_table_length if len(invites) >= max_table_length else len(invites)
        table = tabulate.tabulate(invites[0:value], headers=['Inviter', 'Added'])

        description = description + f'\n**__Top server {value} inviters__**\n```\n' + table + '```' + \
                      (f' ___There are {len(invites) - max_table_length} more inviters in this server.___' if len(
                          invites) > max_table_length else '')

        if return_embed is True:
            description += 'Invite codes hidden for privacy reasons. See\nthe `invite-stats` command for invite codes.'

        embed.description = description

        if return_embed is True:
            embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
            return embed
        await ctx.send(embed=embed)

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def welcome(self, ctx: CustomContext):
        """
        Commands to manage the welcome message for this server.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @welcome.command(name='channel')
    async def welcome_channel(self, ctx: CustomContext, *, new_channel: discord.TextChannel = None):
        """
        Sets the channel where the welcome messages should be delivered to.
        Send it without the channel
        """
        channel = new_channel
        query = """
                INSERT INTO prefixes(guild_id, welcome_channel) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET welcome_channel = $2
                """
        if channel:
            if not channel.permissions_for(ctx.author).send_messages:
                raise commands.BadArgument("You can't send messages in that channel!")
            await self.bot.db.execute(query, ctx.guild.id, channel.id)
            self.bot.welcome_channels[ctx.guild.id] = channel.id
            message = await self.bot.db.fetchval("SELECT welcome_message FROM prefixes WHERE guild_id = $1",
                                                 ctx.guild.id)
            await ctx.send(f"Done! Welcome channel updated to {channel.mention} \n"
                           f"{'also, you can customize the welcome message with the `welcome message` command.' if not message else ''}")
        else:
            await self.bot.db.execute(query, ctx.guild.id, None)
            self.bot.welcome_channels[ctx.guild.id] = None
            await ctx.send("Done! cleared the welcome channel.")

    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @welcome.command(name="message")
    async def welcome_message(self, ctx: CustomContext, *, message: commands.clean_content):
        """
        Sets the welcome message for this server.

        **__Here are all available placeholders__**
        To use these placeholders, surround them in `{}`. For example: {user-mention}

        > **`server`** : returns the server's name (Server Name)
        > **`user`** : returns the user's name (Name)
        > **`full-user`** : returns the user's full name (Name#1234)
        > **`user-mention`** : will mention the user (@Name)
        > **`count`** : returns the member count of the server(4385)
        > **`ordinal`** : returns the ordinal member count of the server(4385th)
        > **`code`** : the invite code the member used to join(TdRfGKg8Wh) **\***
        > **`full-code`** : the full invite (discord.gg/TdRfGKg8Wh) **\***
        > **`full-url`** : the full url (<https://discord.gg/TdRfGKg8Wh>) **\***
        > **`inviter`** : returns the inviter's name (Name) *****
        > **`full-inviter`** : returns the inviter's full name (Name#1234) **\***
        > **`inviter-mention`** : returns the inviter's mention (@Name) **\***

        ⚠ These placeholders are __CASE SENSITIVE.__
        ⚠ Placeholders marked with ***** may not be populated when a member joins, like when a bot joins, or when a user is added by an integration.

        **🧐 Example:**
        `%PRE%welcome message Welcome to **{server}**, **{full-user}**!`
        **📤 Output when a user joins:**
        > Welcome to **Duck Hideout**, **LeoCx1000#9999**!
        """
        query = """
                INSERT INTO prefixes(guild_id, welcome_message) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET welcome_message = $2
                """

        member = ctx.author
        inviter = random.choice(ctx.guild.members)

        l = {'server': str(member.guild),
             'user': str(member.display_name),
             'full-user': str(member),
             'user-mention': str(member.mention),
             'count': str(member.guild.member_count),
             'ordinal': str(make_ordinal(member.guild.member_count)),
             'code': "discord-api",
             'full-code': "discord.gg/discord-api",
             'full-url': "https://discord.gg/discord-api",
             'inviter': str(inviter),
             'full-inviter': str(inviter if inviter else 'N/A'),
             'inviter-mention': str(inviter.mention if inviter else 'N/A')}

        if len(message) > 1000:
            raise commands.BadArgument(f"That welcome message is too long! ({len(message)}/1000)")

        try:
            str(message).format(**l)
        except KeyError as e:
            return await ctx.send(f'Unrecognised argument: `{e}`')

        await self.bot.db.execute(query, ctx.guild.id, message)

        return await ctx.send(f"**Welcome message updated to:**\n{message}")

    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @welcome.command(name='fake-message', aliases=['fake', 'test-message'])
    async def welcome_message_test(self, ctx: CustomContext):
        """ Sends a fake welcome message to test the one set using the `welcome message` command. """
        member = ctx.author
        message = await self.bot.db.fetchval("SELECT welcome_message FROM prefixes WHERE guild_id = $1",
                                             member.guild.id)
        message = message or default_message
        invite = SimpleNamespace(url='https://discord.gg/TdRfGKg8Wh',
                                 code='discord-api',
                                 inviter=random.choice(ctx.guild.members))

        l = {'server': str(member.guild),
             'user': str(member.display_name),
             'full-user': str(member),
             'user-mention': str(member.mention),
             'count': str(member.guild.member_count),
             'ordinal': str(make_ordinal(member.guild.member_count)),
             'code': str(invite.code),
             'full-code': f"discord.gg/{invite.code}",
             'full-url': str(invite.url),
             'inviter': str(((member.guild.get_member(
                 invite.inviter.id).display_name) or invite.inviter.name) if invite.inviter else 'N/A'),
             'full-inviter': str(invite.inviter if invite.inviter else 'N/A'),
             'inviter-mention': str(invite.inviter.mention if invite.inviter else 'N/A')}

        await ctx.send(message.format(**l), allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_invite_update(self, member, invite):
        try:
            channel = await self.bot.get_welcome_channel(member)
        except errors.NoWelcomeChannel:
            return
        message = await self.bot.db.fetchval("SELECT welcome_message FROM prefixes WHERE guild_id = $1",
                                             member.guild.id)
        message = message or default_message

        l = {'server': str(member.guild),
             'user': str(member.display_name),
             'full-user': str(member),
             'user-mention': str(member.mention),
             'count': str(member.guild.member_count),
             'ordinal': str(make_ordinal(member.guild.member_count)),
             'code': (str(invite.code) if invite else 'N/A'),
             'full-code': (f"discord.gg/{invite.code}" if invite else 'N/A'),
             'full-url': (str(invite) if invite else 'N/A'),
             'inviter': str(((member.guild.get_member(
                 invite.inviter.id).display_name) or invite.inviter.name)
                            if invite and invite.inviter else 'N/A'),
             'full-inviter': str(invite.inviter if invite and invite.inviter else 'N/A'),
             'inviter-mention': str(invite.inviter.mention if invite and invite.inviter else 'N/A')}

        await channel.send(message.format(**l))

    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, add_reactions=True)
    @commands.command(name='enable-suggestions', aliases=['enable_suggestions'])
    async def enable_suggestions(self, ctx: CustomContext,
                                 channel: discord.TextChannel,
                                 image_only: bool):
        """
        Enables "Suggestion mode" - which is, the bot will react with an upvote and downvote reaction, for people to vote.
        _It is recommended to use the `%PRE%slowmode <short_time>` command to accompany this one, as to not flood the channel with reactions.
        **Note:** If image-only is set to `yes`, the bot will delete all messages without attachments, and warn the user.
        """
        self.bot.suggestion_channels[channel.id] = image_only
        await self.bot.db.execute('INSERT INTO suggestions (channel_id, image_only) VALUES ($1, $2) ON CONFLICT '
                                  '(channel_id) DO UPDATE SET image_only = $2', channel.id, image_only)
        await ctx.send(f'💞 | **Enabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **{"disabled" if image_only is False else "enabled"}**.')

    @commands.has_permissions(manage_channels=True)
    @commands.command(name='disable-suggestions', aliases=['disable_suggestions'])
    async def disable_suggestions(self, ctx: CustomContext,
                                  channel: discord.TextChannel):
        """
        Disables "suggestion mode" for a channel.
        """
        try:
            self.bot.suggestion_channels.pop(channel.id)
        except KeyError:
            pass
        await self.bot.db.execute('DELETE FROM suggestions WHERE channel_id = $1', channel.id)
        await ctx.send(f'💞 | **Disabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **N/A**.')

    # Add dj role

    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    @commands.group(invoke_without_command=True, name='dj-role', aliases=['dj', 'dj_role'])
    async def dj_role(self, ctx: CustomContext, new_role: discord.Role = None):
        """
        Manages the current DJ role. If no role is specified, shows the current DJ role.
        """
        if ctx.invoked_subcommand is None:
            if new_role:
                await self.bot.db.execute(
                    "INSERT INTO prefixes(guild_id, dj_id) VALUES ($1, $2) "
                    "ON CONFLICT (guild_id) DO UPDATE SET dj_id = $2",
                    ctx.guild.id, new_role.id)

                return await ctx.send(f"Updated the dj role to {new_role.mention}!",
                                      allowed_mentions=discord.AllowedMentions().none())

            dj_role = await self.bot.db.fetchval('SELECT dj_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

            if not dj_role:
                return await ctx.send("This server doesn't have a DJ role!"
                                      "\nDo `help dj` for more commends")

            role = ctx.guild.get_role(int(dj_role))
            if not isinstance(role, discord.Role):
                return await ctx.send("This server doesn't have a DJ role!"
                                      "\nDo `help dj` for more commends")

            return await ctx.send(f"This server's DJ role is {role.mention}"
                                  "\nDo `help dj` for more commends",
                                  allowed_mentions=discord.AllowedMentions().none())

    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @dj_role.command(name="clear", aliases=["unset", "remove"])
    async def dj_remove(self, ctx: CustomContext):
        """
        Unsets the DJ role for the server.
        """
        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, dj_id) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET dj_id = $2",
            ctx.guild.id, None)

        return await ctx.send(f"Removed this server's DJ role!",
                              allowed_mentions=discord.AllowedMentions().none())

    # Disable DJ role requirement

    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @dj_role.command(name='all', aliases=['disable'])
    async def dj_all(self, ctx: CustomContext):
        """
        Makes everyone able to control the player
        """

        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, dj_id) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET dj_id = $2",
            ctx.guild.id, 1234)

        return await ctx.send(f"Everyone is the dj now! 💃"
                              "\nDo `help dj` for more commends",
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.group(invoke_without_command=True, aliases=['prefixes'])
    async def prefix(self, ctx: CustomContext) -> discord.Message:
        """ Lists all the bots prefixes. """
        prefixes = await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True)
        embed = discord.Embed(title="Here are my prefixes:",
                              description=ctx.me.mention + '\n' + '\n'.join(prefixes))
        embed.add_field(name="Available prefix commands:", value=f"```fix"
                                                                 f"\n{ctx.clean_prefix}{ctx.command} add"
                                                                 f"\n{ctx.clean_prefix}{ctx.command} remove"
                                                                 f"\n{ctx.clean_prefix}{ctx.command} clear"
                                                                 f"\n```")
        return await ctx.send(embed=embed)

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefix.command(name="add")
    async def prefixes_add(self, ctx: CustomContext,
                           new: str) -> discord.Message:
        """Adds a prefix to the bots prefixes.\nuse quotes to add spaces: %PRE%prefix \"duck \" """
        try:
            await self.bot.db.execute("INSERT INTO pre(guild_id, prefix) VALUES ($1, $2)", ctx.guild.id, new)
            self.bot.prefixes[ctx.guild.id] = await self.bot.fetch_prefixes(ctx.message)
            await ctx.send(f'✅ **|** Added `{new}` to my prefixes!')
        except asyncpg.exceptions.UniqueViolationError:
            return await ctx.send('⚠ **|** That is already one of my prefixes!')

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefix.command(name="remove", aliases=['delete'])
    async def prefixes_remove(self, ctx: CustomContext,
                              prefix: str) -> discord.Message:
        """Removes a prefix from the bots prefixes.\nuse quotes to add spaces: %PRE%prefix \"duck \" """

        old = list(await self.bot.get_pre(self.bot, ctx.message, raw_prefix=True))
        if prefix in old:
            await ctx.send(f"✅ **|** Successfully removed `{prefix}` from my prefixes!")
        else:
            await ctx.send('⚠ **|** That is not one of my prefixes!')
        await self.bot.db.execute('DELETE FROM pre WHERE (guild_id, prefix) = ($1, $2)', ctx.guild.id, prefix)
        self.bot.prefixes[ctx.guild.id] = await self.bot.fetch_prefixes(ctx.message)

    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    @prefix.command(name="clear", aliases=['delall'])
    async def prefixes_clear(self, ctx):
        """ Clears the bots prefixes, resetting it to default. """
        await self.bot.db.execute("DELETE FROM pre WHERE guild_id = $1", ctx.guild.id)
        self.bot.prefixes[ctx.guild.id] = self.bot.PRE
        return await ctx.send("✅ **|** Cleared prefixes!")

    # Add mute role
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole(self, ctx: CustomContext, new_role: discord.Role = None):
        """
        Sets the mute-role. If no role is specified, shows the current mute role.
        """
        if ctx.invoked_subcommand is None:
            if new_role:
                await self.bot.db.execute(
                    "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                    "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                    ctx.guild.id, new_role.id)

                return await ctx.send(f"Updated the muted role to {new_role.mention}!",
                                      allowed_mentions=discord.AllowedMentions().none())

            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                raise errors.MuteRoleNotFound

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                raise errors.MuteRoleNotFound

            return await ctx.send(f"This server's mute role is {role.mention}"
                                  f"\nChange it with the `muterole [new_role]` command",
                                  allowed_mentions=discord.AllowedMentions().none())

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @muterole.command(name="remove", aliases=["unset"])
    async def muterole_remove(self, ctx: CustomContext):
        """
        Unsets the mute role for the server,
        note that this will NOT delete the role, but only remove it from the bot's database!
        If you want to delete it, do "%PRE%muterole delete" instead
        """
        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
            ctx.guild.id, None)

        return await ctx.send(f"Removed this server's mute role!",
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @muterole.command(name="create")
    async def muterole_create(self, ctx: CustomContext):
        starting_time = time.monotonic()

        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

        if mute_role:
            mute_role = ctx.guild.get_role(mute_role)
            if mute_role:
                raise commands.BadArgument('You already have a mute role')

        await ctx.send(f"Creating Muted role, and applying it to all channels."
                       f"\nThis may take awhile ETA: {len(ctx.guild.channels)} seconds.")

        async with ctx.typing():
            permissions = discord.Permissions(send_messages=False,
                                              add_reactions=False,
                                              connect=False,
                                              speak=False)
            role = await ctx.guild.create_role(name="Muted", colour=0xff4040, permissions=permissions,
                                               reason=f"DuckBot mute-role creation. Requested "
                                                      f"by {ctx.author} ({ctx.author.id})")
            await self.bot.db.execute(
                "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                ctx.guild.id, role.id)

            modified = 0
            for channel in ctx.guild.channels:
                perms = channel.overwrites_for(role)
                perms.update(send_messages=None,
                             add_reactions=None,
                             create_public_threads=None,
                             create_private_threads=None
                             )
                try:
                    await channel.set_permissions(role, overwrite=perms,
                                                  reason=f"DuckBot mute-role creation. Requested "
                                                         f"by {ctx.author} ({ctx.author.id})")
                    modified += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
                await asyncio.sleep(1)

            ending_time = time.monotonic()
            complete_time = (ending_time - starting_time)
            await ctx.send(f"done! took {round(complete_time, 2)} seconds"
                           f"\nSet permissions for {modified} channel{'' if modified == 1 else 's'}!")

    @muterole.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole_delete(self, ctx: CustomContext):
        """
        Deletes the server's mute role if it exists.
        # If you want to keep the role but not
        """
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            raise errors.MuteRoleNotFound

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            await self.bot.db.execute(
                "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
                ctx.guild.id, None)

            return await ctx.send("It seems like the muted role was already deleted, or I can't find it right now!"
                                  "\n I removed it from my database. If the mute role still exists, delete it manually")

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to delete that role!")

        if role > ctx.author.top_role:
            return await ctx.send("You're not high enough in role hierarchy to delete that role!")

        try:
            await role.delete(reason=f"Mute role deletion. Requested by {ctx.author} ({ctx.author.id})")
        except discord.Forbidden:
            return await ctx.send("I can't delete that role! But I deleted it from my database")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while deleting the muted role!")
        await self.bot.db.execute(
            "INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
            "ON CONFLICT (guild_id) DO UPDATE SET muted_id = $2",
            ctx.guild.id, None)
        await ctx.send("🚮")

    @muterole.command(name="fix")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def muterole_fix(self, ctx: CustomContext):
        async with ctx.typing():
            starting_time = time.monotonic()
            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                raise errors.MuteRoleNotFound

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                raise errors.MuteRoleNotFound

            cnf = await ctx.confirm(
                f'Are you sure you want to change the permissions for **{role.name}** in all channels?')
            if not cnf:
                return

            modified = 0
            for channel in ctx.guild.channels:
                perms = channel.overwrites_for(role)
                perms.update(send_messages=False,
                             add_reactions=False,
                             connect=False,
                             speak=False,
                             create_public_threads=False,
                             create_private_threads=False,
                             send_messages_in_threads=False,
                             )
                try:
                    await channel.set_permissions(role, overwrite=perms,
                                                  reason=f"DuckBot mute-role creation. Requested "
                                                         f"by {ctx.author} ({ctx.author.id})")
                    modified += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
                await asyncio.sleep(1)

            ending_time = time.monotonic()
            complete_time = (ending_time - starting_time)
            await ctx.send(f"done! took {round(complete_time, 2)} seconds"
                           f"\nSet permissions for {modified} channel{'' if modified == 1 else 's'}!")

    @commands.group(aliases=['ct'])
    async def counting(self, ctx: CustomContext):
        """ Base command for setting up counting """
        if ctx.invoked_subcommand is None:
            p = ctx.clean_prefix
            embed = discord.Embed(title='How to set up counting',
                                  description='**__Counting is a fun game, where users count up in a channel.__**'
                                              '\nThis game can be as simple or complex as **you** want.'
                                              '\nIt has support for a **rewards system**, which will allow'
                                              '\nfor **special messages** when certain goals are achieved. Also'
                                              '\nsupport for adding **roles** to the user who reached that goal, or'
                                              '\nif that\'s too much for you, it can simply add a **reaction** to the'
                                              '\nmessage that reached the goal.'
                                              '\n'
                                              '\nHere are some configuration commands for setting up this game.'
                                              f'\n_PS: for more info do `{p}help counting`_'
                                              f'\n'
                                              f'\n`{p}ct set-channel <channel>`'
                                              f'\n`{p}ct unset-channel <channel>`'
                                              f'\n`{p}ct add-reward` *(interactive command)*'
                                              f'\n`{p}ct remove-reward <number>`'
                                              f'\n`{p}ct all-rewards`'
                                              f'\n`{p}ct check-reward <level>`'
                                              f'\n`{p}ct override-number <number>`')
            embed.set_footer(text='All sub-commands require Manage Server permission')
            return await ctx.send(embed=embed)

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='set-channel')
    async def ct_set_channel(self, ctx: CustomContext, channel: discord.TextChannel):
        """ Sets this server's count channel """
        try:
            await ctx.trigger_typing()
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await self.bot.db.execute('INSERT INTO prefixes (guild_id) VALUES ($1) '
                                      'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id)
            await self.bot.db.execute('INSERT INTO count_settings (guild_id, channel_id) VALUES ($1, $2)', ctx.guild.id,
                                      channel.id)
            self.bot.counting_channels[ctx.guild.id] = {'channel': channel.id,
                                                        'number': 0,
                                                        'last_counter': None,
                                                        'delete_messages': True,
                                                        'reset': False,
                                                        'last_message_id': None,
                                                        'messages': deque(maxlen=100)}
            await ctx.send(f'✅ **|** Set the **counting channel** to {channel.mention}')
        except asyncpg.UniqueViolationError:
            if (ctx.guild.id in self.bot.counting_channels and self.bot.counting_channels[ctx.guild.id][
                'channel'] != channel.id) or (ctx.guild.id not in self.bot.counting_channels):
                confirm = await ctx.confirm(
                    '⚠ **|** There is already a **counting channel**! Would you like to **update it** and reset the count number to **0**?',
                    return_message=True)
                if confirm[0] is True:
                    await self.bot.db.execute('INSERT INTO prefixes (guild_id) VALUES ($1) '
                                              'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id)
                    await self.bot.db.execute(
                        'INSERT INTO count_settings (guild_id, channel_id, current_number) VALUES ($1, $2, 1)'
                        'ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, current_number = 0',
                        ctx.guild.id, channel.id)
                    try:
                        self.bot.counting_channels[ctx.guild.id]['channel'] = channel.id
                        self.bot.counting_channels[ctx.guild.id]['number'] = 0
                        self.bot.counting_channels[ctx.guild.id]['last_counter'] = None
                        self.bot.counting_channels[ctx.guild.id]['messages'] = deque(maxlen=100)
                    except KeyError:
                        self.bot.counting_channels[ctx.guild.id] = {'channel': channel.id, 'number': 0,
                                                                    'last_counter': None, 'delete_messages': True,
                                                                    'reset': False, 'last_message_id': None,
                                                                    'messages': deque(maxlen=100)}
                    await confirm[1].edit(
                        content='✅ **|** Updated the **counting channel** and reset the current number to **0**',
                        view=None)
                else:
                    await confirm[1].edit(content='❌ **|** Cancelled!', view=None)
            else:
                await ctx.send(f'⚠ **|** {channel.mention} is already the **counting channel**!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='unset-channel')
    async def ct_unset_channel(self, ctx: CustomContext):
        """ Unsets this server's counting channel """
        if ctx.guild.id in self.bot.counting_channels:
            confirm = await ctx.confirm('⚠ **|** Are you sure you **unset** the **counting channel**?',
                                        return_message=True)
            if confirm[0] is True:
                self.bot.counting_channels.pop(ctx.guild.id)
                await self.bot.db.execute('DELETE FROM count_settings WHERE guild_id = $1', ctx.guild.id)
                await confirm[1].edit(content='✅ **|** **Unset** this server\'s **counting channel**!', view=None)
            else:
                await confirm[1].edit(content='❌ **|** Cancelled!', view=None)
        else:
            await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='add-reward')
    async def ct_add_reward(self, ctx: CustomContext):
        """ An interactive way to add a reward to the counting game. """

        def check(m: discord.Message):
            return m.channel == ctx.channel and m.author == ctx.author

        def int_check(m: discord.Message):
            return m.channel == ctx.channel and m.author == ctx.author and m.content.isdigit()

        try:
            await ctx.send('1️⃣ **|** What **number** would this reward be assigned to?')
            number = int((await self.bot.wait_for('message', check=int_check, timeout=120)).content)

            await ctx.send(
                '2️⃣ **|** What **message** would you want to be sent to the channel when this number is reached?'
                '\nℹ **|** Type `skip` to skip, and `cancel` to cancel')
            message = (await self.bot.wait_for('message', check=check, timeout=120)).content
            if message.lower() == 'cancel':
                return
            message = message if message.lower() != 'skip' else None

            await ctx.send(
                '3️⃣ **|** What **role** would you want to be assigned to the person who reached this number?'
                '\nℹ **|** Type `skip` to skip, and `cancel` to cancel')
            role = False
            while role is False:
                role = (await self.bot.wait_for('message', check=check, timeout=120)).content
                if role.lower() == 'cancel':
                    return
                try:
                    role = await commands.RoleConverter().convert(ctx, role) if role.lower() != 'skip' else None
                except commands.RoleNotFound:
                    role = False

            await ctx.send('4️⃣ **|** What **reaction** would you like to be added to the message?'
                           '\nℹ **|** Type `skip` to skip, and `cancel` to cancel')
            emoji = False
            while emoji is False:
                emoji = (await self.bot.wait_for('message', check=check, timeout=120)).content
                if emoji.lower() == 'cancel':
                    return
                try:
                    emoji = str((await UnicodeEmoji().convert(ctx, emoji)) or (
                        await commands.EmojiConverter().convert(ctx, emoji))) if emoji.lower() != 'skip' else None
                    if isinstance(emoji, discord.Emoji) and not emoji.is_usable():
                        emoji = None
                except commands.EmojiNotFound:
                    emoji = False

            try:
                if number in self.bot.counting_rewards[ctx.guild.id]:
                    confirm = await ctx.confirm(
                        f'⚠ **|** **{number} has already a reward associated with it, would you like to overwrite it?',
                        delete_after_confirm=True, delete_after_timeout=False, delete_after_cancel=False)
                    if confirm is False:
                        return
            except KeyError:
                pass

            await self.update_rewards(guild=ctx.guild, reward_number=number, message=message, role=role, reaction=emoji)
            await ctx.send(f'✅ **|** Added **reward** for number **{number}**')

        except asyncio.TimeoutError:
            return await ctx.send('⚠ **|** Timed out! Please try again.')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='remove-reward')
    async def ct_remove_reward(self, ctx: CustomContext, number: int):
        """ Removes one of the counting rewards """
        if ctx.guild.id not in self.bot.counting_rewards:
            return await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')
        if number in self.bot.counting_rewards[ctx.guild.id]:
            confirm = await ctx.confirm(
                f'⚠ **|** would you like to remove **{number}** from the rewards?',
                return_message=True)

            if confirm[0] is False:
                return await confirm[1].edit(content='❌ **|** Cancelled!', view=None)

            try:
                self.bot.counting_rewards[ctx.guild.id].remove(number)
            except KeyError:
                pass
            await self.bot.db.execute('DELETE FROM counting WHERE (guild_id, reward_number) = ($1, $2)', ctx.guild.id,
                                      number)
        else:
            await ctx.send('⚠ **|** That is not one of the **counting rewards**!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='all-rewards')
    async def ct_all_rewards(self, ctx: CustomContext):
        """ [unavailable] Shows all the counting rewards """
        await ctx.send('WIP - coming soon!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='check-reward')
    async def ct_check_reward(self, ctx: CustomContext, number: int):
        """ [unavailable] Checks a number to see if it is assigned to a reward """
        await ctx.send('WIP - coming soon!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='override-number')
    async def ct_override_number(self, ctx: CustomContext, number: int):
        """ Sets this server's current count number in case it breaks somehow """
        if ctx.guild.id in self.bot.counting_channels:
            if number < 0:
                raise commands.BadArgument('⚠ **|** **Number** must be greater or equal to **0**')
            confirm = await ctx.confirm(f'⚠ **|** Are you sure you **set** the **counting number** to **{number}**?',
                                        return_message=True)
            if confirm[0] is True:
                self.bot.counting_channels[ctx.guild.id]['number'] = number
                await self.bot.db.execute('UPDATE count_settings SET current_number = $2 WHERE guild_id = $1',
                                          ctx.guild.id, number)
                await confirm[1].edit(content=f'✅ **|** Updated the **counting number** to **{number}**. '
                                              f'\nℹ **|** The next number will be **{number + 1}**', view=None)
        else:
            await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')

    ##############################
    @commands.group(aliases=['logging', 'logger'])
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log(self, ctx: CustomContext):
        """Base command to manage the logging events.

        Run this command without sub-commands to show more detailed information on the logging module"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title='DuckBot Logging Module', colour=discord.Colour.yellow(),
                                  description='**What is this?**\n'
                                              'The Logging module is a fully customizable logger for different server events. '
                                              'It can be configured to log up to 30 unique events, and for those events to be '
                                              'delivered into 5 different channels.\n'
                                              '**Available commands:**\n'
                                              f'\n`{ctx.clean_prefix}log enable <channel>` Enables logging for this server.'
                                              f'\n`{ctx.clean_prefix}log disable` Disables logging for this server.'
                                              f'\n`{ctx.clean_prefix}log channels` Shows the current channel settings.'
                                              f'\n`{ctx.clean_prefix}log edit-channels` Modifies the log channels (interactive menu).'
                                              f'\n`{ctx.clean_prefix}log all-events` Shows all events, disabled and enabled.'
                                              f'\n`{ctx.clean_prefix}log enable-event <event>` Enables a specific event from the list.'
                                              f'\n`{ctx.clean_prefix}log disable-event <event>` Disables a specific event from the list.'
                                              f'\n`{ctx.clean_prefix}log auto-setup` Creates a logging category with different channels.'
                                              f'\n'
                                              f'\nFor more info on a specific command, run the `help` command with it, E.G:'
                                              f'\n`db.help log enable-event`')
            await ctx.send(embed=embed)

    @log.command(name='enable', aliases=['set-default'], preview='https://i.imgur.com/SYOrcfG.gif')
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_enable(self, ctx: CustomContext, channel: discord.TextChannel):
        """Enables the logging module to deliver to one channel.

        If logging is already enabled, it will set the default logging channel to the one specified.
        _Note: This will not modify your enabled/disabled events, if any._"""
        if ctx.guild.id in self.bot.log_channels:
            raise commands.BadArgument('This server already has a logging enabled.')
        if not channel.permissions_for(ctx.me).manage_webhooks and not channel.permissions_for(ctx.me).send_messages:
            raise commands.BadArgument(f"I'm missing the Manage Webhooks permission in {channel.mention}")
        await ctx.trigger_typing()

        try:
            webhooks = await channel.webhooks()
        except (discord.Forbidden, discord.HTTPException):
            raise commands.BadArgument(
                f'I was unable to get the list of webhooks in {channel.mention}. (Missing Permissions - Manage Webhooks)')
        for w in webhooks:
            if w.user == self.bot.user:
                webhook_url = w.url
                break
        else:
            if len(webhooks) == 10:
                raise commands.BadArgument(f'{channel.mention} has already the max number of webhooks! (10 webhooks)')
            try:
                w = await channel.create_webhook(name='DuckBot logging', avatar=await ctx.me.avatar.read(),
                                                 reason='DuckBot logging')
                webhook_url = w.url
            except discord.Forbidden:
                raise commands.BadArgument(
                    f'I couldn\'t create a webhook in {channel.mention}(Missing Permissions - Manage Webhooks)')
            except discord.HTTPException:
                raise commands.BadArgument(
                    f'There was an unexpected error while creating a webhook in {channel.mention} (HTTP exception) - Perhaps try again?')
        await self.bot.db.execute('INSERT INTO prefixes (guild_id) VALUES ($1) '
                                  'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id)
        await self.bot.db.execute(
            "INSERT INTO log_channels(guild_id, default_channel, default_chid) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id) DO UPDATE SET default_channel = $2, default_chid = $3",
            ctx.guild.id, webhook_url, channel.id)
        await self.bot.db.execute("INSERT INTO logging_events(guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
                                  ctx.guild.id)
        self.bot.guild_loggings[ctx.guild.id] = LoggingEventsFlags.all()
        try:
            self.bot.log_channels[ctx.guild.id]._replace(default=webhook_url)
        except KeyError:
            self.bot.log_channels[ctx.guild.id] = self.bot.log_webhooks(default=webhook_url, voice=None, message=None,
                                                                        member=None, server=None, join_leave=None)
        await ctx.send(f'Successfully set the logging channel to {channel.mention}'
                       f'\n_see `{ctx.clean_prefix}help log` for more customization commands!_')

    @log.command(name='disable', aliases=['disable-logging'])
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_disable(self, ctx: CustomContext):
        """Disables logging for this server, and deletes all the bots logging webhooks."""
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument('Logging is not enabled for this server!')
        confirm = await ctx.confirm('**Are you sure you want to disable logging?**'
                                    '\nThis will overwrite and disable **all** delivery channels, and delete all my webhooks.',
                                    delete_after_confirm=True, delete_after_timeout=False)
        if not confirm:
            return
        async with ctx.typing():
            try:
                self.bot.log_channels.pop(ctx.guild.id)
            except KeyError:
                pass
            channels = await self.bot.db.fetchrow('DELETE FROM log_channels WHERE guild_id = $1 RETURNING *',
                                                  ctx.guild.id)

            channel_ids = channels['default_chid'], channels['message_chid'], channels['join_leave_chid'], channels[
                'member_chid'], channels['voice_chid'], channels['server_chid']
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
            await ctx.send('✅ **Successfully unset all logging channels!**'
                           f'\n_Deleted {success} webhooks. {failed} failed to delete._')

    @log.command(name='channels')
    @commands.has_permissions(manage_guild=True)
    async def log_channels(self, ctx: CustomContext):
        """Shows this server's logging channels"""
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument('This server doesn\'t have logging enabled.')
        channels = await self.bot.db.fetchrow('SELECT * FROM log_channels WHERE guild_id = $1', ctx.guild.id)
        embed = discord.Embed(title='Logging Channels', colour=discord.Colour.blurple(),
                              timestamp=discord.utils.utcnow())
        default = self.bot.get_channel(channels['default_chid'] or 1)
        message = self.bot.get_channel(channels['message_chid'] or 1)
        join_leave = self.bot.get_channel(channels['join_leave_chid'] or 1)
        member = self.bot.get_channel(channels['member_chid'] or 1)
        server = self.bot.get_channel(channels['server_chid'] or 1)
        voice = self.bot.get_channel(channels['voice_chid'] or 1)
        embed.description = f"**Default channel:** {default.mention}" \
                            f"\n**Message events:** {message.mention if message else ''}" \
                            f"\n**Joining and Leaving:** {join_leave.mention if join_leave else ''}" \
                            f"\n**Member events:** {member.mention if member else ''}" \
                            f"\n**Server events:** {server.mention if server else ''}" \
                            f"\n**Voice events:** {voice.mention if voice else ''}" \
                            f"\n" \
                            f"\n_Channels not shown here will be_" \
                            f"\n_delivered to the default channel._"
        loggings = self.bot.guild_loggings[ctx.guild.id]
        enabled = [x for x, y in set(loggings) if y is True]
        embed.set_footer(text=f'{len(enabled)}/{len(set(loggings))} events enabled.')
        await ctx.send(embed=embed)

    @log.command(name='disable-event', aliases=['disable_event', 'de'])
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_disable_event(self, ctx, *, event: ValidEventConverter):
        """**Disables a logging event, which can be one of the following:**
        `message_delete`, `message_purge`, `message_edit`, `member_join`, `member_leave`, `member_update`, `user_ban`, `user_unban`, `user_update`, `invite_create`, `invite_delete`, `voice_join`, `voice_leave`, `voice_move`, `voice_mod`, `emoji_create`, `emoji_delete`, `emoji_update`, `sticker_create`, `sticker_delete`, `sticker_update`, `server_update`, `stage_open`, `stage_close`, `channel_create`, `channel_delete`, `channel_edit`, `role_create`, `role_delete`, `role_edit`

        You can either use underscore `_` or dash `-` when specifying the event.
        _Note that the command will attempt to auto-complete to the closest match, if not specified._
        """
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument('This server doesn\'t have logging enabled.')
        arg = getattr(self.bot.guild_loggings[ctx.guild.id], event, None)
        if arg is False:
            raise commands.BadArgument(
                f'❌ **|** **{str(event).replace("_", " ").title()} Events** are already disabled!')
        await self.bot.db.execute(f'UPDATE logging_events SET {event} = $2 WHERE guild_id = $1',
                                  ctx.guild.id, False)
        setattr(self.bot.guild_loggings[ctx.guild.id], event, False)
        await ctx.send(f'✅ **|** Successfully disabled **{str(event).replace("_", " ").title()} Events**')

    @log.command(name='enable-event', aliases=['enable_event', 'ee'])
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_enable_event(self, ctx: CustomContext, *, event: ValidEventConverter):
        """**Enables a logging event, which can be one of the following:**
        `message_delete`, `message_purge`, `message_edit`, `member_join`, `member_leave`, `member_update`, `user_ban`, `user_unban`, `user_update`, `invite_create`, `invite_delete`, `voice_join`, `voice_leave`, `voice_move`, `voice_mod`, `emoji_create`, `emoji_delete`, `emoji_update`, `sticker_create`, `sticker_delete`, `sticker_update`, `server_update`, `stage_open`, `stage_close`, `channel_create`, `channel_delete`, `channel_edit`, `role_create`, `role_delete`, `role_edit`

        You can either use underscore `_` or dash `-` when specifying the event.
        _Note that the command will attempt to auto-complete to the closest match, if not specified._
        """
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument('This server doesn\'t have logging enabled.')
        arg = getattr(self.bot.guild_loggings[ctx.guild.id], event, None)
        if arg is True:
            raise commands.BadArgument(
                f'❌ **|** **{str(event).replace("_", " ").title()} Events** are already enabled!')
        await self.bot.db.execute(f'UPDATE logging_events SET {event} = $2 WHERE guild_id = $1',
                                  ctx.guild.id, True)
        setattr(self.bot.guild_loggings[ctx.guild.id], event, True)
        await ctx.send(f'✅ **|** Successfully enabled **{str(event).replace("_", " ").title()} Events**')

    @log.command(name='edit-channels', aliases=['edit_channels', 'ec'], preview='https://i.imgur.com/FO9e9VC.gif')
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def log_edit_channels(self, ctx):
        """Shows an interactive menu to modify the server's logging channels."""
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument('This server doesn\'t have logging enabled.')
        view = ChannelsView(ctx)
        await view.start()
        await view.wait()

    @log.command(name='all-events')
    @commands.has_permissions(manage_guild=True)
    async def log_all_events(self, ctx: CustomContext):
        if ctx.guild.id not in self.bot.log_channels:
            raise commands.BadArgument('This server doesn\'t have logging enabled.')
        await ctx.trigger_typing()
        events = self.bot.guild_loggings[ctx.guild.id]
        embed = discord.Embed(title='Logging events for this server', colour=discord.Colour.blurple(),
                              timestamp=ctx.message.created_at)
        message_events = [ctx.default_tick(events.message_delete, 'Message Delete'),
                          ctx.default_tick(events.message_edit, 'Message Edit'),
                          ctx.default_tick(events.message_purge, 'Message Purge')]
        embed.add_field(name='Message Events', value='\n'.join(message_events))
        join_leave_events = [ctx.default_tick(events.member_join, 'Member Join'),
                             ctx.default_tick(events.member_leave, 'Member Leave')]
        subtract = 0
        if not ctx.me.guild_permissions.manage_channels:
            if events.invite_create:
                join_leave_events.append('⚠ Invite Create'
                                         '\n╰ Manage Channels')
                subtract += 1
            else:
                join_leave_events.append(ctx.default_tick(events.invite_create, 'Invite Create'))
            if events.invite_delete:
                join_leave_events.append('⚠ Invite Delete'
                                         '\n╰ Manage Channels')
                subtract += 1
            else:
                join_leave_events.append(ctx.default_tick(events.invite_delete, 'Invite Create'))
        else:
            join_leave_events.append(ctx.default_tick(events.invite_create, 'Invite Create'))
            join_leave_events.append(ctx.default_tick(events.invite_delete, 'Invite Delete'))
        embed.add_field(name='Join Leave Events', value='\n'.join(join_leave_events))
        member_update_evetns = [ctx.default_tick(events.member_update, 'Member Update'),
                                ctx.default_tick(events.user_update, 'User Update'),
                                ctx.default_tick(events.user_ban, 'User Ban'),
                                ctx.default_tick(events.user_unban, 'User Unban')]
        embed.add_field(name='Member Events', value='\n'.join(member_update_evetns))
        voice_events = [ctx.default_tick(events.voice_join, 'Voice Join'),
                        ctx.default_tick(events.voice_leave, 'Voice Leave'),
                        ctx.default_tick(events.voice_move, 'Voice Move'),
                        ctx.default_tick(events.voice_mod, 'Voice Mod'),
                        ctx.default_tick(events.stage_open, 'Stage Open'),
                        ctx.default_tick(events.stage_close, 'Stage Close')]
        embed.add_field(name='Voice Events', value='\n'.join(voice_events))
        server_events = [ctx.default_tick(events.channel_create, 'Channel Create'),
                         ctx.default_tick(events.channel_delete, 'Channel Delete'),
                         ctx.default_tick(events.channel_edit, 'Channel Edit'),
                         ctx.default_tick(events.role_create, 'Role Create'),
                         ctx.default_tick(events.role_delete, 'Role Delete'),
                         ctx.default_tick(events.role_edit, 'Role Edit'),
                         ctx.default_tick(events.server_update, 'Server Update'),
                         ctx.default_tick(events.emoji_create, 'Emoji Create'),
                         ctx.default_tick(events.emoji_delete, 'Emoji Delete'),
                         ctx.default_tick(events.emoji_update, 'Emoji Update'),
                         ctx.default_tick(events.sticker_create, 'Sticker Create'),
                         ctx.default_tick(events.sticker_delete, 'Sticker Delete'),
                         ctx.default_tick(events.sticker_update, 'Sticker Update')]
        embed.add_field(name='Server Events', value='\n'.join(server_events))
        embed.description = '✅ Enabled • ❌ Disabled • ⚠ Missing Perms'
        enabled = [x for x, y in set(events) if y is True]
        amount_enabled = len(enabled) - subtract
        embed.set_footer(text=f'{amount_enabled}/{len(set(events))} events enabled.')
        await ctx.send(embed=embed)

    @log.command(name='auto-setup')
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
            raise commands.BadArgument('This server already has Logging Set up!')
        c = await ctx.confirm('**Do you want to proceed?**'
                              '\nThis command will set up logging for you,'
                              '\nBy creating the followinc category:'
                              '\n'
                              f'\n`#logging` (category)'
                              f'\n- `#join-leave-log`'
                              f'\n- `#message-log`'
                              f'\n- `#voice-log`'
                              f'\n- `#member-log`',
                              delete_after_timeout=False, delete_after_cancel=False, delete_after_confirm=True)
        if not c:
            return
        async with ctx.typing():
            try:
                over = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        ctx.me: discord.PermissionOverwrite(read_messages=True, send_messages=True,
                                                            manage_channels=True, manage_webhooks=True)}
                avatar = await ctx.me.avatar.read()
                cat = await ctx.guild.create_category(name='logging', overwrites=over)
                join_leave_channel = await cat.create_text_channel(name='join-leave-log')
                join_leave_webhook = await join_leave_channel.create_webhook(name='DuckBot logging', avatar=avatar)
                message_channel = await cat.create_text_channel(name='message-log')
                message_webhook = await message_channel.create_webhook(name='DuckBot logging', avatar=avatar)
                voice_channel = await cat.create_text_channel(name='voice-log')
                voice_webhook = await voice_channel.create_webhook(name='DuckBot logging', avatar=avatar)
                member_channel = await cat.create_text_channel(name='member-log')
                member_webhook = await member_channel.create_webhook(name='DuckBot logging', avatar=avatar)
                server_channel = await cat.create_text_channel(name='server-log')
                server_webhook = await server_channel.create_webhook(name='DuckBot logging', avatar=avatar)
                self.bot.log_channels[ctx.guild.id] = self.bot.log_webhooks(join_leave=join_leave_webhook.url,
                                                                            server=server_webhook.url,
                                                                            default=server_webhook.url,
                                                                            message=message_webhook.url,
                                                                            member=member_webhook.url,
                                                                            voice=voice_webhook.url)
                self.bot.guild_loggings[ctx.guild.id] = LoggingEventsFlags.all()
                await self.bot.db.execute('INSERT INTO prefixes (guild_id) VALUES ($1) '
                                          'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id)
                await self.bot.db.execute("""
                INSERT INTO log_channels(guild_id, default_channel, default_chid, message_channel, message_chid, 
                                         join_leave_channel, join_leave_chid, member_channel, member_chid,
                                         voice_channel, voice_chid, server_channel, server_chid) 
                                         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                    ON CONFLICT (guild_id) DO UPDATE SET
                                        default_channel = $2,
                                        default_chid = $3,
                                        message_channel = $4,
                                        message_chid = $5,
                                        join_leave_channel = $6,
                                        join_leave_chid = $7,
                                        member_channel = $8,
                                        member_chid = $9,
                                        voice_channel = $10,
                                        voice_chid = $11,
                                        server_channel = $12,
                                        server_chid = $13; """,
                                          ctx.guild.id, server_webhook.url, server_channel.id,
                                          message_webhook.url, message_channel.id,
                                          join_leave_webhook.url, join_leave_channel.id,
                                          member_webhook.url, member_channel.id,
                                          voice_webhook.url, voice_channel.id,
                                          server_webhook.url, server_channel.id)
                await self.bot.db.execute('INSERT INTO logging_events(guild_id) VALUES ($1)'
                                          'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id)
                try:
                    embed = discord.Embed(title='Successfully set up!', colour=discord.Colour.blurple(),
                                          description=f"{join_leave_channel.mention}"
                                                      f"\n{message_channel.mention}"
                                                      f"\n{voice_channel.mention}"
                                                      f"\n{server_channel.mention}")
                    await ctx.send(embed=embed, mention_author=True)
                except (discord.Forbidden, discord.HTTPException):
                    pass
            except discord.Forbidden:
                await ctx.send('For some reason, I didn\'t have the necessary permissions to do that.'
                               '\nTry assigning me a role with `Administrator` permissions')
            except discord.HTTPException:
                await ctx.send('Something went wrong, ups!')

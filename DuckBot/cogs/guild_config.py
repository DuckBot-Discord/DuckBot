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

default_message = "**{inviter}** just added **{user}** to **{server}** (They're the **{count}** to join)"

POLL_PERIOD = 25


def setup(bot: commands.Bot):
    bot.add_cog(GuildSettings(bot))


class GuildSettings(commands.Cog, name='Guild Settings'):
    """
    👋 Commands and stuff about logging, welcome channels, ect.
    """

    def __init__(self, bot: commands.Bot):
        self.bot: DuckBot = bot
        self._invites_ready = asyncio.Event()
        self._dict_filled = asyncio.Event()

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
                self.bot.counting_rewards[guild.id]['rewards'].remove(reward_number)
            except KeyError:
                pass
            return reward_number
        await self.bot.db.execute('INSERT INTO counting (guild_id, reward_number, reward_message, '
                                  'role_to_grant, reaction_to_add) VALUES ($1, $2, $3, $4, $5) '
                                  'ON CONFLICT (guild_id, reward_number) DO UPDATE SET '
                                  'reward_message = $3, role_to_grant = $4, reaction_to_add = $5',
                                  guild.id, reward_number, message, getattr(role, 'id', None), reaction)
        try:
            self.bot.counting_rewards[guild.id]['rewards'].add(reward_number)
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
        print(f"created invite {invite} in {invite.guild}")
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
    @commands.command()
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def invitestats(self, ctx: CustomContext):
        """Displays the top 10 most used invites in the guild, and the top 10 inviters."""
        max_table_length = 10
        # PEP8 + same code, more readability
        invites = self.bot.invites.get(ctx.guild.id, None)

        # falsey check for None or {}
        if not invites:
            # if there is no invites send this information
            # in an embed and return
            raise commands.BadArgument('I couldn\'t find any Invites. (try again?)')

        # if you got here there are invites in the cache
        embed = discord.Embed(colour=discord.Colour.green(), title=f'{ctx.guild.name}\'s invite stats')
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
            [(f'{i + 1}. [{invites[i].code}] {invites[i].inviter.name}', f'{invites[i].uses}') for i in range(amount)],
            headers=['Invite', 'Uses']) + (f'\n``` ___There are {len(invites) - max_table_length} more invites in this server.___\n' if len(invites) > max_table_length else '\n```')

        inv = collections.defaultdict(int)
        for t in [(invite.inviter.name, invite.uses) for invite in invites]:
            inv[t[0]] += t[1]
        invites = dict(inv)
        invites = sorted(invites.items(), key=operator.itemgetter(1), reverse=True)
        value = max_table_length if len(invites) >= max_table_length else len(invites)
        table = tabulate.tabulate(invites[0:value], headers=['Inviter', 'Added'])

        description = description + f'\n**__Top server {value} inviters__**\n```\n' + table + '```' + \
            (f' ___There are {len(invites) - max_table_length} more inviters in this server.___' if len(invites) > max_table_length else '')

        embed.description = description

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

    @welcome.command(name="message")
    async def welcome_message(self, ctx: CustomContext, *, message: commands.clean_content):
        """
        Sets the welcome message for this server.
        ``````fix
        Here are some placeholders you can use in the message.
        To use them, just surround them in {} symbols, like so:
        = {server}, {full-name} or {code}
        ``````yaml
        server : returns the server's name (Server Name)
        user : returns the user's name (Name)
        full-user : returns the user's full name (Name#1234)
        user-mention : will mention the user (@Name)
        count : returns the member count of the server(4385)
        code : *the invite code the member used to join(JKf38mZ)
        full-code : *the full invite (discord.gg/JKf38mZ)
        full-url : *the full url (https://discord.gg/JKf38mZ)
        inviter : *returns the inviter's name (Name)
        full-inviter : *returns the inviter's full name (Name#1234)
        inviter-mention : *returns the inviter's mention (@Name)
        ``````yaml
        NOTE: these placeholders are CASE SENSITIVE.
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

    @welcome.command(name='fake-message', aliases=['fake', 'test-message'])
    async def welcome_message_test(self, ctx: CustomContext):
        """ Sends a fake welcome message """
        member = ctx.author
        message = await self.bot.db.fetchval("SELECT welcome_message FROM prefixes WHERE guild_id = $1",
                                             member.guild.id)
        message = message or default_message
        invite = SimpleNamespace(url='https://discord.gg/discord-api',
                                 code='discord-api',
                                 inviter=random.choice(ctx.guild.members))

        l = {'server': str(member.guild),
             'user': str(member.display_name),
             'full-user': str(member),
             'user-mention': str(member.mention),
             'count': str(member.guild.member_count),
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
        # It is recommended to use the "%PRE%slowmode [channel] <short_time>" command to accompany this one, as to not flood the channel with reactions.
        Note: If set to image_only, the bot will delete all messages without attachments.
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
        Manages the current mute role. If no role is specified, shows the current mute role.
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

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
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
            return await ctx.send(embed=embed)

    @counting.command(name='set-channel')
    async def ct_set_channel(self, ctx: CustomContext, channel: discord.TextChannel):
        """ Sets this server's count channel """
        try:
            await ctx.trigger_typing()
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await self.bot.db.execute('INSERT INTO count_settings (guild_id, channel_id) VALUES ($1, $2)', ctx.guild.id,
                                      channel.id)
            self.bot.counting_channels[ctx.guild.id] = {'channel': ctx.channel.id,
                                                        'number': 0,
                                                        'last_counter': None,
                                                        'delete_messages': True,
                                                        'reset': False,
                                                        'last_message_id': None,
                                                        'messages': deque(maxlen=100)}
            await ctx.send(f'✅ **|** Set the **counting channel** to {channel.mention}')
        except asyncpg.UniqueViolationError:
            if (ctx.guild.id in self.bot.counting_channels and self.bot.counting_channels[ctx.guild.id]['channel'] != channel.id) or (ctx.guild.id not in self.bot.counting_channels):
                confirm = await ctx.confirm(
                    '⚠ **|** There is already a **counting channel**! Would you like to **update it** and reset the count number to **0**?',
                    return_message=True)
                if confirm[0] is True:
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

    @counting.command(name='unset-channel')
    async def ct_unset_channel(self, ctx: CustomContext):
        """ Unsets this server's counting channel """
        if ctx.guild.id in self.bot.counting_channels:
            confirm = await ctx.confirm('⚠ **|** Are you sure you **unset** the **counting channel**?', return_message=True)
            if confirm[0] is True:
                self.bot.counting_channels.pop(ctx.guild.id)
                await self.bot.db.execute('DELETE FROM count_settings WHERE guild_id = $1', ctx.guild.id)
                await confirm[1].edit(content='✅ **|** **Unset** this server\'s **counting channel**!', view=None)
            else:
                await confirm[1].edit(content='❌ **|** Cancelled!', view=None)
        else:
            await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')

    @counting.command(name='add-reward')
    async def ct_add_reward(self, ctx: CustomContext):
        """ An interactive way to add a reward to the counting game. """
        async def check(m: discord.Message):
            return m.channel == ctx.channel and m.author == ctx.author

        async def int_check(m: discord.Message):
            return m.channel == ctx.channel and m.author == ctx.author and m.content.isdigit()

        async def role_check(m: discord.Message):
            if m.channel == ctx.channel and m.author == ctx.author:
                if m.content.lower() in ('cancel', 'skip'):
                    return True
                try:
                    await commands.RoleConverter().convert(ctx, m.content)
                    return True
                except commands.RoleNotFound:
                    return False
            return False

        async def emoji_check(m: discord.Message):
            if m.channel == ctx.channel and m.author == ctx.author:
                if m.content.lower() in ('cancel', 'skip'):
                    return True
                try:
                    (await UnicodeEmoji().convert(ctx, m.content)) or (await commands.RoleConverter().convert(ctx, m.content))
                    return True
                except commands.EmojiNotFound:
                    return False
            return False

        try:
            await ctx.send('1️⃣ **|** What **number** would this reward be assigned to?')
            number = int((await self.bot.wait_for('message', check=int_check, timeout=120)).content)

            await ctx.send('2️⃣ **|** What **message** would you want to be sent to the channel when this number is reached?'
                           '\nℹ **|** Type `skip` to skip, and `cancel` to cancel')
            message = (await self.bot.wait_for('message', check=check, timeout=120)).content
            message = message if message.lower() != 'skip' else None

            await ctx.send('3️⃣ **|** What **role** would you want to be assigned to the person who reached this number?'
                           '\nℹ **|** Type `skip` to skip, and `cancel` to cancel')
            role = (await self.bot.wait_for('message', check=role_check, timeout=120)).content
            role = await commands.RoleConverter().convert(ctx, role) if role.lower() != 'skip' else None

            await ctx.send('4️⃣ **|** What **reaction** would you like to be added to the message?'
                           '\nℹ **|** Type `skip` to skip, and `cancel` to cancel')
            emoji = (await self.bot.wait_for('message', check=emoji_check, timeout=120)).content
            emoji = str((await UnicodeEmoji().convert(ctx, emoji)) or (await commands.RoleConverter().convert(ctx, emoji))) if emoji.lower() != 'skip' else None

            try:
                if number in self.bot.counting_rewards[ctx.guild.id]:
                    confirm = await ctx.confirm(f'⚠ **|** **{number} has already a reward associated with it, would you like to overwrite it?',
                                                delete_after_confirm=True, delete_after_timeout=False, delete_after_cancel=False)
                    if confirm is False:
                        return
            except KeyError:
                pass

            await self.update_rewards(guild=ctx.guild, reward_number=number, message=message, role=role, reaction=emoji)
            await ctx.send(f'✅ **|** Added **reward** for number **{number}**')

        except asyncio.TimeoutError:
            return await ctx.send('⚠ **|** Timed out! Please try again.')

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
            await self.bot.db.execute('DELETE FROM counting WHERE (guild_id, reward_number) = ($1, $2)', ctx.guild.id, number)
        else:
            await ctx.send('⚠ **|** That is not one of the **counting rewards**!')

    @counting.command(name='all-rewards')
    async def ct_all_rewards(self, ctx: CustomContext):
        """ [unavailable] Shows all the counting rewards """
        await ctx.send('Not implemented yet!')

    @counting.command(name='check-reward')
    async def ct_check_reward(self, ctx: CustomContext, number: int):
        """ [unavailable] Checks a number to see if it is assigned to a reward """
        await ctx.send('Not implemented yet!')

    @counting.command(name='override-number')
    async def ct_override_number(self, ctx: CustomContext, number: int):
        """ Sets this server's current count number in case it breaks somehow """
        if ctx.guild.id in self.bot.counting_channels:
            if number < 0:
                raise commands.BadArgument('⚠ **|** **Number** must be greater or equal to **0**')
            confirm = await ctx.confirm(f'⚠ **|** Are you sure you **set** the **counting number** to **{number}**?', return_message=True)
            if confirm[0] is True:
                self.bot.counting_channels[ctx.guild.id]['number'] = number
                await self.bot.db.execute('UPDATE count_settings SET current_number = $2 WHERE guild_id = $1',
                                          ctx.guild.id, number)
                await confirm[1].edit(content=f'✅ **|** Updated the **counting number** to **{number}**. '
                                              f'\nℹ **|** The next number will be **{number + 1}**', view=None)
        else:
            await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')

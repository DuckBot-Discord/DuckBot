import random
from typing import TYPE_CHECKING
from types import SimpleNamespace

import discord
from discord.ext import commands

from DuckBot import errors
from DuckBot.__main__ import CustomContext
from ._base import ConfigBase

if TYPE_CHECKING:
    clean_content = str
else:
    from discord.ext.commands import clean_content

default_message = "**{inviter}** just added **{user}** to **{server}** (They're the **{count}** to join)"


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


class Welcome(ConfigBase):

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
    async def welcome_message(self, ctx: CustomContext, *, message: clean_content):
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
        > **`code`** : the invite code the member used to join(TdRfGKg8Wh) **\\***
        > **`full-code`** : the full invite (discord.gg/TdRfGKg8Wh) **\\***
        > **`full-url`** : the full url (<https://discord.gg/TdRfGKg8Wh>) **\\***
        > **`inviter`** : returns the inviters name (Name) *****
        > **`full-inviter`** : returns the inviters full name (Name#1234) **\\***
        > **`inviter-mention`** : returns the inviters mention (@Name) **\\***

        ⚠ These placeholders are __CASE SENSITIVE.__
        ⚠ Placeholders marked with ***** may not be populated when a member joins, like when a bot joins, or when a user is added by an integration.

        **🧐 Example:**
        `%PRE%welcome message Welcome to **{server}**, **{full-user}**!`
        **📤 Output when a user joins:**
        > Welcome to **Duck Hideout**, **LeoCx1000#9999**!
        """
        message: str
        query = """
                INSERT INTO prefixes(guild_id, welcome_message) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET welcome_message = $2
                """

        member = ctx.author
        inviter = random.choice(ctx.guild.members)

        to_format = {'server': str(member.guild),
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
            str(message).format(**to_format)
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

        to_format = {'server': str(member.guild),
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

        await ctx.send(message.format(**to_format), allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_invite_update(self, member, invite):
        try:
            channel = await self.bot.get_welcome_channel(member)
        except errors.NoWelcomeChannel:
            return
        message = await self.bot.db.fetchval("SELECT welcome_message FROM prefixes WHERE guild_id = $1",
                                             member.guild.id)
        message = message or default_message

        to_format = {'server': str(member.guild),
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

        await channel.send(message.format(**to_format))

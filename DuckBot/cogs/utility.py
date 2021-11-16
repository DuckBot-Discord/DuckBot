import asyncio
import re
import typing
import unicodedata
from itertools import cycle
from pprint import pprint

import discord

from inspect import Parameter
from typing import Optional

import humanize
import jishaku
import tabulate
from discord.ext import commands, menus
from jishaku.paginators import WrappedPaginator

from DuckBot import errors
from DuckBot.cogs.guild_config import GuildSettings
from DuckBot.helpers import paginator, time_inputs, constants
from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers import helper
from DuckBot.helpers.paginator import PaginatedStringListPageSource, TodoListPaginator


def setup(bot):
    bot.add_cog(Utility(bot))


def get_sorted_mapping(guild: discord.Guild) -> typing.Dict[Optional[discord.CategoryChannel], typing.List[discord.abc.GuildChannel]]:
    mapping = {None: sorted([c for c in guild.channels if not isinstance(c, discord.CategoryChannel) and not c.category], key=lambda c: c.position)}
    for c in sorted(guild.categories, key=lambda c: c.position):
        mapping[c] = sorted(c.channels, key=lambda c: c.position if not isinstance(c, discord.VoiceChannel) else c.position + len(guild.channels))

    return mapping


def get_channel_positions(ctx: CustomContext, guild: discord.Guild, member_counts: bool = False) -> typing.Dict[str, str]:
    sorted_channels = []
    for category, channels in get_sorted_mapping(guild).items():
        if category:
            sorted_channels.append((str(category), '✅ --' if category.permissions_for(ctx.author).read_messages else '❌ --'))
        for channel in channels:
            if member_counts:
                sorted_channels.append((str(channel), ('✅ ' if channel.permissions_for(ctx.author).view_channel else '❌ ') + f"{len(channel.members)}"))
            else:
                sorted_channels.append((str(channel), ('✅ ' if channel.permissions_for(ctx.author).view_channel else '❌ ') + f"N/A"))
    return sorted_channels


class GenerateChannels(discord.ui.Button['ServerInfoView']):
    def __init__(self, ctx: CustomContext, *, guild: discord.Guild = None):
        super().__init__(label='Request Channel Members', emoji='📚')
        self.guild = guild
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        self.emoji = '<a:loading:747680523459231834>'
        self.label = 'Requesting... Please wait.'
        self.view.callback.disabled = True
        self.view.callback.placeholder = 'Loading Channel Data...'
        self.view._end.disabled = True
        await interaction.response.edit_message(view=self.view)

        channels = await self.ctx.bot.loop.run_in_executor(None, get_channel_positions, self.ctx, self.guild, True)

        self.view.channels = channels

        self.view._end.disabled = False
        self.view._end.emoji = '🛑'
        self.view.callback.disabled = False
        self.view.callback.placeholder = 'Select a category to view...'
        self.view.remove_item(self)

        embed = self.view.generate_channels_embed()
        self.view.channels_embed = embed

        if self.view.callback.values and self.view.callback.values[0] == 'channels':
            print('true')
            return await self.view.message.edit(embed=self.view.channels_embed, view=self.view)
        await self.view.message.edit(view=self.view)


class ServerInfoView(discord.ui.View):
    def __init__(self, ctx: CustomContext, *, guild: discord.Guild):
        super().__init__()
        self.channels: typing.List[discord.abc.GuildChannel] = []
        self.guild = guild
        self.ctx = ctx
        self.bot: DuckBot = ctx.bot
        self.message: discord.Message = None
        self.main_embed: discord.Embed = None
        self.roles_embed: discord.Embed = None
        self.invite_embed: discord.Embed = None
        self.members_embed: discord.Embed = None
        self.channels_embed: discord.Embed = None

    @discord.ui.select(placeholder="Loading data, please wait...",
                       options=[discord.SelectOption(label='Main Page', value='main_page', description='View the main page', emoji='📋'),
                                discord.SelectOption(label='Roles', value='roles', description='View the roles', emoji='🎭'),
                                discord.SelectOption(label='Members', value='members', description='View the members', emoji='👥'),
                                discord.SelectOption(label='Channels', value='channels', description='View the channels', emoji='📚'),
                                discord.SelectOption(label='Invites', value='invite', description='View invite stats', emoji='🔗')],
                       disabled=True)
    async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if select.values[0] == "main_page":
            await interaction.response.edit_message(embed=self.main_embed)
        elif select.values[0] == "roles":
            await interaction.response.edit_message(embed=self.roles_embed)
        elif select.values[0] == "members":
            await interaction.response.edit_message(embed=self.members_embed)
        elif select.values[0] == "channels":
            await interaction.response.edit_message(embed=self.channels_embed)
        elif select.values[0] == "invite":
            await interaction.response.edit_message(embed=self.invite_embed)

    @discord.ui.button(emoji='<a:loading:747680523459231834>', style=discord.ButtonStyle.danger, disabled=True,
                       label='Loading may take up to 10 seconds')
    async def _end(self, _, interaction: discord.Interaction):
        await interaction.message.delete()
        self.stop()

    async def on_timeout(self) -> None:
        if self.message:
            self.clear_items()
            await self.message.edit(view=self)

    async def start(self):
        self.message = await self.ctx.send(embed=discord.Embed(title='<a:loading:747680523459231834> Loading...'), footer=False)
        self.main_embed = await self.bot.loop.run_in_executor(None, self.generate_main_embed)
        self.message = await self.message.edit(embed=self.main_embed, view=self)
        await self.build_embeds()
        self.callback.disabled = False
        self.callback.placeholder = 'Select a category to view...'
        self._end.disabled = False
        self._end.emoji = '🛑'
        self._end.label = None
        self.message = await self.message.edit(embed=self.main_embed, view=self)

    async def build_embeds(self):
        if not self.roles_embed:
            self.roles_embed = await self.bot.loop.run_in_executor(None, self.generate_roles_embed)
        if not self.members_embed:
            self.members_embed = await self.bot.loop.run_in_executor(None, self.generate_members_embed)
        if not self.channels_embed:
            self.channels_embed = await self.bot.loop.run_in_executor(None, self.generate_channels_embed)
        if not self.invite_embed:
            self.invite_embed = await self.generate_invite_embed()

    def generate_main_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx

        enabled_features = []
        features = set(guild.features)

        for feature, label in constants.GUILD_FEATURES.items():
            if feature in features:
                enabled_features.append(f'{ctx.tick(True)} {label}')

        embed = discord.Embed(title=guild.name, colour=ctx.colour, timestamp=ctx.message.created_at)

        embed.add_field(name=f"{constants.RICH_PRESENCE} Features:",
                        value=(('\n'.join(
                            enabled_features) if enabled_features else 'No features...') + '\n\u200b _ _'),
                        inline=True)

        embed.add_field(name=f"{constants.INFORMATION_SOURCE} General Info:",
                        value=f"🆔 {guild.id}"
                              f"\n{constants.OWNER_CROWN} {guild.owner}"
                              f"\n🌐 Server Region:\n╰ {helper.get_server_region(guild)}"
                              f"\n{constants.VERIFICATION_LEVEL[guild.verification_level]} "
                              f"{str(guild.verification_level).replace('_', ' ').replace('none', 'no').title()} Verification Level"
                              f"\n📁 File size limit: {humanize.naturalsize(guild.filesize_limit)}"
                              f"\n{constants.ROLES_ICON} Role amount: {len(guild.roles)}"
                              f"\n\u200b _ _"
                        )

        embed.add_field(name=f"{constants.INFORMATION_SOURCE} Server description:",
                        value=guild.description or f"{constants.TOGGLES[False]} Description disabled!",
                        inline=False)

        embed.add_field(name=f"{constants.JOINED_SERVER} Created at:",
                        value=f"{discord.utils.format_dt(guild.created_at, 'F')} ({discord.utils.format_dt(guild.created_at, 'R')})",
                        inline=False)

        embed.add_field(name=f"{constants.VERIFICATION_LEVEL[guild.verification_level]} Server content filter:",
                        value=f"{constants.CONTENT_FILTER[guild.explicit_content_filter]}\n\u200b _ _",
                        inline=False)

        embed.add_field(name=f"{constants.RICH_PRESENCE} Channels:",
                        value=f"{constants.VOICE_CHANNEL} "
                              f"{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}"
                              f"\n{constants.TEXT_CHANNEL} Channels: "
                              f"{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}"
                              f"\n{constants.CATEGORY_CHANNEL} Categories: "
                              f"{len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}"
                              f"\n{constants.STAGE_CHANNEL} Stages: "
                              f"{len([c for c in guild.channels if isinstance(c, discord.StageChannel)])}"
                              f"\n{constants.TEXT_CHANNEL_WITH_THREAD} Threads: {len(guild.threads)}"
                              f"\n╰ (only threads visible by me)",
                        inline=True)

        embed.add_field(name=f"{constants.EMOJI_GHOST} Emojis:",
                        value=f"Static: {len([e for e in guild.emojis if not e.animated])}/{guild.emoji_limit} "
                              f"\nAnimated: {len([e for e in guild.emojis if e.animated])}/{guild.emoji_limit} ",
                        inline=True)

        last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
        if last_boost.premium_since is not None:
            boost = f"\n{last_boost}" \
                    f"\n╰ {discord.utils.format_dt(last_boost.premium_since, style='R')}"
        else:
            boost = "\n╰ No active boosters"

        embed.add_field(name=f"{constants.BOOST} Boosts:",
                        value=f"{constants.GUILD_BOOST_LEVEL_EMOJI[str(guild.premium_tier)]} Level: {guild.premium_tier}"
                              f"\n╰ Amount: {guild.premium_subscription_count}"
                              f"\n**{constants.BOOST} Last booster:**{boost}")

        embed.add_field(name=f'👥 Member information:',
                        value=f"\n👤 Humans: {len([m for m in guild.members if not m.bot])} "
                              f"\n🤖 Bots: {len([m for m in guild.members if m.bot])}"
                              f"\n♾ Total: {guild.member_count}"
                              f"\n📂 Limit: {guild.max_members}"
                        )
        embed.add_field(name=f"{constants.ROLES_ICON} Member statuses:",
                        value=f"\n{constants.statuses.ONLINE} Online: {len(list(filter(lambda m: m.status == discord.Status.online, guild.members)))}"
                              f"\n{constants.statuses.IDLE} Idle: {len(list(filter(lambda m: m.status == discord.Status.idle, guild.members)))}"
                              f"\n{constants.statuses.DND} DND: {len(list(filter(lambda m: m.status == discord.Status.do_not_disturb, guild.members)))}"
                              f"\n{constants.statuses.OFFLINE} Offline: {len(list(filter(lambda m: m.status == discord.Status.offline, guild.members)))}"
                        )

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        return embed

    def generate_roles_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx
        embed = discord.Embed(title=guild.name, colour=ctx.colour, timestamp=ctx.message.created_at)

        roles = [(r.name, f'{str(len(r.members))} <' if r in ctx.author.roles else str(len(r.members))) for r in sorted(guild.roles, key=lambda r: r.position, reverse=True)]

        if ctx.author.is_on_mobile():
            pag = WrappedPaginator(prefix='Role Name and Member Count:\n```\n', suffix='\n```', max_size=4096)
            for line in (tabulate.tabulate(roles, headers=["Role Name", "Count"], tablefmt="presto")).split('\n'):
                pag.add_line(line)
            embed.description = pag.pages[0]
        else:
            pag = WrappedPaginator(prefix='```\n', suffix='\n```', max_size=1024)
            pag2 = WrappedPaginator(prefix='```\n', suffix='\n```', max_size=1024)
            for role, amount in roles:
                pag.add_line(role)
                pag2.add_line(amount)
            embed.description = 'Role Name and Member Count:'
            embed.add_field(name='Role Name', value=pag.pages[0])
            embed.add_field(name='Count', value=pag2.pages[0])

        embed.add_field(name="Your Roles", inline=False,
                        value=f"You have {len(ctx.author.roles)} (signified by `<`)"
                              f"\nYour top role: {ctx.author.top_role.mention}")

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed

    def generate_members_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx
        embed = discord.Embed(title=guild.name, colour=ctx.colour, timestamp=ctx.message.created_at)

        sort_mems = sorted(ctx.guild.members, key=lambda m: m.joined_at or ctx.message.created_at)

        index = 0
        members = [f'{m} ({m.joined_at.strftime("%d %b %Y. %H:%M")})' for m in sort_mems[:5]]
        join_order = [f"{n}.{' ' * (7 - len(str(n)) + 1)}{s}" for n, s in enumerate(members, start=index+1)]

        embed.add_field(name=f"👥 First Members and Join Date:", inline=False,
                        value='```py\n' + '\n'.join(join_order) + '\n```')

        index = len(sort_mems)
        members = [f'{m} ({m.joined_at.strftime("%d %b %Y. %H:%M")})' for m in sort_mems[-5:]]
        join_order = [f"{n}.{' ' * (7 - len(str(n)) + 1)}{s}" for n, s in enumerate(members, start=index-5)]

        embed.add_field(name=f"👥 Recent Members and Join Date:", inline=False,
                        value='```py\n' + '\n'.join(join_order) + '\n```')

        if guild.premium_subscribers:
            index = len(guild.premium_subscribers)
            sort_subs = sorted(guild.premium_subscribers, key=lambda m: m.premium_since or m.created_at, reverse=True)
            boosters = [f"{m} ({m.premium_since.strftime('%d %b %Y. %H:%M')})" for m in sort_subs[:5]]
            boosters.reverse()
            boost_order = '\n'.join([f"{n}.{' ' * (7 - len(str(n)) + 1)}{s}" for n, s in enumerate(boosters, start=index)])
            embed.add_field(name=f"💎 Recent Boosters:", inline=False,
                            value='```py\n' + boost_order + '\n```' +
                                  f'**Boosts** {guild.premium_subscription_count} •'
                                  f'**Boosters** {len(guild.premium_subscribers)}')

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed

    def generate_channels_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx
        embed = discord.Embed(title=guild.name, colour=ctx.colour)

        if not self.channels:
            if guild.member_count < 1000:
                channels = get_channel_positions(self.ctx, self.guild, member_counts=True)
            else:
                self.add_item(GenerateChannels(ctx, guild=guild))
                channels = get_channel_positions(self.ctx, self.guild, member_counts=False)
        else:
            channels = self.channels

        if ctx.author.is_on_mobile():
            pag = WrappedPaginator(prefix='Channel Name and Member Count:\n```\n', suffix='\n```', max_size=4096)
            for line in (tabulate.tabulate(channels, headers=["Channel Name", "Count"], tablefmt="presto")).split('\n'):
                pag.add_line(line)
            embed.description = pag.pages[0]
        else:
            pag = WrappedPaginator(prefix='```\n', suffix='\n```', max_size=1024)
            pag2 = WrappedPaginator(prefix='```\n', suffix='\n```', max_size=1024)
            for ch, amount in channels:
                pag.add_line(ch)
                pag2.add_line(amount)
            embed.description = 'Channel Name and Member Count:'
            embed.add_field(name='Channel Name', value=pag.pages[0])
            embed.add_field(name='Count', value=pag2.pages[0])

        embed.set_footer(text=f"✅ - Channels you have access to."
                              f"\n❌ - Channels you don't have access to.", icon_url=ctx.author.display_avatar.url)
        return embed

    async def generate_invite_embed(self) -> discord.Embed:
        cog: GuildSettings = self.bot.get_cog('Guild Settings')
        try:
            return await cog.invitestats(self.ctx, return_embed=True)
        except commands.BotMissingPermissions:
            embed = discord.Embed(title="Invite Stats", colour=self.ctx.colour,
                                  description="I don't have the `Manage Server` permission.")
            embed.set_footer(text=f"Requested by {self.ctx.author}", icon_url=self.ctx.author.display_avatar.url)
        except Exception as e:
            embed = discord.Embed(title="Invite Stats", colour=self.ctx.colour,
                                  description=f"Something went wrong.\n{e}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.defer()
        return False


class UserInfoView(discord.ui.View):
    def __init__(self, ctx: CustomContext, uinfo_embed: discord.Embed, banner: discord.Embed = None,
                 order_embed: discord.Embed = None):
        super().__init__()
        if banner:
            self.embeds = cycle([uinfo_embed, order_embed, banner])
            self.labels = cycle(['Show Banner', 'Show User Info', 'Show Join Order'])
        else:
            self.embeds = cycle([uinfo_embed, order_embed])
            self.labels = cycle(['Show User Info', 'Show Join Order'])
        self.banner = banner
        self.ui = uinfo_embed
        self.message: discord.Message = None
        self.ctx = ctx

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.defer()
        return False

    async def start(self):
        self.message = await self.ctx.send(embed=next(self.embeds), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji='🔁', label='Show Join Order')
    async def next_embed(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = next(self.embeds)
        button.label = next(self.labels)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.red, emoji='🗑')
    async def stop_button(self, _, __):
        await self.message.delete()
        self.stop()


class Utility(commands.Cog):
    """
    💬 Text and utility commands, mostly to display information about a server.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = '💬'
        self.select_brief = 'Utility And General Information Commands.'

    @commands.command(name='charinfo')
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def character_info(self, ctx: CustomContext, *, characters: str):
        """Shows you information about a number of characters."""

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - **{c}** \N{EM DASH} ' \
                   f'<http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))

        menu = menus.MenuPages(paginator.CharacterInformationPageSource(msg.split("\n"), per_page=20),
                               delete_message_after=True)
        await menu.start(ctx)

    @commands.command(aliases=['s', 'send'],
                      help="Speak as if you were me. # URLs/Invites not allowed!")
    @commands.check_any(commands.bot_has_permissions(send_messages=True), commands.is_owner())
    async def say(self, ctx: CustomContext, *, msg: str) -> Optional[discord.Message]:

        results = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|)+",
                             msg)  # HTTP/HTTPS URL regex
        results2 = re.findall(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?",
                              msg)  # Discord invite regex
        if results or results2:
            await ctx.send(
                f"hey, {ctx.author.mention}. Urls or invites aren't allowed!",
                delete_after=10)
            return await ctx.message.delete(delay=10)

        await ctx.message.delete(delay=0)
        if ctx.channel.permissions_for(ctx.author).manage_messages:
            allowed = True
        else:
            allowed = False

        return await ctx.send(msg[0:2000], allowed_mentions=discord.AllowedMentions(everyone=False,
                                                                                    roles=False,
                                                                                    users=allowed),
                              reference=ctx.message.reference,
                              reply=False)

    @commands.command(
        aliases=['a', 'an', 'announce'],
        usage="<channel> <message_or_reply>")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def echo(self, ctx: CustomContext, channel: typing.Union[discord.TextChannel, int], *,
                   message_or_reply: str = None) \
            -> discord.Message:
        """"
        Echoes a message to another channel
        # If a message is quoted, it will echo the quoted message's content.
        """
        if isinstance(channel, int) and self.bot.is_owner(ctx.author):
            channel = self.bot.get_channel(channel)
        if not channel:
            raise commands.MissingRequiredArgument(Parameter(name='channel', kind=Parameter.POSITIONAL_ONLY))
        if not ctx.message.reference and not message_or_reply:
            raise commands.MissingRequiredArgument(
                Parameter(name='message_or_reply', kind=Parameter.POSITIONAL_ONLY))
        elif ctx.message.reference:
            message_or_reply = ctx.message.reference.resolved.content
        return await channel.send(message_or_reply[0:2000], allowed_mentions=discord.AllowedMentions(
            everyone=False, roles=False, users=True))

    @commands.command(
        aliases=['e', 'edit'], name='edit-message',
        usage="[new message] [--d|--s]")
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

    @commands.command(aliases=['uinfo', 'ui', 'whois', 'userinfo'], name='user-info', slash_command=True, slash_command_guilds=[774561547930304536, 745059550998298756])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def userinfo(self, ctx: CustomContext, *, member: typing.Optional[discord.Member]):
        """
        Shows a user's information. If not specified, shows your own.
        """
        member = member or ctx.author
        uid = getattr(ctx.interaction, 'data', {}).get("resolved", {}).get("members", {})
        member = ctx.guild.get_member(int(next(iter(uid), member.id))) or ctx.author
        await ctx.trigger_typing()
        fetched_user = await self.bot.fetch_user(member.id)

        embed = discord.Embed(color=member.color if member.color not in (None, discord.Color.default()) else ctx.color)
        embed.set_author(name=f"{member}'s User Info", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name=f"{constants.INFORMATION_SOURCE} General information",
                        value=f"**ID:** {member.id}"
                              f"\n**Name:** {member.name}"
                              f"\n╰ **Nick:** {(member.nick or '✖')}"
                              f"\n**Profile Color:** {str(fetched_user.accent_color).upper() or 'Not set'}"
                              f"\n**Owner:** {ctx.tick(member == member.guild.owner)} • "
                              f"**Bot:** {ctx.tick(member.bot)}", inline=True)

        embed.add_field(name=f"{constants.STORE_TAG} Badges",
                        value=helper.get_user_badges(user=member, fetched_user=fetched_user,
                                                     bot=self.bot) or "No Badges", inline=True)

        embed.add_field(name=f"{constants.INVITE} Created At",
                        value=f"╰ {discord.utils.format_dt(member.created_at, style='f')} "
                              f"({discord.utils.format_dt(member.created_at, style='R')})",
                        inline=False)

        embed.add_field(name=f"{constants.JOINED_SERVER} Joined At",
                        value=(f"╰ {discord.utils.format_dt(member.joined_at, style='f')} "
                               f"({discord.utils.format_dt(member.joined_at, style='R')})"
                               f"\n\u200b \u200b \u200b \u200b ╰ {constants.MOVED_CHANNELS} **Join Position:** "
                               f"{sorted(ctx.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow()).index(member) + 1}")
                        if member.joined_at else "Could not get data",
                        inline=False)

        if member.premium_since:
            embed.add_field(name=f"{constants.BOOST} Boosting since:",
                            value=f"╰ {discord.utils.format_dt(member.premium_since, style='f')} "
                                  f"({discord.utils.format_dt(member.premium_since, style='R')})",
                            inline=False)

        custom_activity = discord.utils.find(lambda act: isinstance(act, discord.CustomActivity), member.activities)
        activity_string = f"`{discord.utils.remove_markdown(custom_activity.name)}`" if custom_activity and custom_activity.name else 'User has no custom status.'
        embed.add_field(name=f'Activity:',
                        value=f"\n{helper.generate_user_statuses(member)}"
                              f"\n**Custom status:**"
                              f"\n{activity_string}")

        spotify = discord.utils.find(lambda act: isinstance(act, discord.Spotify), member.activities)

        embed.add_field(name=f"{constants.SPOTIFY} Spotify:",
                        value=f"**[{spotify.title}]({spotify.track_url})**"
                              f"\nBy __{spotify.artist}__"
                              f"\nOn __{spotify.album}__"
                              f"\n**Time:** {helper.deltaconv((ctx.message.created_at - spotify.start).total_seconds())}/"
                              f"{helper.deltaconv(spotify.duration.total_seconds())}"
                        if spotify else 'Not listening to anything...')

        perms = helper.get_perms(member.guild_permissions)
        if perms:
            embed.add_field(name=f"{constants.STORE_TAG} Staff Perms:",
                            value=f"`{'` `'.join(perms)}`", inline=False)

        roles = [r.mention for r in member.roles if not r.is_default()]
        roles.reverse()
        if roles:
            embed.add_field(name=f"{constants.ROLES_ICON} Roles:",
                            value=", ".join(roles) +
                                  f"\n**Top Role:** {member.top_role} • "
                                  f"**Color:** {member.color if member.color is not discord.Color.default() else 'Default'}",
                            inline=False)

        order_embed = discord.Embed(
            color=member.color if member.color not in (None, discord.Color.default()) else ctx.color,
            timestamp=ctx.message.created_at)
        order_embed.set_author(name=f"{member}'s Joined order", icon_url=member.display_avatar.url)
        order_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        sort_mems = sorted(ctx.guild.members, key=lambda m: m.joined_at or m.created_at)
        index = sort_mems.index(member)
        members = [f'{m} ({m.joined_at.strftime("%d %b %Y. %S:%H")})' for m in
                   sort_mems[(index - 10 if index > 10 else 0):index + 10]]
        join_order = '\n'.join([f"{n}.{' ' * (10 - len(str(n)) + 1)}{s}" for n, s in
                                enumerate(members, start=(index - 10 if index > 10 else 0) + 1)]).replace(f"  {member}",
                                                                                                          f"> {member}")
        order_embed.description = '```py\n' + join_order + '\n```'
        order_embed.add_field(name=f"{constants.JOINED_SERVER} Joined At",
                              value=(f"╰ {discord.utils.format_dt(member.joined_at, style='f')} "
                                     f"({discord.utils.format_dt(member.joined_at, style='R')})"
                                     f"\n\u200b \u200b \u200b \u200b ╰ {constants.MOVED_CHANNELS} **Join Position:** "
                                     f"{sorted(ctx.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow()).index(member) + 1}")
                              if member.joined_at else "This user's joined data seems to be None, so ive put them near the end,", inline=False)

        banner_embed = None
        if fetched_user.banner:
            banner_embed = discord.Embed(
                color=member.color if member.color not in (None, discord.Color.default()) else ctx.color,
                timestamp=ctx.message.created_at)
            banner_embed.set_author(name=f"{member}'s Banner", icon_url=member.display_avatar.url)
            banner_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            banner_embed.set_image(url=fetched_user.banner.url)
        view = UserInfoView(ctx, embed, banner_embed, order_embed)
        await view.start()

    @commands.command(aliases=['perms'], usage='[target] [channel]')
    @commands.guild_only()
    async def permissions(self, ctx: CustomContext,
                          target: typing.Optional[discord.Member],
                          channel: typing.Optional[discord.abc.GuildChannel],
                          _target: typing.Optional[discord.Member]):
        """
        Displays a user's server permissions, and their channel-specific overwrites.
        By default, it will show the bots permissions, for the current channel.
        """
        perms = []
        target = target or _target or ctx.me
        channel = channel or ctx.channel
        channel_perms = [x for x, y in channel.permissions_for(target) if y is True]
        for perm, value in target.guild_permissions:
            perms.append([perm.replace('guild', 'server').replace('_', ' ').title(), str(value),
                          str(perm in channel_perms)])
        table = tabulate.tabulate(perms, tablefmt="orgtbl", headers=['Permissions', 'Server', 'Channel'])
        embed = discord.Embed(description=f"```py\n{table}\n```")
        embed.set_footer(text='"Channel" permissions consider Server, Channel and Member overwrites.')
        embed.set_author(name=f'{target}\'s permissions for {channel}'[0:256], icon_url=target.display_avatar)
        await ctx.send(embed=embed)

    @commands.command(aliases=['si', 'serverinfo'], name='server-info', usage=None)
    @commands.guild_only()
    async def server_info(self, ctx: CustomContext, guild: typing.Optional[discord.Guild]):
        """
        Shows the current server's information.
        """
        await ctx.trigger_typing()
        guild = guild if guild and (await self.bot.is_owner(ctx.author)) else ctx.guild
        view = ServerInfoView(ctx, guild=guild)
        await view.start()

    @commands.command(aliases=['av', 'pfp'])
    async def avatar(self, ctx: CustomContext, *, member: typing.Union[discord.Member, discord.User] = None):
        """
        Displays a user's avatar. If not specified, shows your own.
        """
        user: discord.User = member or ctx.author
        embed = discord.Embed(title=user, url=user.display_avatar.url)
        if isinstance(user, discord.Member) and user.guild_avatar:
            embed.set_thumbnail(url=user.display_avatar.url if user.avatar else user.default_avatar.url)
            embed.description = f"[avatar]({user.display_avatar.url if user.avatar else user.default_avatar.url}) | " \
                                f"[server avatar]({user.display_avatar.url})"
        embed.set_image(url=user.display_avatar.url)

        await ctx.send(embed=embed, footer=False)

    @commands.group(invoke_without_command=True, aliases=['em'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def emoji(self, ctx: CustomContext,
                    custom_emojis: commands.Greedy[typing.Union[discord.Emoji, discord.PartialEmoji]]):
        """
        Shows information about one or more emoji.
        _Note, this is a group, and has also more sub-commands_
        """
        if not custom_emojis:
            raise commands.MissingRequiredArgument(
                Parameter(name='custom_emojis', kind=Parameter.POSITIONAL_ONLY))

        source = paginator.EmojiListPageSource(data=custom_emojis, ctx=ctx)
        menu = paginator.ViewPaginator(source=source, ctx=ctx,
                                       check_embeds=True)
        await menu.start()

    @emoji.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_lock(self, ctx: CustomContext, server_emoji: discord.Emoji,
                         roles: commands.Greedy[discord.Role]) -> discord.Message:
        """
        Locks an emoji to one or multiple roles. Input as many roles as you want in the "[roles]..." parameter.
        Note: admin/owner DOES NOT bypass this lock, so be sure to have the role if you wish to unlock the emoji.
        # If the role is removed and re-assigned, the locked emoji will not be visible until you restart your client.
        # To unlock an emoji you can't access, use the `db.emoji unlock <emoji_name>` command
        """
        if not roles:
            raise commands.MissingRequiredArgument(Parameter('role', Parameter.POSITIONAL_ONLY))
        if server_emoji.guild_id != ctx.guild.id:
            return await ctx.send("That emoji is from another server!")
        embed = discord.Embed(description=f"**Restricted access of {server_emoji} to:**"
                                          f"\n{', '.join([r.mention for r in roles])}"
                                          f"\nTo unlock the emoji do `{ctx.clean_prefix} emoji unlock {server_emoji}`"
                                          f"_Note that to do this you will need one of the roles the emoji has been "
                                          f"restricted to. \nNo, admin permissions don't bypass this lock._")
        await ctx.send(embed=embed)
        await server_emoji.edit(roles=roles)

    @emoji.group(name="unlock", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_unlock(self, ctx: CustomContext, server_emoji: discord.Emoji) -> discord.Message:
        """
        Unlocks a locked emoji.
        **Note:** If you don't have access to the emoji you can also do:

        **__GOOD:__** `%PRE%emoji unlock RooDuck`
        **__BAD:__** `%PRE%emoji unlock :RooDuck:`
        """
        if server_emoji.guild_id != ctx.guild.id:
            return await ctx.send("That emoji is from another server!")
        await server_emoji.edit(roles=[])
        embed = discord.Embed(title="Successfully unlocked emoji!",
                              description=f"**Allowed {server_emoji} to @everyone**")
        return await ctx.send(embed=embed)

    @emoji_unlock.command(name="all")
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_unlock_all(self, ctx: CustomContext):
        """
        Unlocks all locked emojis in the current server.
        """
        async with ctx.typing():
            unlocked = []
            for emoji in ctx.guild.emojis:
                if emoji.roles:
                    await emoji.edit(roles=[], reason=f"Unlock all emoji requested by {ctx.author} ({ctx.author.id})")
                    unlocked.append(emoji)
                    await asyncio.sleep(1)
            await ctx.send(f"Done! Unlocked {len(unlocked)} emoji(s)"
                           f"\n {' '.join([str(em) for em in unlocked])}")

    @emoji.command(name="steal", hidden=True, aliases=['s'])
    @commands.is_owner()
    async def emoji_steal(self, ctx, index: int = 1):
        if not ctx.message.reference:
            raise errors.NoQuotedMessage

        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
        emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
        if not emojis:
            raise errors.NoEmojisFound

        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
        except IndexError:
            return await ctx.send(f"Emoji out of index {index}/{len(emojis)}!"
                                  f"\nIndex must be lower or equal to {len(emojis)}")
        file = await emoji.read()
        guild = self.bot.get_guild(831313673351593994)
        emoji = await guild.create_custom_emoji(name=emoji.name, image=file, reason="stolen emoji KEK")
        try:
            await ctx.message.add_reaction(emoji)
        except discord.NotFound:
            pass

    @emoji.command(name="clone", aliases=['create'])
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_clone(self, ctx: CustomContext,
                          server_emoji: typing.Optional[discord.PartialEmoji],
                          index: typing.Optional[int] = 1, *, name: typing.Optional[str] = '#'):
        """
        Clones an emoji into the current server.
        You can pass either an emoji or an index, not both.

        What is index? Index is for stealing emotes from other people. To do so, reply to their message, and pass a number (index) to select which emoji to steal. For example, to steal the first emoji of the quoted message, pass a number `1`
        If you don't pass an emoji nor a number, and you quoted a message, it will select the first emoji in the message, if applicable.

        Note: You can only pass an emoji _or_ an index, not both.
        """
        if ctx.message.reference:
            custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
            emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
            if not emojis:
                raise errors.NoEmojisFound
            try:
                server_emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
            except IndexError:
                return await ctx.send(f"Emoji out of index {index}/{len(emojis)}!"
                                      f"\nIndex must be lower or equal to {len(emojis)}")

        if not server_emoji:
            raise commands.MissingRequiredArgument(
                Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))

        file = await server_emoji.read()
        guild = ctx.guild

        valid_name = re.compile('^[a-zA-Z0-9_]+$')

        server_emoji = await guild.create_custom_emoji(name=name if valid_name.match(name) else server_emoji.name,
                                                       image=file,
                                                       reason=f"Cloned emoji, requested by {ctx.author}")
        await ctx.send(f"**Done!** cloned {server_emoji} **|** `{server_emoji}`")

    @emoji.command(usage="", name='list')
    @commands.guild_only()
    async def emoji_list(self, ctx: CustomContext, guild: typing.Optional[typing.Union[discord.Guild,
                                                                                       typing.Literal['bot']]]):
        """ Lists this server's emoji """
        target_guild = guild if isinstance(guild, discord.Guild) and (await self.bot.is_owner(ctx.author)) \
            else 'bot' if isinstance(guild, str) and (await self.bot.is_owner(ctx.author)) else ctx.guild
        emojis = target_guild.emojis if isinstance(target_guild, discord.Guild) else self.bot.emojis

        emotes = [f"{str(e)} **|** `{e.id}` **|** [{e.name}]({e.url})" for e in emojis]
        menu = paginator.ViewPaginator(paginator.ServerEmotesEmbedPage(data=emotes,
                                                                       guild=(target_guild if isinstance(target_guild,
                                                                                                         discord.Guild)
                                                                              else ctx.bot)), ctx=ctx)
        await menu.start()

    @emoji.command(name='delete')
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_delete(self, ctx: CustomContext, server_emoji: discord.Emoji):
        """
        Deletes an emoji from this server.
        """
        if server_emoji.guild != ctx.guild:
            raise commands.MissingRequiredArgument(Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))
        confirm = await ctx.confirm(f'❓ | Are you sure you want to delete {server_emoji}?', return_message=True)

        if confirm[0]:
            await server_emoji.delete(reason=f'Deletion requested by {ctx.author} ({ctx.author.id})')
            await confirm[1].edit(content=f'🚮 | Successfully deleted `{server_emoji}`', view=None)
        else:
            await confirm[1].edit(content='❌ | Cancelled!', view=None)

    @emoji.command(name='rename')
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_rename(self, ctx, server_emoji: discord.Emoji, new_name: commands.clean_content):
        """
        Renames an emoji from this server.
        """
        if server_emoji.guild != ctx.guild:
            raise commands.MissingRequiredArgument(Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))
        if len(new_name) > 32:
            raise commands.BadArgument('⚠ | **new_name** must be less than **32 characters** in long.')
        if server_emoji.name == new_name:
            raise commands.BadArgument(f"⚠ | {server_emoji} is already named {new_name}")

        valid_name = re.compile('^[a-zA-Z0-9_]+$')
        if not valid_name.match(new_name):
            raise commands.BadArgument(
                '⚠ | **new_name** can only contain **alphanumeric characters** and **underscores**')
        new_emoji = await server_emoji.edit(name=new_name,
                                            reason='Deletion requested by {ctx.author} ({ctx.author.id})')
        await ctx.send(
            f"{constants.EDIT_NICKNAME} | Successfully renamed {new_emoji} from `{server_emoji.name}` to `{new_emoji.name}`!")

    @commands.command(aliases=['uuid'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def minecraft_uuid(self, ctx: CustomContext, *, username: str) \
            -> typing.Optional[discord.Message]:
        """ Fetches the UUID of a minecraft user from the Mojang API, and avatar from craftavatar.com """
        argument = username
        async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
            if cs.status == 204:
                raise commands.BadArgument('That is not a valid Minecraft UUID!')
            elif cs.status != 200:
                raise commands.BadArgument('Something went wrong...')
            res = await cs.json()
            user = res["name"]
            uuid = res["id"]
            embed = discord.Embed(description=f"**UUID:** `{uuid}`")
            embed.set_author(icon_url=f'https://crafatar.com/avatars/{uuid}?size=128&overlay=true', name=user)
            return await ctx.send(embed=embed)

    @commands.command(name="in")
    async def _in_command(self, ctx, *, relative_time: time_inputs.ShortTime):
        """
        Shows a time in everyone's time-zone
          note that: `relative_time` must be a short time!
        for example: 1d, 5h, 3m or 25s, or a combination of those, like 3h5m25s (without spaces between these times)
        """

        await ctx.send(f"{discord.utils.format_dt(relative_time.dt, style='F')} "
                       f"({discord.utils.format_dt(relative_time.dt, style='R')})")

    @commands.command()
    async def afk(self, ctx: CustomContext, *, reason: commands.clean_content = '...'):
        if ctx.author.id in self.bot.afk_users and ctx.author.id in self.bot.auto_un_afk and self.bot.auto_un_afk[
            ctx.author.id] is True:
            return
        if ctx.author.id not in self.bot.afk_users:
            await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, $2, $3) '
                                      'ON CONFLICT (user_id) DO UPDATE SET start_time = $2, reason = $3',
                                      ctx.author.id, ctx.message.created_at, reason[0:1800])
            self.bot.afk_users[ctx.author.id] = True
            await ctx.send(f'**You are now afk!** {constants.ROO_SLEEP}'
                           f'\n**with reason:** {reason}')
        else:
            self.bot.afk_users.pop(ctx.author.id)

            info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', ctx.author.id)
            await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, null, null) '
                                      'ON CONFLICT (user_id) DO UPDATE SET start_time = null, reason = null',
                                      ctx.author.id)

            await ctx.channel.send(
                f'**Welcome back, {ctx.author.mention}, afk since: {discord.utils.format_dt(info["start_time"], "R")}**'
                f'\n**With reason:** {info["reason"]}', delete_after=10)

            await ctx.message.add_reaction('👋')

    @commands.command(name='auto-afk-remove', aliases=['autoafk', 'aafk'])
    async def auto_un_afk(self, ctx: CustomContext, mode: bool = None):
        """
        Toggles weather to remove the AFK status automatically or not.
        mode: either enabled or disabled. If none, it will toggle it.
        """
        mode = mode or (False if (ctx.author.id in self.bot.auto_un_afk and self.bot.auto_un_afk[
            ctx.author.id] is True) or ctx.author.id not in self.bot.auto_un_afk else True)
        self.bot.auto_un_afk[ctx.author.id] = mode
        await self.bot.db.execute('INSERT INTO afk (user_id, auto_un_afk) VALUES ($1, $2) '
                                  'ON CONFLICT (user_id) DO UPDATE SET auto_un_afk = $2', ctx.author.id, mode)
        return await ctx.send(f'{"Enabled" if mode is True else "Disabled"} automatic AFK removal.'
                              f'\n{"**Remove your AFK status by running the `afk` command while being AFK**" if mode is False else ""}')

    @commands.group()
    async def todo(self, ctx: CustomContext):
        """ Sends help about the to​do command """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @todo.command(name='add')
    async def todo_add(self, ctx: CustomContext, *, text: commands.clean_content):
        """ Adds an item to your to​do list """
        insertion = await self.bot.db.fetchrow(
            "INSERT INTO todo (user_id, text, jump_url, added_time) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (user_id, text) DO UPDATE SET user_id = $1 RETURNING jump_url, added_time",
            ctx.author.id, text[0:4000], ctx.message.jump_url, ctx.message.created_at)
        if insertion['added_time'] != ctx.message.created_at:
            embed = discord.Embed(description=f'⚠ **That is already added to your todo list:**'
                                              f'\n\u200b  → [added here]({insertion["jump_url"]}) '
                                              f'{discord.utils.format_dt(insertion["added_time"], style="R")}')
            return await ctx.send(embed=embed, footer=False)
        await ctx.send('**Added to todo list:**'
                       f'\n\u200b  → {text[0:200]}{"..." if len(text) > 200 else ""}')

    @todo.command(name='list', invoke_without_command=True)
    async def todo_list(self, ctx: CustomContext):
        """ Shows your to​do list """
        user = ctx.author
        entries = await self.bot.db.fetch(
            'SELECT text, added_time, jump_url FROM todo WHERE user_id = $1 ORDER BY added_time ASC', user.id)
        if not entries:
            return await ctx.send(embed=discord.Embed(description='Your to-do list is empty'))

        pages = jishaku.paginators.WrappedPaginator(prefix='', suffix='', max_size=4098)
        for page in [
            f'**[{i + 1}]({entries[i]["jump_url"]} \"Jump to message\"). ({discord.utils.format_dt(entries[i]["added_time"], style="R")}):** {entries[i]["text"]}'
            for i in range(len(entries))]:
            pages.add_line(page[0:4098])

        source = PaginatedStringListPageSource(pages.pages, ctx=ctx)
        view = TodoListPaginator(source, ctx=ctx, compact=True)
        await view.start()

    @todo.command(name='clear')
    async def todo_clear(self, ctx: CustomContext):
        """ Clears all your to​do entries """
        response = await ctx.confirm('Are you sure you want to clear your todo list?', return_message=True)
        if response[0] is True:
            count = await self.bot.db.fetchval(
                'WITH deleted AS (DELETE FROM todo WHERE user_id = $1 RETURNING *) SELECT count(*) FROM deleted;',
                ctx.author.id)
            return await response[1].edit(content=f'✅ **|** Done! Removed **{count}** entries.', view=None)
        await response[1].edit(content='❌ **|** cancelled! Removed **0** entries.', view=None)

    @todo.command(name='remove')
    async def todo_remove(self, ctx: CustomContext, index: int):
        """ Removes one of your to​do list entries """
        entries = await self.bot.db.fetch(
            'SELECT text, added_time FROM todo WHERE user_id = $1 ORDER BY added_time ASC', ctx.author.id)
        try:
            to_delete = entries[index - 1]
        except IndexError:
            raise commands.BadArgument(f'⚠ **|** You do not have a task with index **{index}**')
        await self.bot.db.execute("DELETE FROM todo WHERE (user_id, text) = ($1, $2)", ctx.author.id, to_delete['text'])
        return await ctx.send(
            f'**Deleted** task number **{index}**! - created at {discord.utils.format_dt(to_delete["added_time"], style="R")}'
            f'\n\u200b  → {to_delete["text"][0:1900]}{"..." if len(to_delete["text"]) > 1900 else ""}')

    @todo.command(name='edit')
    async def todo_edit(self, ctx: CustomContext, index: int, text: commands.clean_content):
        """ Edits one of your to​do list entries """
        entries = await self.bot.db.fetch(
            'SELECT text, added_time FROM todo WHERE user_id = $1 ORDER BY added_time ASC', ctx.author.id)
        try:
            to_delete = entries[index - 1]
        except KeyError:
            raise commands.BadArgument(f'⚠ **|** You do not have a task with index **{index}**')

        await self.bot.db.execute('UPDATE todo SET text = $4, jump_url = $3 WHERE user_id = $1 AND text = $2',
                                  ctx.author.id, to_delete['text'], ctx.message.jump_url, text)

        return await ctx.send(
            f'✏ **|** **Modified** task number **{index}**! - created at {discord.utils.format_dt(to_delete["added_time"], style="R")}'
            f'\n\u200b  → {text[0:1900]}{"..." if len(to_delete["text"]) > 1900 else ""}')

    @commands.command()
    async def hoisters(self, ctx: CustomContext):
        """ Shows a sorted list of members that have a nicknname """
        members = sorted([m for m in ctx.guild.members if m.nick], key=lambda mem: mem.display_name)
        source = paginator.SimplePageSource(
            [f"`{m.id}` <:separator:902081402831523850> {discord.utils.escape_markdown(m.nick)}" for m in members],
            per_page=10)
        pages = paginator.ViewPaginator(source=source, ctx=ctx, compact=True)
        await pages.start()

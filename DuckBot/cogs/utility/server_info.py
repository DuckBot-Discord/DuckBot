import contextlib
import random
import typing
from typing import Optional

import discord
import humanize
import tabulate
from discord.ext import commands
from jishaku.paginators import WrappedPaginator

from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.cogs.guild_config import GuildConfig
from DuckBot.helpers import constants, paginator
from DuckBot.helpers import helper
from ._base import UtilityBase


def get_sorted_mapping(
    guild: discord.Guild,
) -> typing.Dict[Optional[discord.CategoryChannel], typing.List[discord.abc.GuildChannel]]:
    mapping = {
        None: sorted(
            [c for c in guild.channels if not isinstance(c, discord.CategoryChannel) and not c.category],
            key=lambda c: c.position,
        )
    }
    for c in sorted(guild.categories, key=lambda c: c.position):
        mapping[c] = sorted(
            c.channels,
            key=lambda c: c.position if not isinstance(c, discord.VoiceChannel) else c.position + len(guild.channels),
        )

    return mapping


def get_channel_positions(ctx: CustomContext, guild: discord.Guild, member_counts: bool = False) -> typing.Dict[str, str]:
    sorted_channels = []
    for category, channels in get_sorted_mapping(guild).items():
        if category:
            sorted_channels.append(
                (f"📚 {category}", '✅ --' if category.permissions_for(ctx.author).read_messages else '❌ --')
            )
        for channel in channels:
            if member_counts:
                if not isinstance(channel, discord.VoiceChannel):
                    sorted_channels.append(
                        (
                            f"📑 {channel}",
                            ('✅ ' if channel.permissions_for(ctx.author).view_channel else '❌ ') + f"{len(channel.members)}",
                        )
                    )
                else:
                    mem_count = [m for m in channel.guild.members if channel.permissions_for(m).read_messages]
                    sorted_channels.append(
                        (
                            f"🔊 {channel}",
                            ('✅ ' if channel.permissions_for(ctx.author).view_channel else '❌ ') + f"{len(mem_count)}",
                        )
                    )
            else:
                if not isinstance(channel, discord.VoiceChannel):
                    sorted_channels.append(
                        (f"📑 {channel}", ('✅ ' if channel.permissions_for(ctx.author).view_channel else '❌ ') + f"N/A")
                    )
                else:
                    sorted_channels.append(
                        (f"🔊 {channel}", ('✅ ' if channel.permissions_for(ctx.author).view_channel else '❌ ') + f"N/A")
                    )
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
        previous = self.view.change_style.disabled
        self.view.change_style.disabled = True
        self.view.callback.disabled = True
        self.view.callback.placeholder = 'Loading Channel Data...'
        self.view._end.disabled = True
        await interaction.response.edit_message(view=self.view)

        channels = await self.ctx.bot.loop.run_in_executor(None, get_channel_positions, self.ctx, self.guild, True)

        self.view.channels = channels
        self.view._end.disabled = False
        self.view._end.emoji = '🛑'
        self.view.change_style.disabled = previous
        self.view.callback.disabled = False
        self.view.callback.placeholder = 'Select a category to view...'
        self.view.remove_item(self)

        embed = self.view.generate_channels_embed()
        if self.view.current == self.view.channels_embed:
            self.view.current = embed
        self.view.channels_embed = embed

        if self.view.callback.values and self.view.callback.values[0] == 'channels':
            return await self.view.message.edit(embed=self.view.channels_embed, view=self.view)
        await self.view.message.edit(view=self.view)


class ServerInfoView(discord.ui.View):
    def __init__(self, ctx: CustomContext, *, guild: discord.Guild):
        super().__init__()
        self.channels: typing.List[discord.abc.GuildChannel] = []
        self.guild = guild
        self.ctx = ctx
        self.bot: DuckBot = ctx.bot
        self.current: Optional[discord.Embed] = None
        self.message: Optional[discord.Message] = None
        self.main_embed: Optional[discord.Embed] = None
        self.roles_embed: Optional[discord.Embed] = None
        self.invite_embed: Optional[discord.Embed] = None
        self.members_embed: Optional[discord.Embed] = None
        self.channels_embed: Optional[discord.Embed] = None
        self.is_on_mobile = self.ctx.author.is_on_mobile()
        self.emotes = {False: constants.statuses.IDLE_MOBILE, True: constants.statuses.IDLE}
        self.item_added = False

    @discord.ui.select(
        placeholder="Loading data, please wait...",
        options=[
            discord.SelectOption(label='Main Page', value='main_page', description='View the main page', emoji='📋'),
            discord.SelectOption(label='Roles', value='roles', description='View the roles', emoji='🎭'),
            discord.SelectOption(label='Members', value='members', description='View the members', emoji='👥'),
            discord.SelectOption(label='Channels', value='channels', description='View the channels', emoji='📚'),
            discord.SelectOption(label='Invites', value='invite', description='View invite stats', emoji='🔗'),
        ],
        disabled=True,
    )
    async def callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.change_style.disabled = True
        self.change_style.style = discord.ButtonStyle.grey
        if select.values[0] == "main_page":
            self.current = self.main_embed
        elif select.values[0] == "roles":
            self.current = self.roles_embed
            self.change_style.disabled = False
            self.change_style.style = discord.ButtonStyle.blurple
        elif select.values[0] == "members":
            self.current = self.members_embed
        elif select.values[0] == "channels":
            self.current = self.channels_embed
            self.change_style.disabled = False
            self.change_style.style = discord.ButtonStyle.blurple
        elif select.values[0] == "invite":
            self.current = self.invite_embed
        await interaction.response.edit_message(embed=self.current, view=self)

    @discord.ui.button(emoji='<a:loading:747680523459231834>', style=discord.ButtonStyle.danger, disabled=True)
    async def _end(self, interaction: discord.Interaction, _):
        with contextlib.suppress(discord.HTTPException):
            await interaction.message.delete()
            await self.ctx.message.add_reaction(random.choice(constants.DONE))
        self.stop()

    @discord.ui.button(emoji=constants.TYPING_INDICATOR, style=discord.ButtonStyle.grey, disabled=True)
    async def change_style(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.is_on_mobile = not self.is_on_mobile

        button.emoji = self.emotes[self.is_on_mobile]

        if self.current in (self.main_embed, self.members_embed, self.invite_embed):
            await self.fix_mobile_embeds()
            await interaction.response.edit_message(embed=self.current, view=self)

        elif self.current == self.roles_embed:
            await self.fix_mobile_embeds()
            self.current = self.roles_embed
            await interaction.response.edit_message(embed=self.current, view=self)

        elif self.current == self.channels_embed:
            await self.fix_mobile_embeds()
            self.current = self.channels_embed
            await interaction.response.edit_message(embed=self.current, view=self)

        else:
            await self.fix_mobile_embeds()
            self.current = None
            error_embed = discord.Embed(
                title="Error",
                description="Something went wrong, please select a category" "\nusing the dropdown menu below.",
                colour=self.ctx.colour,
            )
            await interaction.response.edit_message(embed=error_embed, view=self)

    async def on_timeout(self) -> None:
        if self.message:
            self.clear_items()
            await self.message.edit(view=self)

    async def start(self):
        self.message = await self.ctx.send(
            embed=discord.Embed(title='<a:loading:747680523459231834> Loading...'), footer=False
        )
        self.main_embed = await self.bot.loop.run_in_executor(None, self.generate_main_embed)
        self.current = self.main_embed
        self.change_style.emoji = self.emotes[self.is_on_mobile]
        self.message = await self.message.edit(embed=self.main_embed, view=self)
        await self.build_embeds()
        self.callback.disabled = False
        self.callback.placeholder = 'Select a category to view...'
        self._end.disabled = False
        self._end.emoji = '🛑'
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

    async def fix_mobile_embeds(self):
        self.roles_embed = await self.bot.loop.run_in_executor(None, self.generate_roles_embed)
        self.channels_embed = await self.bot.loop.run_in_executor(None, self.generate_channels_embed)

    def generate_main_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx

        enabled_features = []
        features = set(guild.features)

        for feature, label in constants.GUILD_FEATURES.items():
            if feature in features:
                enabled_features.append(f'{ctx.tick(True)} {label}')

        embed = discord.Embed(title=guild.name, colour=ctx.colour, timestamp=ctx.message.created_at)

        embed.add_field(
            name=f"{constants.RICH_PRESENCE} Features:",
            value=(('\n'.join(enabled_features) if enabled_features else 'No features...') + '\n\u200b _ _'),
            inline=True,
        )

        embed.add_field(
            name=f"{constants.INFORMATION_SOURCE} General Info:",
            value=f"🆔 {guild.id}"
            f"\n{constants.OWNER_CROWN} {guild.owner}"
            f"\n🌐 Server Region:\n╰ {helper.get_server_region(guild)}"
            f"\n{constants.VERIFICATION_LEVEL[guild.verification_level]} "
            f"{str(guild.verification_level).replace('_', ' ').replace('none', 'no').title()} Verification Level"
            f"\n📁 File size limit: {humanize.naturalsize(guild.filesize_limit)}"
            f"\n{constants.ROLES_ICON} Role amount: {len(guild.roles)}"
            f"\n\u200b _ _",
        )

        embed.add_field(
            name=f"{constants.INFORMATION_SOURCE} Server description:",
            value=guild.description or f"{constants.TOGGLES[False]} Description disabled!",
            inline=False,
        )

        embed.add_field(
            name=f"{constants.JOINED_SERVER} Created at:",
            value=f"{discord.utils.format_dt(guild.created_at, 'F')} ({discord.utils.format_dt(guild.created_at, 'R')})",
            inline=False,
        )

        embed.add_field(
            name=f"{constants.VERIFICATION_LEVEL[guild.verification_level]} Server content filter:",
            value=f"{constants.CONTENT_FILTER[guild.explicit_content_filter]}\n\u200b _ _",
            inline=False,
        )

        embed.add_field(
            name=f"{constants.RICH_PRESENCE} Channels:",
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
            inline=True,
        )

        embed.add_field(
            name=f"{constants.EMOJI_GHOST} Emojis:",
            value=f"Static: {len([e for e in guild.emojis if not e.animated])}/{guild.emoji_limit} "
            f"\nAnimated: {len([e for e in guild.emojis if e.animated])}/{guild.emoji_limit} ",
            inline=True,
        )

        last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
        if last_boost.premium_since is not None:
            boost = f"\n{last_boost}" f"\n╰ {discord.utils.format_dt(last_boost.premium_since, style='R')}"
        else:
            boost = "\n╰ No active boosters"

        embed.add_field(
            name=f"{constants.BOOST} Boosts:",
            value=f"{constants.GUILD_BOOST_LEVEL_EMOJI[str(guild.premium_tier)]} Level: {guild.premium_tier}"
            f"\n╰ Amount: {guild.premium_subscription_count}"
            f"\n**{constants.BOOST} Last booster:**{boost}",
        )

        embed.add_field(
            name=f'👥 Member information:',
            value=f"\n👤 Humans: {len([m for m in guild.members if not m.bot])} "
            f"\n🤖 Bots: {len([m for m in guild.members if m.bot])}"
            f"\n♾ Total: {guild.member_count}"
            f"\n📂 Limit: {guild.max_members}",
        )
        embed.add_field(
            name=f"{constants.ROLES_ICON} Member statuses:",
            value=f"\n{constants.statuses.ONLINE} Online: {len(list(filter(lambda m: m.status == discord.Status.online, guild.members)))}"
            f"\n{constants.statuses.IDLE} Idle: {len(list(filter(lambda m: m.status == discord.Status.idle, guild.members)))}"
            f"\n{constants.statuses.DND} DND: {len(list(filter(lambda m: m.status == discord.Status.do_not_disturb, guild.members)))}"
            f"\n{constants.statuses.OFFLINE} Offline: {len(list(filter(lambda m: m.status == discord.Status.offline, guild.members)))}",
        )

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        return embed

    def generate_roles_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx
        embed = discord.Embed(title=guild.name, colour=ctx.colour)

        roles = [
            (r.name, f'{str(len(r.members))} <' if r in ctx.author.roles else str(len(r.members)))
            for r in sorted(guild.roles, key=lambda r: r.position, reverse=True)
        ]

        if self.is_on_mobile:
            pag = WrappedPaginator(prefix='Role Name and Member Count:\n```\n', suffix='\n```', max_size=4096)
            for line in (tabulate.tabulate(roles, headers=["Role Name", "Count"], tablefmt="presto")).split('\n'):
                pag.add_line(line)
            embed.description = pag.pages[0]
        else:
            pag = WrappedPaginator(prefix='```\n', suffix='\n```', max_size=1024)
            pag2 = WrappedPaginator(prefix='```\n', suffix='\n```', max_size=1024)
            for role, amount in roles:
                if len(pag._pages) < 1:
                    pag.add_line(role)
                    pag2.add_line(amount)
                else:
                    break
            embed.description = 'Role Name and Member Count:'
            embed.add_field(name='Role Name', value=pag.pages[0])
            embed.add_field(name='Count', value=pag2.pages[0])

        embed.add_field(
            name="Your Roles",
            inline=False,
            value=f"You have {len(ctx.author.roles)} (signified by `<`)" f"\nYour top role: {ctx.author.top_role.mention}",
        )

        warntext = f"If on mobile, press the blue button to fix the columns"
        if self.is_on_mobile:
            warntext = "If on computer, press the blue button for better fomatting"
        embed.set_footer(text=warntext)
        return embed

    def generate_members_embed(self) -> discord.Embed:
        guild = self.guild
        ctx = self.ctx
        embed = discord.Embed(title=guild.name, colour=ctx.colour, timestamp=ctx.message.created_at)

        sort_mems = sorted(ctx.guild.members, key=lambda m: m.joined_at or ctx.message.created_at)

        index = 0
        members = [f'{m} ({m.joined_at.strftime("%d %b %Y. %H:%M")})' for m in sort_mems[:5]]
        join_order = [f"{n}.{' ' * (7 - len(str(n)) + 1)}{s}" for n, s in enumerate(members, start=index + 1)]

        embed.add_field(
            name=f"👥 First Members and Join Date:", inline=False, value='```py\n' + '\n'.join(join_order) + '\n```'
        )

        index = len(sort_mems)
        members = [f'{m} ({m.joined_at.strftime("%d %b %Y. %H:%M")})' for m in sort_mems[-5:]]
        join_order = [f"{n}.{' ' * (7 - len(str(n)) + 1)}{s}" for n, s in enumerate(members, start=index - 5)]

        embed.add_field(
            name=f"👥 Recent Members and Join Date:", inline=False, value='```py\n' + '\n'.join(join_order) + '\n```'
        )

        if guild.premium_subscribers:
            index = len(guild.premium_subscribers)
            sort_subs = sorted(guild.premium_subscribers, key=lambda m: m.premium_since or m.created_at, reverse=True)
            boosters = [f"{m} ({m.premium_since.strftime('%d %b %Y. %H:%M')})" for m in sort_subs[:5]]
            boosters.reverse()
            boost_order = '\n'.join([f"{n}.{' ' * (7 - len(str(n)) + 1)}{s}" for n, s in enumerate(boosters, start=index)])
            embed.add_field(
                name=f"💎 Recent Boosters:",
                inline=False,
                value='```py\n' + boost_order + '\n```' + f'**Boosts** {guild.premium_subscription_count} • '
                f'**Boosters** {len(guild.premium_subscribers)}',
            )

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
                if not self.item_added:
                    self.item_added = True
                    self.add_item(GenerateChannels(ctx, guild=guild))
                channels = get_channel_positions(self.ctx, self.guild, member_counts=False)
        else:
            channels = self.channels

        if self.is_on_mobile:
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

        warntext = f"If on mobile, press the blue button to fix the columns"
        if self.is_on_mobile:
            warntext = "If on computer, press the blue button for better fomatting"
        embed.set_footer(
            text=f"{warntext}"
            f"\n📚: Category • 📑: Text Channel • 🔊: Voice Channel"
            f"\n✅ - Channels you have access to."
            f"\n❌ - Channels you don't have access to."
        )
        return embed

    async def generate_invite_embed(self) -> discord.Embed:
        cog: GuildSettings = self.bot.get_cog('Guild Settings')
        try:
            return await cog.invitestats(self.ctx, return_embed=True)
        except commands.BotMissingPermissions:
            embed = discord.Embed(
                title="Invite Stats", colour=self.ctx.colour, description="I don't have the `Manage Server` permission."
            )
            embed.set_footer(text=f"Requested by {self.ctx.author}", icon_url=self.ctx.author.display_avatar.url)
        except Exception as e:
            embed = discord.Embed(title="Invite Stats", colour=self.ctx.colour, description=f"Something went wrong.\n{e}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.defer()
        return False


class ServerInfo(UtilityBase):
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

    @commands.command()
    async def hoisters(self, ctx: CustomContext):
        """Shows a sorted list of members that have a nicknname"""
        members = sorted([m for m in ctx.guild.members if m.nick], key=lambda mem: mem.display_name)
        source = paginator.SimplePageSource(
            [f"`{m.id}` <:separator:902081402831523850> {discord.utils.escape_markdown(m.nick)}" for m in members],
            per_page=10,
        )
        pages = paginator.ViewPaginator(source=source, ctx=ctx, compact=True)
        await pages.start()

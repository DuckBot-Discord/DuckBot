import logging
import typing

import discord
import discord.http
from discord.ext import commands
from discord.utils import format_dt

from bot import DuckBot
from utils import DuckCog, DuckContext, PartiallyMatch, command
from utils.types import constants

from .perms import PermsEmbed

type_mapping = {
    discord.ActivityType.unknown: "Playing",
    discord.ActivityType.playing: "Playing",
    discord.ActivityType.streaming: "Streaming",
    discord.ActivityType.listening: "Listening to",
    discord.ActivityType.watching: "Watching",
    discord.ActivityType.competing: "Competing in",
    discord.ActivityType.custom: "",
}


def generate_user_statuses(member: discord.Member):
    mobile = {
        discord.Status.online: constants.statuses.ONLINE_MOBILE,
        discord.Status.idle: constants.statuses.IDLE_MOBILE,
        discord.Status.dnd: constants.statuses.DND_MOBILE,
        discord.Status.offline: constants.statuses.OFFLINE_MOBILE,
    }[member.mobile_status]
    web = {
        discord.Status.online: constants.statuses.ONLINE_WEB,
        discord.Status.idle: constants.statuses.IDLE_WEB,
        discord.Status.dnd: constants.statuses.DND_WEB,
        discord.Status.offline: constants.statuses.OFFLINE_WEB,
    }[member.web_status]
    desktop = {
        discord.Status.online: constants.statuses.ONLINE,
        discord.Status.idle: constants.statuses.IDLE,
        discord.Status.dnd: constants.statuses.DND,
        discord.Status.offline: constants.statuses.OFFLINE,
    }[member.desktop_status]
    return f"\u200b{desktop}\u200b{web}\u200b{mobile}"


def get_perms(permissions: discord.Permissions):
    if permissions.administrator:
        return ['Administrator']
    wanted_perms = dict({x for x in permissions if x[1] is True} - set(discord.Permissions(521942715969)))
    return [p.replace('_', ' ').replace('guild', 'server').title() for p in wanted_perms]


def deltaconv(s):
    hours = s // 3600
    s = s - (hours * 3600)
    minutes = s // 60
    seconds = s - (minutes * 60)
    if hours > 0:
        return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
    return '{:02}:{:02}'.format(int(minutes), int(seconds))


async def get_user_badges(
    user: typing.Union[discord.Member, discord.User],
    bot: DuckBot,
    fetched_user: discord.User | None = None,
):
    flags = dict(user.public_flags)

    user_flags = []
    for flag, text in constants.USER_FLAGS.items():
        try:
            if flags[flag] and text:
                user_flags.append(text)
        except KeyError:
            logging.warning(f"Flag {flag} was not a part of the constants.USER_FLAGS dict.")
    is_avatar_animated = user.avatar.is_animated() if user.avatar else False or user.display_avatar.is_animated()
    if is_avatar_animated:
        user_flags.append(f'{constants.NITRO} Nitro')

    elif fetched_user and fetched_user.banner:
        user_flags.append(f'{constants.NITRO} Nitro')

    elif isinstance(user, discord.Member) and user.premium_since:
        user_flags.append(f'{constants.NITRO} Nitro')

    if isinstance(user, discord.Member):
        if user.id == user.guild.owner_id:
            user_flags.append(f'{constants.OWNER_CROWN} Server Owner')

    if user.bot:
        user_flags.append(f'{constants.BOT} Bot')

    badges = await bot.pool.fetch(
        """
        SELECT name, emoji FROM badges WHERE badge_id IN
        (SELECT badge_id FROM acknowledgements WHERE user_id = $1)
    """,
        user.id,
    )
    for name, emoji in badges:
        user_flags.append(f'{emoji} {name}')

    return '\n'.join(user_flags) if user_flags else None


class BaseEmbed(discord.Embed):
    def __init__(self, **kwargs):
        user = kwargs.pop('user')
        super().__init__(**kwargs)
        self.set_thumbnail(url=user.display_avatar.url)
        self.set_author(name=str(user), icon_url=(user.avatar or user.display_avatar).url)


class UserInfoViewer(discord.ui.View):
    def __init__(
        self,
        user: typing.Union[discord.Member, discord.User],
        /,
        *,
        bot: DuckBot,
        author: typing.Union[discord.Member, discord.User],
        color: discord.Colour | None = None,
    ):
        super().__init__()
        self.user = user
        self.bot = bot
        self.author = author
        self.color = color or bot.color
        self.message: typing.Optional[discord.Message] = None
        self.fetched: typing.Optional[discord.User] = None
        self._main_embed: typing.Optional[typing.List[BaseEmbed]] = None
        self._perms_embed: typing.Optional[typing.List[PermsEmbed]] = None
        self._assets_embeds: typing.Optional[typing.List[discord.Embed]] = None

    async def fetch_user(self):
        if not self.fetched:
            self.fetched = await self.bot.fetch_user(self.user.id)
        return self.fetched

    async def make_main_embed(self) -> typing.List[BaseEmbed]:
        if self._main_embed is not None:
            return self._main_embed

        user = self.user
        embed = BaseEmbed(title='\N{SCROLL} User Info Main Page', color=self.color, user=user)
        is_member = isinstance(user, discord.Member)

        general = [f"**ID:** {user.id}", f"**Username:** {user.name}"]

        if is_member and user.nick:
            general.append(f"╰ **Nick:** {user.nick}")

        embed.add_field(name=f'{constants.INFORMATION_SOURCE} General', value='\n'.join(general), inline=True)

        embed.add_field(
            name=f'{constants.STORE_TAG} Badges / DuckBadges',
            value=await get_user_badges(user, self.bot, await self.fetch_user()),
        )

        embed.add_field(
            name=f"{constants.INVITE} Created At",
            inline=False,
            value=f"╰ {format_dt(user.created_at)} ({format_dt(user.created_at, 'R')})",
        )

        if is_member and user.joined_at:
            text = f"╰ {format_dt(user.joined_at)} ({format_dt(user.joined_at, 'R')})"
        else:
            text = "╰ This user is not a member of this server."
        embed.add_field(name=f"{constants.JOINED_SERVER} Joined At", value=text, inline=False)

        if is_member and user.premium_since:
            embed.add_field(
                name=f"{constants.BOOST} Boosting since",
                inline=False,
                value=f"╰ {format_dt(user.premium_since)} ({format_dt(user.premium_since, 'R')})",
            )

        if is_member:
            custom_st = discord.utils.find(lambda a: isinstance(a, discord.CustomActivity), user.activities)
            if custom_st and isinstance(custom_st, discord.CustomActivity):
                emoji = f"{custom_st.emoji} " if custom_st.emoji and custom_st.emoji.is_unicode_emoji() else ''
                extra = f"\n**Custom Status**\n{emoji}`{discord.utils.remove_markdown(custom_st.name or '')}`"
            else:
                extra = ''
            embed.add_field(name=f"{constants.STORE_TAG} Status", value=f"{generate_user_statuses(user)}{extra}")

            spotify = discord.utils.find(lambda a: isinstance(a, discord.Spotify), user.activities)
            if isinstance(spotify, discord.Spotify):
                embed.add_field(
                    name=f"{constants.SPOTIFY} Spotify",
                    value=f"**[{spotify.title}]({spotify.track_url})**"
                    f"\n**By** {spotify.artist}"
                    f"\n**On** {spotify.album}",
                )

            roles = [r.mention for r in user.roles if not r.is_default()]
            roles.reverse()
            if roles:
                embed.add_field(
                    name=f"{constants.ROLES_ICON} Roles",
                    value=", ".join(roles) + f"\n**Top Role:** {user.top_role.mention} • "
                    f"**Color:** {user.color if user.color is not discord.Color.default() else 'Default'}",
                    inline=False,
                )

        embeds = [embed]
        self._main_embed = embeds
        return embeds

    async def make_perms_embed(self):
        if self._perms_embed:
            return self._perms_embed

        user = self.user
        if isinstance(user, discord.Member):
            embed = PermsEmbed(entity=user, permissions=user.guild_permissions)
            embed.colour = self.color
            embed.title = '\N{SCROLL} Server Permissions Page'
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_author(name=str(user), icon_url=(user.avatar or user.display_avatar).url)
            embeds = [embed]
            self._perms_embed = embeds
            return embeds
        else:
            return [BaseEmbed(user=user, description="User is not a part of this server.")]

    async def make_asset_embeds(self):
        if self._assets_embeds:
            return self._assets_embeds
        embeds: list[discord.Embed] = []
        fetched_user = await self.fetch_user()
        user = self.user

        if user.avatar:
            embeds.append(discord.Embed(title="Avatar", color=self.bot.color).set_image(url=user.display_avatar.url))
        if user.display_avatar != fetched_user.display_avatar:
            embeds.append(discord.Embed(title="Server Avatar", color=self.bot.color).set_image(url=user.display_avatar.url))
        if fetched_user.banner:
            embeds.append(discord.Embed(title="Banner", color=self.bot.color).set_image(url=fetched_user.banner.url))
        self._assets_embeds = embeds
        return embeds

    @discord.ui.select(
        cls=discord.ui.Select,
        options=[
            discord.SelectOption(
                label='Main Page',
                value='main',
                emoji='\N{BUSTS IN SILHOUETTE}',
                description='Basic info, join dates, badges, status, etc.',
            ),
            discord.SelectOption(
                label='Permissions',
                value='perms',
                emoji='\N{INFORMATION SOURCE}',
                description='The user\'s server permissions.',
            ),
            discord.SelectOption(
                label='Assets',
                value='assets',
                emoji='🎨',
                description="Profile pictures, and banner.",
            ),
            discord.SelectOption(
                label='Stop & Close',
                value='stop',
                emoji='\N{OCTAGONAL SIGN}',
                description="Deletes this message.",
            ),
        ],
    )
    async def select(self, interaction: discord.Interaction[DuckBot], select: discord.ui.Select):
        value = select.values[0]
        if value == 'main':
            embeds = await self.make_main_embed()
        elif value == 'perms':
            embeds = await self.make_perms_embed()
        elif value == 'assets':
            embeds = await self.make_asset_embeds()
        else:
            self.stop()
            await interaction.response.defer()
            await interaction.delete_original_response()
            return

        await interaction.response.edit_message(embeds=embeds)

    async def interaction_check(self, interaction: discord.Interaction[DuckBot]) -> bool:
        return interaction.user == self.author

    async def start(self, ctx):
        self.message = await ctx.send(embeds=await self.make_main_embed(), view=self)
        ctx.bot.views.add(self)

    async def on_timeout(self) -> None:
        self.bot.views.discard(self)
        if self.message:
            await self.message.edit(view=None)

    def stop(self) -> None:
        self.bot.views.discard(self)
        super().stop()


class UserInfo(DuckCog):
    @command(name='userinfo', aliases=['info', 'ui', 'user-info', 'whois'])
    async def user_info(self, ctx: DuckContext, *, user: PartiallyMatch[discord.Member, discord.User] = commands.Author):
        """Displays information about a user or member

        Parameters
        ----------
        user: Union[:class:`discord.Member`, :class:`discord.User`]
            The user or member you want to get info about.
            If None is passed, it will get info about you.
        """
        await ctx.typing()
        await UserInfoViewer(user, bot=ctx.bot, author=ctx.author, color=ctx.color).start(ctx)

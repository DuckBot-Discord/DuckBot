import datetime
import logging
import typing

import asyncio
import discord
from discord.ext import commands
from discord.utils import format_dt

from bot import DuckBot
from utils import DuckContext, DuckCog, constants, human_join

from .perms import PermsEmbed

pronoun_mapping = {
    "unspecified": "Unspecified __[(set one)](https://pronoundb.org/)__",
    "hh": "He/Him",
    "hi": "He/It",
    "hs": "He/She",
    "ht": "He/They",
    "ih": "It/Him",
    "ii": "It/Its",
    "is": "It/She",
    "shh": "She/He",
    "sh": "She/Her",
    "si": "She/It",
    "st": "She/They",
    "th": "They/He",
    "ti": "They/It",
    "ts": "They/She",
    "tt": "They/Them",
    "any": "Any Pronouns",
    "other": "Other Pronouns",
    "ask": "Ask Me",
    "avoid": "Avoid pronouns, use my name!",
}

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
        discord.Status.offline: constants.statuses.OFFLINE_MOBILE
    }[member.mobile_status]
    web = {
        discord.Status.online: constants.statuses.ONLINE_WEB,
        discord.Status.idle: constants.statuses.IDLE_WEB,
        discord.Status.dnd: constants.statuses.DND_WEB,
        discord.Status.offline: constants.statuses.OFFLINE_WEB
    }[member.web_status]
    desktop = {
        discord.Status.online: constants.statuses.ONLINE,
        discord.Status.idle: constants.statuses.IDLE,
        discord.Status.dnd: constants.statuses.DND,
        discord.Status.offline: constants.statuses.OFFLINE
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


async def get_user_badges(user: typing.Union[discord.Member, discord.User], bot: DuckBot,
                          fetched_user: discord.User = None):
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
        user_flags.append(f'{constants.NITRO} Nitro [guess: Boosting]')

    elif user.discriminator in constants.COMMON_DISCRIMINATORS:
        user_flags.append(f'{constants.NITRO} Nitro [guess: Rare #tag]')

    if isinstance(user, discord.Member):
        if user.id == user.guild.owner_id:
            user_flags.append(f'{constants.OWNER_CROWN} Server Owner')

    if user.bot:
        user_flags.append(f'{constants.BOT} Bot')

    badges = await bot.pool.fetch("""
        SELECT name, emoji FROM badges WHERE badge_id IN 
        (SELECT badge_id FROM acknowledgements WHERE user_id = $1)
    """, user.id)
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
    def __init__(self, user: typing.Union[discord.Member, discord.User], /, *, bot: DuckBot, author: discord.User,
                 color: discord.Colour = None):
        super().__init__()
        self.user = user
        self.bot = bot
        self.author = author
        self.color = color or bot.color
        self.message: typing.Optional[discord.Message] = None
        self.fetched: typing.Optional[discord.User] = None
        self._main_embed: typing.Optional[typing.List[discord.Embed]] = None
        self._perms_embed: typing.Optional[typing.List[discord.Embed]] = None

    async def make_main_embed(self) -> typing.List[discord.Embed]:
        if self._main_embed is not None:
            return self._main_embed

        user = self.user
        embed = BaseEmbed(title='\N{SCROLL} User Info Main Page', color=self.color, user=user)
        is_member = isinstance(user, discord.Member)
        is_avatar_animated = user.avatar.is_animated() if user.avatar else False or user.display_avatar.is_animated()

        if not user.bot and self.fetched is None:
            try:
                self.fetched = await self.bot.fetch_user(user.id)
            except discord.HTTPException:
                self.fetched = None
        else:
            self.fetched = False

        general = [
            f"**ID:** {user.id}",
            f"**Username:** {user.name}"
        ]

        if is_member and user.nick:
            general.append(f"╰ **Nick:** {user.nick}")

        try:
            _pr_resp = await self.bot.session.get('https://pronoundb.org/api/v1/lookup', timeout=1.5,
                                                  params=dict(platform='discord', id=user.id))
            _prs = await _pr_resp.json()
            pronouns = pronoun_mapping.get(_prs.get('pronouns', 'unspecified'), 'Unknown...')
            general.append(f'**Pronouns:** {pronouns}')
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logging.debug(f'Failed to get pronouns for {user}, ignoring', exc_info=e)

        if is_member:
            top_role = user.top_role if not user.top_role.is_default() else None
            if top_role:
                general.append(f"**Top Role:** {top_role.mention}")

        embed.add_field(name=f'{constants.INFORMATION_SOURCE} General', value='\n'.join(general), inline=True)

        embed.add_field(name=f'{constants.STORE_TAG} Badges / DuckBadges',
                        value=await get_user_badges(user, self.bot, self.fetched))

        embed.add_field(name=f"{constants.INVITE} Created At", inline=False,
                        value=f"╰ {format_dt(user.created_at)} ({format_dt(user.created_at, 'R')})")

        if is_member:
            text = f"╰ {format_dt(user.joined_at)} ({format_dt(user.joined_at, 'R')})"
        else:
            text = "╰ This user is not a member of this server."
        embed.add_field(name=f"{constants.JOINED_SERVER} Joined At", value=text, inline=False)

        if is_member and user.premium_since:
            embed.add_field(name=f"{constants.BOOST} Boosting since", inline=False,
                            value=f"╰ {format_dt(user.premium_since)} ({format_dt(user.premium_since, 'R')})")

        if is_member:
            now = discord.utils.utcnow()
            custom_st = discord.utils.find(lambda a: isinstance(a, discord.CustomActivity), user.activities)
            if custom_st:
                emoji = f"{custom_st.emoji} " if custom_st.emoji and custom_st.emoji.is_unicode_emoji() else ''
                extra = f"\n**Custom Status:**\n{emoji}`{discord.utils.remove_markdown(custom_st.name)}`"
            else:
                extra = ''
            embed.add_field(name=f"{constants.STORE_TAG} Status:", value=f"{generate_user_statuses(user)}{extra}")

            spotify = discord.utils.find(lambda a: isinstance(a, discord.Spotify), user.activities)
            if spotify:
                embed.add_field(name=f"{constants.FULL_SPOTIFY}\u200b",
                                value=f"**[{spotify.title}]({spotify.track_url})**"
                                      f"\n**By** {spotify.artist}"
                                      f"\n**On** {spotify.album}"
                                      f"\n**Time:** {deltaconv((now - spotify.start).total_seconds())}/"
                                      f"{deltaconv(spotify.duration.total_seconds())}")

        embeds = [embed]
        self._main_embed = embeds
        return embeds

    async def make_perm_embeds(self) -> typing.List[discord.Embed]:
        if self._perms_embed:
            return self._perms_embed
        user = self.user
        embed = PermsEmbed(entity=user, permissions=user.guild_permissions)
        embed.colour = self.color
        embed.title = '\N{SCROLL} Server Permissions Page'
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=str(user), icon_url=(user.avatar or user.display_avatar).url)
        embeds = [embed]
        self._perms_embed = embeds
        return embeds

    @discord.ui.select(options=[
        discord.SelectOption(label='Main Page', value='main', emoji='\N{BUSTS IN SILHOUETTE}',
                             description='Basic info, join dates, badges, status, etc.'),
        discord.SelectOption(label='Permissions', value='perms', emoji='\N{INFORMATION SOURCE}',
                             description='Global permissions for this user.'),
        discord.SelectOption(label='Assets', value='assets', emoji='🎨',
                             description="The user's assets, such as their profile picture, banner, etc."),
        discord.SelectOption(label='Roles', value='roles', emoji=constants.ROLES_ICON,
                             description="All information about this user's roles.")
    ])
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = select.values[0]
        if value == 'main':
            embeds = await self.make_main_embed()
            await interaction.response.edit_message(embeds=embeds)
        elif value == 'perms':
            embeds = await self.make_perm_embeds()
            await interaction.response.edit_message(embeds=embeds)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author

    async def start(self, ctx):
        self.message = await ctx.send(embeds=await self.make_main_embed(), view=self)
        ctx.bot.views.add(self)
    
    async def on_timeout(self) -> None:
        self.bot.views.discard(self)
        if self.message:
            await self.message.delete()

    def stop(self) -> None:
        self.bot.views.discard(self)
        super().stop()

class UserInfo(DuckCog):

    @commands.command(name='userinfo', aliases=['info', 'ui', 'user-info', 'whois'])
    async def user_info(self, ctx: DuckContext, *, user: typing.Union[discord.Member, discord.User] = None):
        """|coro|

        Displays information about a user or member

        Parameters
        ----------
        user: Union[:class:`discord.Member`, :class:`discord.User`]
            The user or member you want to get info about.
            If None is passed, it will get info about you.
        """
        user = user or ctx.author
        ctx.bot.create_task(ctx.trigger_typing())
        await UserInfoViewer(user, bot=ctx.bot, author=ctx.author, color=ctx.color).start(ctx)



"""
            spotify = None
            index = 0
            formatted_activities = []
            for activity in user.activities:
                if isinstance(activity, discord.Spotify):
                    # We don't increment index for spotify.
                    spotify = activity
                elif isinstance(activity, discord.Activity):
                    index += 1

                    formatted = f"`{index}.` {type_mapping.get(activity.type)} {activity.name}"
                    formatted_activities.append(formatted)

                elif isinstance(activity, discord.Game):
                    index += 1

                    formatted = f"`{index}.` Streaming **{activity.name}**"
                    if activity.start:
                        formatted += f" {format_dt(activity.start)}"
                    formatted_activities.append(formatted)

                elif isinstance(activity, discord.Streaming):
                    index += 1

                    formatted = f"`{index}.` Streaming **[{activity.name}]({activity.url})**"
                    if activity.game:
                        formatted += f"\n╰ Currently playing **{activity.game}**"
                    formatted_activities.append(formatted)

                elif isinstance(activity, discord.CustomActivity):
                    index += 1
                    emoji = activity.emoji if activity.emoji and activity.emoji.is_unicode_emoji() else ''
                    formatted = f"`{index}.` **Custom Status**: {emoji} {activity.name}"
                    formatted_activities.append(formatted)

            formatted_activities.append(f"**Status:** {generate_user_statuses(user)}")

            embed.add_field(name=f"{constants.STORE_TAG} Activities",
                            value='\n'.join(formatted_activities))
"""

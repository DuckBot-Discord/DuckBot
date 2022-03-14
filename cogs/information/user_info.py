import logging
import typing

import discord
from discord.ext import commands
from discord.utils import format_dt

from bot import DuckBot
from utils import DuckContext, DuckCog, constants

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
        print('this triggered')
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
        ctx.bot.create_task(ctx.trigger_typing())
        user = user or ctx.author
        embed = discord.Embed(title='User Info', color=ctx.color)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=str(user), icon_url=(user.avatar or user.display_avatar).url)

        is_member = isinstance(user, discord.Member)

        is_avatar_animated = user.avatar.is_animated() if user.avatar else False or user.display_avatar.is_animated()
        if not user.bot and not is_avatar_animated:
            fetched = await ctx.bot.fetch_user(user.id)
        else:
            fetched = None

        general = [f"**ID:** {user.id}",
                   f"**Username:** {user.name}"]
        if is_member and user.nick:
            general.append(f"╰ **Nick:** {user.nick}")
        try:
            _pr_resp = await self.bot.session.get('https://pronoundb.org/api/v1/lookup',
                                                  params=dict(platform='discord', id=user.id))
            _prs = await _pr_resp.json()
            pronouns = pronoun_mapping.get(_prs.get('pronouns', 'unspecified'), 'Unknown...')
            general.append(f'**Pronouns:** {pronouns}')
        except Exception as e:
            logging.debug(f'Failed to get pronouns for {user}, ignoring', exc_info=e)

        embed.add_field(name=f'{constants.INFORMATION_SOURCE} General', value='\n'.join(general), inline=True)

        embed.add_field(name=f'{constants.STORE_TAG} Badges / DuckBadges',
                        value=await get_user_badges(user, ctx.bot, fetched))

        embed.add_field(name=f"{constants.INVITE} Created At", inline=False,
                        value=f"╰ {format_dt(user.created_at)} ({format_dt(user.created_at, 'R')})")

        if is_member:
            text = f"╰ {format_dt(user.joined_at)} ({format_dt(user.joined_at, 'R')})"
            try:
                pos = sorted(user.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow()).index(user) + 1
                text += f"\n\u200b \u200b \u200b \u200b ╰ {constants.MOVED_CHANNELS} **Join Position:** {pos}"
            except ValueError:
                pass
        else:
            text = "╰ This user is not a member of this server."
        embed.add_field(name=f"{constants.JOINED_SERVER} Joined At", value=text, inline=False)

        if is_member and user.premium_since:
            embed.add_field(name=f"{constants.BOOST} Boosting since", inline=False,
                            value=f"╰ {format_dt(user.premium_since)} ({format_dt(user.premium_since, 'R')})")

        if is_member:
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

            if spotify:
                embed.add_field(name=f"{constants.SPOTIFY} Spotify:",
                                value=f"**[{spotify.title}]({spotify.track_url})**"
                                      f"\n**By** {spotify.artist}"
                                      f"\n**On** {spotify.album}"
                                      f"\n**Time:** {deltaconv((ctx.message.created_at - spotify.start).total_seconds())}/"
                                      f"{deltaconv(spotify.duration.total_seconds())}")

            perms = get_perms(user.guild_permissions)
            if perms:
                embed.add_field(name=f"{constants.STORE_TAG} Staff Perms:",
                                value=f"`{'` `'.join(perms)}`", inline=False)

        await ctx.send(embed=embed)

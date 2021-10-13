import os

import aiofiles
import discord
import typing
from discord import VoiceRegion

from DuckBot.__main__ import DuckBot
from DuckBot.helpers import constants


def get_perms(permissions: discord.Permissions):
    if permissions.administrator:
        return ['Administrator']
    return [p.replace('_', ' ').replace('guild', 'server').title()
            for p in dict({x for x in set(permissions) if x[1] is True} - set(discord.Permissions(521942724161)))]


def get_user_badges(user: discord.Member, bot: DuckBot, fetched_user: discord.User = None):
    flags = dict(user.public_flags)

    user_flags = []
    for flag, text in constants.USER_FLAGS.items():
        try:
            if flags[flag]:
                user_flags.append(text)
        except KeyError:
            continue

    if user.avatar.is_animated():
        user_flags.append(f'<:nitro:895392323519799306> Nitro')

    elif fetched_user and (fetched_user.accent_color or fetched_user.banner):
        user_flags.append(f'<:nitro:895392323519799306> Nitro')

    elif user.premium_since:
        user_flags.append(f'<:nitro:895392323519799306> Nitro [guess: Boosting]')

    elif user.discriminator in constants.COMMON_DISCRIMINATORS:
        print('this triggered')
        user_flags.append(f'<:nitro:895392323519799306> Nitro [guess: Nitro #tag]')

    elif user.discriminator in bot.common_discrims:
        print('this triggered')
        user_flags.append(f'<:nitro:895392323519799306> Nitro [guess: Nitro #tag]')

    else:
        pass

    return '\n'.join(user_flags) if user_flags else None


def get_server_region(guild: discord.Guild):
    r = discord.VoiceRegion.us_central
    region = guild.region

    if region == VoiceRegion.amsterdam:
        return "🇳🇱 Amsterdam"
    if region == VoiceRegion.brazil:
        return "🇧🇷 Brazil"
    if region == VoiceRegion.dubai:
        return "🇦🇪 Dubai"
    if region == VoiceRegion.eu_central:
        return "🇪🇺 EU central"
    if region == VoiceRegion.eu_west:
        return "🇪🇺 EU west"
    if region == VoiceRegion.europe:
        return "🇪🇺 Europe"
    if region == VoiceRegion.frankfurt:
        return "🇩🇪 Frankfurt"
    if region == VoiceRegion.hongkong:
        return "🇭🇰 Hong Kong"
    if region == VoiceRegion.india:
        return "🇮🇳 India"
    if region == VoiceRegion.japan:
        return "🇯🇵 Japan"
    if region == VoiceRegion.london:
        return "🇬🇧 London"
    if region == VoiceRegion.russia:
        return "🇷🇺 Russia"
    if region == VoiceRegion.singapore:
        return "🇸🇬 Singapore"
    if region == VoiceRegion.southafrica:
        return "🇿🇦 South Africa"
    if region == VoiceRegion.south_korea:
        return "🇰🇷 South Korea"
    if region == VoiceRegion.sydney:
        return "🇦🇺 Sydney"
    if region == VoiceRegion.us_central:
        return "🇺🇸 US Central"
    if region == VoiceRegion.us_east:
        return "🇺🇸 US East"
    if region == VoiceRegion.us_south:
        return "🇺🇸 US South"
    if region == VoiceRegion.us_west:
        return "🇺🇸 US West"
    if region == VoiceRegion.vip_amsterdam:
        return "🇳🇱🌟 VIP Amsterdam"
    if region == VoiceRegion.vip_us_east:
        return "🇺🇸🌟 VIP US East"
    if region == VoiceRegion.vip_us_west:
        return "🇺🇸🌟 VIP US West"
    if str(region) == 'atlanta':
        return "🇺🇸 Atlanta"
    if str(region) == 'santa-clara':
        return "🇺🇸 Santa Clara"
    else:
        return "⁉ Not Found"


def generate_youtube_bar(position: int, duration: int, bar_length: int,
                         bar_style: typing.Tuple[typing.Tuple[str, str, str]] = None) -> str:
    bar_length = bar_length if bar_length > 0 else 1
    duration = duration if duration > 0 else 1
    played = int((position / duration) * bar_length)
    missing = int(bar_length - played)
    bars = bar_style or constants.YOUTUBE_BARS
    bar = []
    if played == 0 and missing > 0:
        bar += [bars[0][1]]
        bar += [bars[1][2] * (missing - 2)]
        bar += [bars[2][2]]

    elif played > 0 and missing == 0:
        bar += [bars[0][0]]
        bar += [bars[1][0] * (played - 2)]
        bar += [bars[2][1]]

    elif played > 0 and missing > 0:
        bar += [bars[0][0]]
        bar += [bars[1][0] * (played - 1)]
        bar += [bars[1][1]]
        bar += [bars[1][2] * (missing - 2)]
        bar += [bars[2][2]]

    elif played > missing:
        bar += [bars[0][0]]
        bar += [bars[1][0] * (bar_length - 2)]
        bar += [bars[2][0]]

    return ''.join(bar)


async def count_lines(path: str, filetype: str = '.py'):
    lines = 0
    for i in os.scandir(path):
        if i.is_file():
            if i.path.endswith(filetype):
                lines += len((await (await aiofiles.open(i.path, 'r')).read()).split("\n"))
        elif i.is_dir():
            lines += await count_lines(i.path, filetype)
    return lines


async def count_others(path: str, filetype: str = '.py', file_contains: str = 'def'):
    line_count = 0
    for i in os.scandir(path):
        if i.is_file():
            if i.path.endswith(filetype):
                line_count += len([line for line in (await (await aiofiles.open(i.path, 'r')).read()).split("\n") if
                                   file_contains in line])
        elif i.is_dir():
            line_count += await count_others(i.path, filetype, file_contains)
    return line_count


class Url(discord.ui.View):
    def __init__(self, url: str, label: str = 'Open', emoji: str = None):
        super().__init__()
        self.add_item(discord.ui.Button(label=label, emoji=emoji, url=url))


def deltaconv(s):
    hours = s // 3600
    s = s - (hours * 3600)
    minutes = s // 60
    seconds = s - (minutes * 60)
    if hours > 0:
        return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
    return '{:02}:{:02}'.format(int(minutes), int(seconds))


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

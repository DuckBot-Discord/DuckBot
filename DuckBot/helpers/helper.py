import os

import aiofiles
import discord
import typing
from discord import VoiceRegion

from DuckBot.helpers import constants


def get_perms(permissions):
    perms = []
    if permissions.administrator:
        perms.append("Administrator")
        return ["Administrator"]
    if permissions.manage_guild:
        perms.append("Manage Server")
    if permissions.ban_members:
        perms.append("Ban Members")
    if permissions.kick_members:
        perms.append("Kick Members")
    if permissions.manage_channels:
        perms.append("Manage Channels")
    if permissions.manage_threads:
        perms.append("Manage Threads")
    if permissions.manage_emojis_and_stickers:
        perms.append("Manage Emojis and Stickers")
    if permissions.manage_messages:
        perms.append("Manage Messages")
    if permissions.manage_permissions:
        perms.append("Manage Permissions")
    if permissions.manage_roles:
        perms.append("Manage Roles")
    if permissions.mention_everyone:
        perms.append("Mention Everyone")
    if permissions.manage_emojis:
        perms.append("Manage Emojis")
    if permissions.manage_webhooks:
        perms.append("Manage Webhooks")
    if permissions.manage_events:
        perms.append("Manage Events")
    if permissions.move_members:
        perms.append("Move Members")
    if permissions.mute_members:
        perms.append("Mute Members")
    if permissions.deafen_members:
        perms.append("Deafen Members")
    if permissions.priority_speaker:
        perms.append("Priority Speaker")
    if permissions.view_audit_log:
        perms.append("See Audit Log")
    if permissions.create_instant_invite:
        perms.append("Create Instant Invites")
    if len(perms) == 0:
        return None
    return perms


def get_user_badges(user, bot: bool = False):
    flags = dict(user.public_flags)

    if bot is True:
        return True if flags['verified_bot'] else False

    if user.premium_since:
        flags['premium_since'] = True
    else:
        flags['premium_since'] = False

    user_flags = []
    for flag, emoji in constants.base_flags.items():
        if flags[flag]:
            user_flags.append(emoji)

    return ' '.join(user_flags) if user_flags else None


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
    played = int(position/(duration*bar_length))
    missing = int(bar_length-played)
    bars = bar_style or constants.bars
    bar = []
    if played == 0 and missing > 0:
        bar += [bars[0][1]]
        bar += [bars[1][2]*(missing-2)]
        bar += [bars[2][2]]

    elif played > 0 and missing == 0:
        bar += [bars[0][0]]
        bar += [bars[1][0]*(played-2)]
        bar += [bars[2][1]]

    elif played > 0 and missing > 0:
        bar += [bars[0][0]]
        bar += [bars[1][0]*(played-2)]
        bar += [bars[1][1]]
        bar += [bars[1][2]*(missing-1)]
        bar += [bars[2][2]]

    elif played > missing:
        bar += [bars[0][0]]
        bar += [bars[1][0]*(bar_length-2)]
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
                line_count += len([line for line in (await (await aiofiles.open(i.path, 'r')).read()).split("\n") if file_contains in line])
        elif i.is_dir():
            line_count += await count_others(i.path, filetype, file_contains)
    return line_count

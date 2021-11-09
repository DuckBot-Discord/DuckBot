import os

import aiofiles
import discord
import typing
from discord import VoiceRegion
from discord.ext import commands
from openrobot import api_wrapper as openrobot
from discord.flags import BaseFlags, fill_with_flags, flag_value

from DuckBot.helpers import constants


def get_perms(permissions: discord.Permissions):
    if permissions.administrator:
        return ['Administrator']
    wanted_perms = dict({x for x in permissions if x[1] is True} - set(discord.Permissions(521942715969)))
    return [p.replace('_', ' ').replace('guild', 'server').title() for p in wanted_perms]


def get_user_badges(user: discord.Member, bot, fetched_user: discord.User = None):
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
        user_flags.append(f'<:nitro:895392323519799306> Nitro [guess: Rare #tag]')

    elif user.discriminator in bot.common_discrims:
        print('this triggered')
        user_flags.append(f'<:nitro:895392323519799306> Nitro [guess: Uncommon #tag]')

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


class LyricsConverter(commands.Converter):
    async def convert(self, ctx, argument) -> openrobot.LyricResult:
        try:
            return await ctx.bot.orb.lyrics(argument)
        except openrobot.OpenRobotAPIError:
            raise commands.BadArgument(f"Sorry, I couldn't find any song named `{argument[0:1000]}`")


def convert_bytes(size):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return "%3.1f %s" % (size, x)
        size /= 1024.0
    return size


@fill_with_flags()
class LoggingEventsFlags(BaseFlags):

    def __init__(self, permissions: int = 0, **kwargs: bool):
        super().__init__(**kwargs)
        if not isinstance(permissions, int):
            raise TypeError(f"Expected int parameter, received {permissions.__class__.__name__} instead.")
        self.value = permissions
        for key, value in kwargs.items():
            if key not in self.VALID_FLAGS:
                raise TypeError(f"{key!r} is not a valid permission name.")
            setattr(self, key, value)

    @classmethod
    def all(cls):
        bits = max(cls.VALID_FLAGS.values()).bit_length()
        value = (1 << bits) - 1
        self = cls.__new__(cls)
        self.value = value
        return self

    @classmethod
    def message(cls):
        return cls(0b000000000000000000000000000111)

    @classmethod
    def join_leave(cls):
        return cls(0b000000000000000000000000011000)

    @classmethod
    def member(cls):
        return cls(0b000000000000000000011111100000)

    @classmethod
    def voice(cls):
        return cls(0b000000110000000111100000000000)

    @classmethod
    def server(cls):
        return cls(0b111111111111111000000000000000)

    @flag_value
    def message_delete(self):
        return 1 << 0

    @flag_value
    def message_purge(self):
        return 1 << 1

    @flag_value
    def message_edit(self):
        return 1 << 2

    @flag_value
    def member_join(self):
        return 1 << 3

    @flag_value
    def member_leave(self):
        return 1 << 4

    @flag_value
    def member_update(self):
        return 1 << 5

    @flag_value
    def user_ban(self):
        return 1 << 6

    @flag_value
    def user_unban(self):
        return 1 << 7

    @flag_value
    def user_update(self):
        return 1 << 8

    @flag_value
    def invite_create(self):
        return 1 << 9

    @flag_value
    def invite_delete(self):
        return 1 << 10

    @flag_value
    def voice_join(self):
        return 1 << 11

    @flag_value
    def voice_leave(self):
        return 1 << 12

    @flag_value
    def voice_move(self):
        return 1 << 13

    @flag_value
    def voice_mod(self):
        return 1 << 14

    @flag_value
    def emoji_create(self):
        return 1 << 15

    @flag_value
    def emoji_delete(self):
        return 1 << 16

    @flag_value
    def emoji_update(self):
        return 1 << 17

    @flag_value
    def sticker_create(self):
        return 1 << 18

    @flag_value
    def sticker_delete(self):
        return 1 << 19

    @flag_value
    def sticker_update(self):
        return 1 << 20

    @flag_value
    def server_update(self):
        return 1 << 21

    @flag_value
    def stage_open(self):
        return 1 << 22

    @flag_value
    def stage_close(self):
        return 1 << 23

    @flag_value
    def channel_create(self):
        return 1 << 24

    @flag_value
    def channel_delete(self):
        return 1 << 25

    @flag_value
    def channel_edit(self):
        return 1 << 26

    @flag_value
    def role_create(self):
        return 1 << 27

    @flag_value
    def role_delete(self):
        return 1 << 28

    @flag_value
    def role_edit(self):
        return 1 << 29

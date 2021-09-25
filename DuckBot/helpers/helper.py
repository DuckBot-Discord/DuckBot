import discord
from discord import VoiceRegion


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

    base_flags = {
    'staff': '<:staff:314068430787706880>',
    'partner': '<:partnernew:754032603081998336>',
    'hypesquad': '<:hypesquad:314068430854684672>',
    'bug_hunter': '<:hypesquad:314068430854684672>',
    'hypesquad_bravery': '<:bravery:585763004218343426>',
    'hypesquad_brilliance': '<:brilliance:585763004495298575>',
    'hypesquad_balance': '<:balance:585763004574859273>',
    'early_supporter': '<:supporter:585763690868113455>',
    'bug_hunter_level_2': '<:bughunter_gold:850843414953984041>',
    'verified_bot_developer': '<:earlybotdev:850843591756349450>',
    'premium_since': '<:nitro:314068430611415041>',
    'discord_certified_moderator': '<:certified_moderator:851224958825660497>'
    }


    if user.premium_since:
        flags['premium_since'] = True
    else:
        flags['premium_since'] = False

    user_flags = []
    for flag, emoji in base_flags.items():
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
    else:
        return "⁉ Not Found"


def generate_youtube_bar(position: int, duration: int, bar_length: int) -> str:
    played = int(position/duration*bar_length)
    missing = int(bar_length-played)

    bars = (
        ('<a:bar_start_full:891218466172993536>',
         '<a:bar_start_mid:891218253513371679>',
         None),
        ('<a:bar_center_full:891218254553575424>',
         '<a:bar_center_mid:891218253827940472>',
         '<a:bar_center_empty:891218254343856168>'),
        ('<a:bar_end_full:891232339437453343>',
         '<a:bar_end_mid:891232862400028693>',
         '<a:bar_end_empty:891218253433679885>'
         )
    )
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

    elif played > 0 and missing != 0 and played > missing:
        bar += [bars[0][0]]
        bar += [bars[1][0]*(played-2)]
        bar += [bars[2][0]]

    return ''.join(bar)

from collections import namedtuple

import discord

CUSTOM_TICKS = {
    True: '<:greenTick:895390596599017493>',
    False: '<:redTick:895390643210305536>',
    None: '<:greyTick:895390690396229753>',
}

DEFAULT_TICKS = {
    True: '✅',
    False: '❌',
    None: '➖',
}

GUILD_FEATURES = {
    'COMMUNITY': 'Community Server',
    'VERIFIED': 'Verified',
    'DISCOVERABLE': 'Discoverable',
    'PARTNERED': 'Partnered',
    'FEATURABLE': 'Featured',
    'COMMERCE': 'Commerce',
    'MONETIZATION_ENABLED': 'Monetization',
    'NEWS': 'News Channels',
    'PREVIEW_ENABLED': 'Preview Enabled',
    'INVITE_SPLASH': 'Invite Splash',
    'VANITY_URL': 'Vanity Invite URL',
    'ANIMATED_ICON': 'Animated Server Icon',
    'BANNER': 'Server Banner',
    'MORE_EMOJI': 'More Emoji',
    'MORE_STICKERS': 'More Stickers',
    'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
    'MEMBER_VERIFICATION_GATE_ENABLED': 'Membership Screening',
    'TICKETED_EVENTS_ENABLED': 'Ticketed Events',
    'VIP_REGIONS': 'VIP Voice Regions',
    'PRIVATE_THREADS': 'Private Threads',
    'THREE_DAY_THREAD_ARCHIVE': '3 Day Thread Archive',
    'SEVEN_DAY_THREAD_ARCHIVE': '1 Week Thread Archive',
}

SQUARE_TICKS = {
    True: '🟩',
    False: '🟥',
    None: '⬛',
}

TOGGLES = {
    True: '<:toggle_on:895390746654412821>',
    False: '<:toggle_off:895390760344629319>',
    None: '<:toggle_off:895390760344629319>',
}

DICES = ['<:dice_1:895391506158997575>',
         '<:dice_2:895391525259841547>',
         '<:dice_3:895391547003117628>',
         '<:dice_4:895391573670498344>',
         '<:dice_5:895391597108285440>',
         '<:dice_6:895391621728854056>']

COINS_STRING = ['<:heads:895391679044005949> Heads!',
                '<:tails:895391716356522057> Tails!']

USER_FLAGS = {
    'staff': '<:staff:895391901778346045>',
    'partner': '<:partnernew:895391927271309412>',
    'hypesquad': '<:hypesquad:895391957638070282>',
    'bug_hunter': '<:bughunter:895392105386631249>',
    'hypesquad_bravery': '<:bravery:895392137225584651>',
    'hypesquad_brilliance': '<:brilliance:895392183950131200>',
    'hypesquad_balance': '<:balance:895392209564733492>',
    'early_supporter': '<:supporter:895392239356903465>',
    'bug_hunter_level_2': '<:bughunter_gold:895392270369579078>',
    'verified_bot_developer': '<:earlybotdev:895392298895032364>',
    'premium_since': '<:nitro:895392323519799306>',
    'discord_certified_moderator': '<:certified_moderator:895393984308981930>'
}

CONTENT_FILTER = {
    discord.ContentFilter.disabled: "Don't scan any media content",
    discord.ContentFilter.no_role: "Scan media content from members without a role.",
    discord.ContentFilter.all_members: "Scan media content from all members."
}

VERIFICATION_LEVEL = {
    discord.VerificationLevel.none: '<:none_verification:895818789919285268>',
    discord.VerificationLevel.low: '<:low_verification:895818719362699274>',
    discord.VerificationLevel.medium: '<:medium_verification:895818719362686976>',
    discord.VerificationLevel.high: '<:high_verification:895818719387865109>',
    discord.VerificationLevel.highest: '<:highest_verification:895818719530450984>'
}

YOUTUBE_BARS = (
    ('<a:bar_start_full:895394028999311370>',
     '<a:bar_start_mid:895394052378361866>',
     None),
    ('<a:bar_center_full:895394087094599711>',
     '<a:bar_center_mid:895394130891526205>',
     '<a:bar_center_empty:895394159169515590>'),
    ('<a:bar_end_full:895394185832697876>',
     '<a:bar_end_mid:895394210595868692>',
     '<a:bar_end_empty:895394240308338719>'
     )
)

GUILD_BOOST_LEVEL_EMOJI = {
    '0': '<:Level0_guild:895394281559306240>',
    '1': '<:Level1_guild:895394308243464203>',
    '2': '<:Level2_guild:895394334164254780>',
    '3': '<:Level3_guild:895394362933006396>'
}

GET_SOME_HELP = '<a:stopit:895395218763968562>'
BLOB_STOP_SIGN = '<:blobstop:895395252284850186>'
REPLY_BUTTON = '<:reply:895394899728408597>'
UPVOTE = '<:upvote:893588750242832424>'
DOWNVOTE = '<:downvote:893588792164892692>'
REDDIT_UPVOTE = '<:upvote:895395361634541628>'
TOP_GG = '<:topgg:895395399043543091>'
BOTS_GG = '<:botsgg:895395445608697967>'
SERVERS_ICON = '<:servers:895395501934006292>'
INVITE = '<:invite:895395547651907607>'
MINECRAFT_LOGO = '<:minecraft:895395622272782356>'
GITHUB = '<:github:895395664383598633>'
WEBSITE = '<:open_site:895395700249075813>'
TYPING_INDICATOR = '<a:typing:895397923687399517>'
POSTGRE_LOGO = '<:psql:895405698278649876>'
SHUT_SEAGULL = '<:shut:895406986227761193>'
EDIT_NICKNAME = '<:nickname:895407885339738123>'
ROO_SLEEP = '<:RooSleep:895407927681253436>'
INFORMATION_SOURCE = '<:info:895407958035431434>'
STORE_TAG = '<:store_tag:895407986850271262>'
JOINED_SERVER = '<:joined:895408141305540648>'
LEFT_SERVER = '<:moved:895408170011332608>'
ROLES_ICON = '<:role:895408243076128819>'
BOOST = '<:booster4:895413288219861032>'
OWNER_CROWN = '<:owner_crown:895414001364762686>'
RICH_PRESENCE = '<:rich_presence:895414264016306196>'
VOICE_CHANNEL = '<:voice:895414328818274315>'
TEXT_CHANNEL = '<:view_channel:895414354588082186>'
CATEGORY_CHANNEL = '<:category:895414388528406549>'
STAGE_CHANNEL = '<:stagechannel:895414409445380096>'
TEXT_CHANNEL_WITH_THREAD = '<:threadnew:895414437916332062>'
EMOJI_GHOST = '<:emoji_ghost:895414463354785853>'

st_nt = namedtuple('statuses', ['ONLINE', 'IDLE', 'DND', 'OFFLINE'])

statuses = st_nt('<:status_online:895808180637020181>',
                 '<:status_idle:895808212580827256>',
                 '<:status_dnd:895808261801009193>',
                 '<:status_offline:895808306222886932>')

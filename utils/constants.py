# This file is bad, but all things that can be deleted at some point
# should go here, so they're easily changeable at a later date.
from __future__ import annotations

from typing import Tuple
from collections import namedtuple

import discord

__all__: Tuple[str, ...] = (
    'CUSTOM_TICKS',
    'DEFAULT_TICKS',
    'GUILD_FEATURES',
    'SQUARE_TICKS',
    'TOGGLES',
    'DICES',
    'COINS_STRING',
    'USER_FLAGS',
    'CONTENT_FILTER',
    'VERIFICATION_LEVEL',
    'YOUTUBE_BARS',
    'GUILD_BOOST_LEVEL_EMOJI',
    'GET_SOME_HELP',
    'BLOB_STOP_SIGN',
    'REPLY_BUTTON',
    'UPVOTE',
    'DOWNVOTE',
    'REDDIT_UPVOTE',
    'TOP_GG',
    'BOTS_GG',
    'SERVERS_ICON',
    'INVITE',
    'MINECRAFT_LOGO',
    'GITHUB',
    'WEBSITE',
    'TYPING_INDICATOR',
    'POSTGRE_LOGO',
    'SHUT_SEAGULL',
    'EDIT_NICKNAME',
    'ROO_SLEEP',
    'INFORMATION_SOURCE',
    'STORE_TAG',
    'JOINED_SERVER',
    'MOVED_CHANNELS',
    'LEFT_SERVER',
    'ROLES_ICON',
    'BOOST',
    'OWNER_CROWN',
    'RICH_PRESENCE',
    'VOICE_CHANNEL',
    'TEXT_CHANNEL',
    'CATEGORY_CHANNEL',
    'STAGE_CHANNEL',
    'TEXT_CHANNEL_WITH_THREAD',
    'EMOJI_GHOST',
    'SPOTIFY',
    'YOUTUBE_LOGO',
    'ARROW',
    'ARROWFWD',
    'ARROWBACK',
    'ARROWZ',
    'ARROWFWDZ',
    'ARROWBACKZ',
    'st_nt',
    'statuses',
    'CAG_UP',
    'CAG_DOWN',
    'SPINNING_MAG_GLASS',
    'DONE',
    'COMMON_DISCRIMINATORS',
    'COMMON_WORDS',
    'NITRO',
    'BOT',
    'FULL_SPOTIFY',
    'BOT_ANSI_ART',
)

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
MOVED_CHANNELS = '<:moved:895408170011332608>'
LEFT_SERVER = '<:left:897315201156792371>'
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
SPOTIFY = '<:spotify:897661396022607913>'
YOUTUBE_LOGO = '<:youtube:898052487989309460>'
ARROW = ARROWFWD = '<:arrow:909672287849041940>'
ARROWBACK = '<:arrow:909889493782376540>'
ARROWZ = ARROWFWDZ = '<:arrow:909897129198231662>'
ARROWBACKZ = '<:arrow:909897233833529345>'
NITRO = '<:nitro:895392323519799306>'
BOT = '<:bot:952905056657752155>'
FULL_SPOTIFY = "<:spotify:897661396022607913>" \
               "<:spotify1:953665420987072583>" \
               "<:spotify2:953665449210544188>" \
               "<:spotify3:953665460916850708>" \
               "<:spotify4:953665475517231194>"

CUSTOM_TICKS = {
    True: '<:greenTick:895390596599017493>',
    False: '<:redTick:895390643210305536>',
    None: '<:greyTick:895390690396229753>',
}

DEFAULT_TICKS = {
    True: '✅',
    False: '❌',
    None: '⬜',
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
    None: '⬜',
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
    'bot_http_interactions': f'{WEBSITE} Interaction-only Bot',
    'bug_hunter': '<:bughunter:895392105386631249> Discord Bug Hunter',
    'bug_hunter_level_2': '<:bughunter_gold:895392270369579078> Discord Bug Hunter',
    'discord_certified_moderator': '<:certified_moderator:895393984308981930> Certified Moderator',
    'early_supporter': '<:supporter:895392239356903465> Early Supporter',
    'hypesquad': '<:hypesquad:895391957638070282> HypeSquad Events',
    'hypesquad_balance': '<:balance:895392209564733492> HypeSquad Balance',
    'hypesquad_bravery': '<:bravery:895392137225584651> HypeSquad Bravery',
    'hypesquad_brilliance': '<:brilliance:895392183950131200> HypeSquad Brilliance',
    'partner': '<:partnernew:895391927271309412> Partnered Server Owner',
    'spammer': '\N{WARNING SIGN} Potential Spammer',
    'staff': '<:staff:895391901778346045> Discord Staff',
    'system': '\N{INFORMATION SOURCE} System',
    'team_user': '\N{INFORMATION SOURCE} Team User',
    'verified_bot': '<:verified_bot:897876151219912754> Verified Bot',
    'verified_bot_developer': '<:earlybotdev:895392298895032364> Early Verified Bot Developer',
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

st_nt = namedtuple('statuses', ['ONLINE', 'IDLE', 'DND', 'OFFLINE',
                                'ONLINE_WEB', 'IDLE_WEB', 'DND_WEB', 'OFFLINE_WEB',
                                'ONLINE_MOBILE', 'IDLE_MOBILE', 'DND_MOBILE', 'OFFLINE_MOBILE'])

statuses = st_nt(ONLINE='<:desktop_online:897644406344130600>',
                 ONLINE_WEB='<:web_online:897644406801313832>',
                 ONLINE_MOBILE='<:mobile_online:897644405102616586>',
                 IDLE='<:desktop_idle:897644406344130603>',
                 IDLE_WEB='<:web_idle:897644403244544010>',
                 IDLE_MOBILE='<:mobile_idle:897644402938347540>',
                 DND='<:desktop_dnd:897644406675497061>',
                 DND_WEB='<:web_dnd:897644405383643137>',
                 DND_MOBILE='<:mobile_dnd:897644405014532107>',
                 OFFLINE='<:desktop_offline:897644406792937532>',
                 OFFLINE_WEB='<:web_offline:897644403395547208>',
                 OFFLINE_MOBILE='<:mobile_offline:897644403345227776>')

CAG_UP = 'https://cdn.discordapp.com/attachments/879251951714467840/896293818096291840/Sv6kz8f.png'
CAG_DOWN = 'https://cdn.discordapp.com/attachments/879251951714467840/896297890396389377/wvUPp3d.png'
SPINNING_MAG_GLASS = 'https://cdn.discordapp.com/attachments/879251951714467840/896903391085748234/DZhQwnD.gif'

DONE = [
    '<:done:912190157942308884>',
    '<:done:912190217102970941>',
    '<a:done:912190284698361876>',
    '<a:done:912190377757376532>',
    '<:done:912190445289877504>',
    '<a:done:912190496791728148>',
    '<a:done:912190546192265276>',
    '<a:done:912190649493749811>',
    '<:done:912190753084694558>',
    '<:done:912190821321814046>',
    '<a:done:912190898241167370>',
    '<a:done:912190952200871957>',
    '<a:done:912191063589027880>',
    '<a:done:912191153326145586>',
    '<:done:912191209919897700>',
    '<:done:912191260356407356>',
    '<a:done:912191386575577119>',
    '<:done:912191480351825920>',
    '<:done:912191682534047825>',
    '<a:done:912192596305129522>',
    '<a:done:912192718212583464>',
]

COMMON_DISCRIMINATORS = ['0001', '0002', '0003', '0004', '0005', '0006', '0007', '0008', '0009',
                         '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999',
                         '1010', '2020', '3030', '4040', '5050', '6060', '7070', '8080', '9090',
                         '1001', '2002', '3003', '5004', '5005', '6006', '7007', '8008', '9009',
                         '1000', '2000', '3000', '4000', '5000', '6000', '7000', '8000', '9000',
                         '1337', '6969', '0420', '2021', '0666', '0333']

COMMON_WORDS = ['abandon', 'ability', 'able', 'abortion', 'about', 'above', 'abroad', 'absence', 'absolute',
                'absolutely', 'absorb', 'abuse', 'academic', 'accept', 'access', 'accident', 'accompany', 'accomplish',
                'according', 'account', 'accurate', 'accuse', 'achieve', 'achievement', 'acid', 'acknowledge',
                'acquire', 'across', 'act', 'action', 'active', 'activist', 'activity', 'actor', 'actress', 'actual',
                'actually', 'ad', 'adapt', 'add', 'addition', 'additional', 'address', 'adequate', 'adjust',
                'adjustment', 'administration', 'administrator', 'admire', 'admission', 'admit', 'adolescent', 'adopt',
                'adult', 'advance', 'advanced', 'advantage', 'adventure', 'advertising', 'advice', 'advise', 'adviser',
                'advocate', 'affair', 'affect', 'afford', 'afraid', 'African', 'African-American', 'after', 'afternoon',
                'again', 'against', 'age', 'agency', 'agenda', 'agent', 'aggressive', 'ago', 'agree', 'agreement',
                'agricultural', 'ah', 'ahead', 'aid', 'aide', 'AIDS', 'aim', 'air', 'aircraft', 'airline', 'airport',
                'album', 'alcohol', 'alive', 'all', 'alliance', 'allow', 'ally', 'almost', 'alone', 'along', 'already',
                'also', 'alter', 'alternative', 'although', 'always', 'AM', 'amazing', 'American', 'among', 'amount',
                'analysis', 'analyst', 'analyze', 'ancient', 'and', 'anger', 'angle', 'angry', 'animal', 'anniversary',
                'announce', 'annual', 'another', 'answer', 'anticipate', 'anxiety', 'any', 'anybody', 'anymore',
                'anyone', 'anything', 'anyway', 'anywhere', 'apart', 'apartment', 'apparent', 'apparently', 'appeal',
                'appear', 'appearance', 'apple', 'application', 'apply', 'appoint', 'appointment', 'appreciate',
                'approach', 'appropriate', 'approval', 'approve', 'approximately', 'Arab', 'architect', 'area', 'argue',
                'argument', 'arise', 'arm', 'armed', 'army', 'around', 'arrange', 'arrangement', 'arrest', 'arrival',
                'arrive', 'art', 'article', 'artist', 'artistic', 'as', 'Asian', 'aside', 'ask', 'asleep', 'aspect',
                'assault', 'assert', 'assess', 'assessment', 'asset', 'assign', 'assignment', 'assist', 'assistance',
                'assistant', 'associate', 'association', 'assume', 'assumption', 'assure', 'at', 'athlete', 'athletic',
                'atmosphere', 'attach', 'attack', 'attempt', 'attend', 'attention', 'attitude', 'attorney', 'attract',
                'attractive', 'attribute', 'audience', 'author', 'authority', 'auto', 'available', 'average', 'avoid',
                'award', 'aware', 'awareness', 'away', 'awful', 'baby', 'back', 'background', 'bad', 'badly', 'bag',
                'bake', 'balance', 'ball', 'ban', 'band', 'bank', 'bar', 'barely', 'barrel', 'barrier', 'base',
                'baseball', 'basic', 'basically', 'basis', 'basket', 'basketball', 'bathroom', 'battery', 'battle',
                'be', 'beach', 'bean', 'bear', 'beat', 'beautiful', 'beauty', 'because', 'become', 'bed', 'bedroom',
                'beer', 'before', 'begin', 'beginning', 'behavior', 'behind', 'being', 'belief', 'believe', 'bell',
                'belong', 'below', 'belt', 'bench', 'bend', 'beneath', 'benefit', 'beside', 'besides', 'best', 'bet',
                'better', 'between', 'beyond', 'Bible', 'big', 'bike', 'bill', 'billion', 'bind', 'biological', 'bird',
                'birth', 'birthday', 'bit', 'bite', 'black', 'blade', 'blame', 'blanket', 'blind', 'block', 'blood',
                'blow', 'blue', 'board', 'boat', 'body', 'bomb', 'bombing', 'bond', 'bone', 'book', 'boom', 'boot',
                'border', 'born', 'borrow', 'boss', 'both', 'bother', 'bottle', 'bottom', 'boundary', 'bowl', 'box',
                'boy', 'boyfriend', 'brain', 'branch', 'brand', 'bread', 'break', 'breakfast', 'breast', 'breath',
                'breathe', 'brick', 'bridge', 'brief', 'briefly', 'bright', 'brilliant', 'bring', 'British', 'broad',
                'broken', 'brother', 'brown', 'brush', 'buck', 'budget', 'build', 'building', 'bullet', 'bunch',
                'burden', 'burn', 'bury', 'bus', 'business', 'busy', 'but', 'butter', 'button', 'buy', 'buyer', 'by',
                'cabin', 'cabinet', 'cable', 'cake', 'calculate', 'call', 'camera', 'camp', 'campaign', 'campus', 'can',
                'Canadian', 'cancer', 'candidate', 'cap', 'capability', 'capable', 'capacity', 'capital', 'captain',
                'capture', 'car', 'carbon', 'card', 'care', 'career', 'careful', 'carefully', 'carrier', 'carry',
                'case', 'cash', 'cast', 'cat', 'catch', 'category', 'Catholic', 'cause', 'ceiling', 'celebrate',
                'celebration', 'celebrity', 'cell', 'center', 'central', 'century', 'CEO', 'ceremony', 'certain',
                'certainly', 'chain', 'chair', 'chairman', 'challenge', 'chamber', 'champion', 'championship', 'chance',
                'change', 'changing', 'channel', 'chapter', 'character', 'characteristic', 'characterize', 'charge',
                'charity', 'chart', 'chase', 'cheap', 'check', 'cheek', 'cheese', 'chef', 'chemical', 'chest',
                'chicken', 'chief', 'child', 'childhood', 'Chinese', 'chip', 'chocolate', 'choice', 'cholesterol',
                'choose', 'Christian', 'Christmas', 'church', 'cigarette', 'circle', 'circumstance', 'cite', 'citizen',
                'city', 'civil', 'civilian', 'claim', 'class', 'classic', 'classroom', 'clean', 'clear', 'clearly',
                'client', 'climate', 'climb', 'clinic', 'clinical', 'clock', 'close', 'closely', 'closer', 'clothes',
                'clothing', 'cloud', 'club', 'clue', 'cluster', 'coach', 'coal', 'coalition', 'coast', 'coat', 'code',
                'coffee', 'cognitive', 'cold', 'collapse', 'colleague', 'collect', 'collection', 'collective',
                'college', 'colonial', 'color', 'column', 'combination', 'combine', 'come', 'comedy', 'comfort',
                'comfortable', 'command', 'commander', 'comment', 'commercial', 'commission', 'commit', 'commitment',
                'committee', 'common', 'communicate', 'communication', 'community', 'company', 'compare', 'comparison',
                'compete', 'competition', 'competitive', 'competitor', 'complain', 'complaint', 'complete',
                'completely', 'complex', 'complicated', 'component', 'compose', 'composition', 'comprehensive',
                'computer', 'concentrate', 'concentration', 'concept', 'concern', 'concerned', 'concert', 'conclude',
                'conclusion', 'concrete', 'condition', 'conduct', 'conference', 'confidence', 'confident', 'confirm',
                'conflict', 'confront', 'confusion', 'Congress', 'congressional', 'connect', 'connection',
                'consciousness', 'consensus', 'consequence', 'conservative', 'consider', 'considerable',
                'consideration', 'consist', 'consistent', 'constant', 'constantly', 'constitute', 'constitutional',
                'construct', 'construction', 'consultant', 'consume', 'consumer', 'consumption', 'contact', 'contain',
                'container', 'contemporary', 'content', 'contest', 'context', 'continue', 'continued', 'contract',
                'contrast', 'contribute', 'contribution', 'control', 'controversial', 'controversy', 'convention',
                'conventional', 'conversation', 'convert', 'conviction', 'convince', 'cook', 'cookie', 'cooking',
                'cool', 'cooperation', 'cop', 'cope', 'copy', 'core', 'corn', 'corner', 'corporate', 'corporation',
                'correct', 'correspondent', 'cost', 'cotton', 'couch', 'could', 'council', 'counselor', 'count',
                'counter', 'country', 'county', 'couple', 'courage', 'course', 'court', 'cousin', 'cover', 'coverage',
                'cow', 'crack', 'craft', 'crash', 'crazy', 'cream', 'create', 'creation', 'creative', 'creature',
                'credit', 'crew', 'crime', 'criminal', 'crisis', 'criteria', 'critic', 'critical', 'criticism',
                'criticize', 'crop', 'cross', 'crowd', 'crucial', 'cry', 'cultural', 'culture', 'cup', 'curious',
                'current', 'currently', 'curriculum', 'custom', 'customer', 'cut', 'cycle', 'dad', 'daily', 'damage',
                'dance', 'danger', 'dangerous', 'dare', 'dark', 'darkness', 'data', 'date', 'daughter', 'day', 'dead',
                'deal', 'dealer', 'dear', 'death', 'debate', 'debt', 'decade', 'decide', 'decision', 'deck', 'declare',
                'decline', 'decrease', 'deep', 'deeply', 'deer', 'defeat', 'defend', 'defendant', 'defense',
                'defensive', 'deficit', 'define', 'definitely', 'definition', 'degree', 'delay', 'deliver', 'delivery',
                'demand', 'democracy', 'Democrat', 'democratic', 'demonstrate', 'demonstration', 'deny', 'department',
                'depend', 'dependent', 'depending', 'depict', 'depression', 'depth', 'deputy', 'derive', 'describe',
                'description', 'desert', 'deserve', 'design', 'designer', 'desire', 'desk', 'desperate', 'despite',
                'destroy', 'destruction', 'detail', 'detailed', 'detect', 'determine', 'develop', 'developing',
                'development', 'device', 'devote', 'dialogue', 'die', 'diet', 'differ', 'difference', 'different',
                'differently', 'difficult', 'difficulty', 'dig', 'digital', 'dimension', 'dining', 'dinner', 'direct',
                'direction', 'directly', 'director', 'dirt', 'dirty', 'disability', 'disagree', 'disappear', 'disaster',
                'discipline', 'discourse', 'discover', 'discovery', 'discrimination', 'discuss', 'discussion',
                'disease', 'dish', 'dismiss', 'disorder', 'display', 'dispute', 'distance', 'distant', 'distinct',
                'distinction', 'distinguish', 'distribute', 'distribution', 'district', 'diverse', 'diversity',
                'divide', 'division', 'divorce', 'DNA', 'do', 'doctor', 'document', 'dog', 'domestic', 'dominant',
                'dominate', 'door', 'double', 'doubt', 'down', 'downtown', 'dozen', 'draft', 'drag', 'drama',
                'dramatic', 'dramatically', 'draw', 'drawing', 'dream', 'dress', 'drink', 'drive', 'driver', 'drop',
                'drug', 'dry', 'due', 'during', 'dust', 'duty', 'each', 'eager', 'ear', 'early', 'earn', 'earnings',
                'earth', 'ease', 'easily', 'east', 'eastern', 'easy', 'eat', 'economic', 'economics', 'economist',
                'economy', 'edge', 'edition', 'editor', 'educate', 'education', 'educational', 'educator', 'effect',
                'effective', 'effectively', 'efficiency', 'efficient', 'effort', 'egg', 'eight', 'either', 'elderly',
                'elect', 'election', 'electric', 'electricity', 'electronic', 'element', 'elementary', 'eliminate',
                'elite', 'else', 'elsewhere', 'e-mail', 'embrace', 'emerge', 'emergency', 'emission', 'emotion',
                'emotional', 'emphasis', 'emphasize', 'employ', 'employee', 'employer', 'employment', 'empty', 'enable',
                'encounter', 'encourage', 'end', 'enemy', 'energy', 'enforcement', 'engage', 'engine', 'engineer',
                'engineering', 'English', 'enhance', 'enjoy', 'enormous', 'enough', 'ensure', 'enter', 'enterprise',
                'entertainment', 'entire', 'entirely', 'entrance', 'entry', 'environment', 'environmental', 'episode',
                'equal', 'equally', 'equipment', 'era', 'error', 'escape', 'especially', 'essay', 'essential',
                'essentially', 'establish', 'establishment', 'estate', 'estimate', 'etc', 'ethics', 'ethnic',
                'European', 'evaluate', 'evaluation', 'even', 'evening', 'event', 'eventually', 'ever', 'every',
                'everybody', 'everyday', 'everyone', 'everything', 'everywhere', 'evidence', 'evolution', 'evolve',
                'exact', 'exactly', 'examination', 'examine', 'example', 'exceed', 'excellent', 'except', 'exception',
                'exchange', 'exciting', 'executive', 'exercise', 'exhibit', 'exhibition', 'exist', 'existence',
                'existing', 'expand', 'expansion', 'expect', 'expectation', 'expense', 'expensive', 'experience',
                'experiment', 'expert', 'explain', 'explanation', 'explode', 'explore', 'explosion', 'expose',
                'exposure', 'express', 'expression', 'extend', 'extension', 'extensive', 'extent', 'external', 'extra',
                'extraordinary', 'extreme', 'extremely', 'eye', 'fabric', 'face', 'facility', 'fact', 'factor',
                'factory', 'faculty', 'fade', 'fail', 'failure', 'fair', 'fairly', 'faith', 'fall', 'false', 'familiar',
                'family', 'famous', 'fan', 'fantasy', 'far', 'farm', 'farmer', 'fashion', 'fast', 'fat', 'fate',
                'father', 'fault', 'favor', 'favorite', 'fear', 'feature', 'federal', 'fee', 'feed', 'feel', 'feeling',
                'fellow', 'female', 'fence', 'few', 'fewer', 'fiber', 'fiction', 'field', 'fifteen', 'fifth', 'fifty',
                'fight', 'fighter', 'fighting', 'figure', 'file', 'fill', 'film', 'final', 'finally', 'finance',
                'financial', 'find', 'finding', 'fine', 'finger', 'finish', 'fire', 'firm', 'first', 'fish', 'fishing',
                'fit', 'fitness', 'five', 'fix', 'flag', 'flame', 'flat', 'flavor', 'flee', 'flesh', 'flight', 'float',
                'floor', 'flow', 'flower', 'fly', 'focus', 'folk', 'follow', 'following', 'food', 'foot', 'football',
                'for', 'force', 'foreign', 'forest', 'forever', 'forget', 'form', 'formal', 'formation', 'former',
                'formula', 'forth', 'fortune', 'forward', 'found', 'foundation', 'founder', 'four', 'fourth', 'frame',
                'framework', 'free', 'freedom', 'freeze', 'French', 'frequency', 'frequent', 'frequently', 'fresh',
                'friend', 'friendly', 'friendship', 'from', 'front', 'fruit', 'frustration', 'fuel', 'full', 'fully',
                'fun', 'function', 'fund', 'fundamental', 'funding', 'funeral', 'funny', 'furniture', 'furthermore',
                'future', 'gain', 'galaxy', 'gallery', 'game', 'gang', 'gap', 'garage', 'garden', 'garlic', 'gas',
                'gate', 'gather', 'gay', 'gaze', 'gear', 'gender', 'gene', 'general', 'generally', 'generate',
                'generation', 'genetic', 'gentleman', 'gently', 'German', 'gesture', 'get', 'ghost', 'giant', 'gift',
                'gifted', 'girl', 'girlfriend', 'give', 'given', 'glad', 'glance', 'glass', 'global', 'glove', 'go',
                'goal', 'God', 'gold', 'golden', 'golf', 'good', 'government', 'governor', 'grab', 'grade', 'gradually',
                'graduate', 'grain', 'grand', 'grandfather', 'grandmother', 'grant', 'grass', 'grave', 'gray', 'great',
                'greatest', 'green', 'grocery', 'ground', 'group', 'grow', 'growing', 'growth', 'guarantee', 'guard',
                'guess', 'guest', 'guide', 'guideline', 'guilty', 'gun', 'guy', 'habit', 'habitat', 'hair', 'half',
                'hall', 'hand', 'handful', 'handle', 'hang', 'happen', 'happy', 'hard', 'hardly', 'hat', 'hate', 'have',
                'he', 'head', 'headline', 'headquarters', 'health', 'healthy', 'hear', 'hearing', 'heart', 'heat',
                'heaven', 'heavily', 'heavy', 'heel', 'height', 'helicopter', 'hell', 'hello', 'help', 'helpful', 'her',
                'here', 'heritage', 'hero', 'herself', 'hey', 'hi', 'hide', 'high', 'highlight', 'highly', 'highway',
                'hill', 'him', 'himself', 'hip', 'hire', 'his', 'historian', 'historic', 'historical', 'history', 'hit',
                'hold', 'hole', 'holiday', 'holy', 'home', 'homeless', 'honest', 'honey', 'honor', 'hope', 'horizon',
                'horror', 'horse', 'hospital', 'host', 'hot', 'hotel', 'hour', 'house', 'household', 'housing', 'how',
                'however', 'huge', 'human', 'humor', 'hundred', 'hungry', 'hunter', 'hunting', 'hurt', 'husband',
                'hypothesis', 'I', 'ice', 'idea', 'ideal', 'identification', 'identify', 'identity', 'ie', 'if',
                'ignore', 'ill', 'illegal', 'illness', 'illustrate', 'image', 'imagination', 'imagine', 'immediate',
                'immediately', 'immigrant', 'immigration', 'impact', 'implement', 'implication', 'imply', 'importance',
                'important', 'impose', 'impossible', 'impress', 'impression', 'impressive', 'improve', 'improvement',
                'in', 'incentive', 'incident', 'include', 'including', 'income', 'incorporate', 'increase', 'increased',
                'increasing', 'increasingly', 'incredible', 'indeed', 'independence', 'independent', 'index', 'Indian',
                'indicate', 'indication', 'individual', 'industrial', 'industry', 'infant', 'infection', 'inflation',
                'influence', 'inform', 'information', 'ingredient', 'initial', 'initially', 'initiative', 'injury',
                'inner', 'innocent', 'inquiry', 'inside', 'insight', 'insist', 'inspire', 'install', 'instance',
                'instead', 'institution', 'institutional', 'instruction', 'instructor', 'instrument', 'insurance',
                'intellectual', 'intelligence', 'intend', 'intense', 'intensity', 'intention', 'interaction',
                'interest', 'interested', 'interesting', 'internal', 'international', 'Internet', 'interpret',
                'interpretation', 'intervention', 'interview', 'into', 'introduce', 'introduction', 'invasion',
                'invest', 'investigate', 'investigation', 'investigator', 'investment', 'investor', 'invite', 'involve',
                'involved', 'involvement', 'Iraqi', 'Irish', 'iron', 'Islamic', 'island', 'Israeli', 'issue', 'it',
                'Italian', 'item', 'its', 'itself', 'jacket', 'jail', 'Japanese', 'jet', 'Jew', 'Jewish', 'job', 'join',
                'joint', 'joke', 'journal', 'journalist', 'journey', 'joy', 'judge', 'judgment', 'juice', 'jump',
                'junior', 'jury', 'just', 'justice', 'justify', 'keep', 'key', 'kick', 'kid', 'kill', 'killer',
                'killing', 'kind', 'king', 'kiss', 'kitchen', 'knee', 'knife', 'knock', 'know', 'knowledge', 'lab',
                'label', 'labor', 'laboratory', 'lack', 'lady', 'lake', 'land', 'landscape', 'language', 'lap', 'large',
                'largely', 'last', 'late', 'later', 'Latin', 'latter', 'laugh', 'launch', 'law', 'lawn', 'lawsuit',
                'lawyer', 'lay', 'layer', 'lead', 'leader', 'leadership', 'leading', 'leaf', 'league', 'lean', 'learn',
                'learning', 'least', 'leather', 'leave', 'left', 'leg', 'legacy', 'legal', 'legend', 'legislation',
                'legitimate', 'lemon', 'length', 'less', 'lesson', 'let', 'letter', 'level', 'liberal', 'library',
                'license', 'lie', 'life', 'lifestyle', 'lifetime', 'lift', 'light', 'like', 'likely', 'limit',
                'limitation', 'limited', 'line', 'link', 'lip', 'list', 'listen', 'literally', 'literary', 'literature',
                'little', 'live', 'living', 'load', 'loan', 'local', 'locate', 'location', 'lock', 'long', 'long-term',
                'look', 'loose', 'lose', 'loss', 'lost', 'lot', 'lots', 'loud', 'love', 'lovely', 'lover', 'low',
                'lower', 'luck', 'lucky', 'lunch', 'lung', 'machine', 'mad', 'magazine', 'mail', 'main', 'mainly',
                'maintain', 'maintenance', 'major', 'majority', 'make', 'maker', 'makeup', 'male', 'mall', 'man',
                'manage', 'management', 'manager', 'manner', 'manufacturer', 'manufacturing', 'many', 'map', 'margin',
                'mark', 'market', 'marketing', 'marriage', 'married', 'marry', 'mask', 'mass', 'massive', 'master',
                'match', 'material', 'math', 'matter', 'may', 'maybe', 'mayor', 'me', 'meal', 'mean', 'meaning',
                'meanwhile', 'measure', 'measurement', 'meat', 'mechanism', 'media', 'medical', 'medication',
                'medicine', 'medium', 'meet', 'meeting', 'member', 'membership', 'memory', 'mental', 'mention', 'menu',
                'mere', 'merely', 'mess', 'message', 'metal', 'meter', 'method', 'Mexican', 'middle', 'might',
                'military', 'milk', 'million', 'mind', 'mine', 'minister', 'minor', 'minority', 'minute', 'miracle',
                'mirror', 'miss', 'missile', 'mission', 'mistake', 'mix', 'mixture', 'mm-hmm', 'mode', 'model',
                'moderate', 'modern', 'modest', 'mom', 'moment', 'money', 'monitor', 'month', 'mood', 'moon', 'moral',
                'more', 'moreover', 'morning', 'mortgage', 'most', 'mostly', 'mother', 'motion', 'motivation', 'motor',
                'mount', 'mountain', 'mouse', 'mouth', 'move', 'movement', 'movie', 'Mr', 'Mrs', 'Ms', 'much',
                'multiple', 'murder', 'muscle', 'museum', 'music', 'musical', 'musician', 'Muslim', 'must', 'mutual',
                'my', 'myself', 'mystery', 'myth', 'naked', 'name', 'narrative', 'narrow', 'nation', 'national',
                'native', 'natural', 'naturally', 'nature', 'near', 'nearby', 'nearly', 'necessarily', 'necessary',
                'neck', 'need', 'negative', 'negotiate', 'negotiation', 'neighbor', 'neighborhood', 'neither', 'nerve',
                'nervous', 'net', 'network', 'never', 'nevertheless', 'new', 'newly', 'news', 'newspaper', 'next',
                'nice', 'night', 'nine', 'no', 'nobody', 'nod', 'noise', 'nomination', 'none', 'nonetheless', 'nor',
                'normal', 'normally', 'north', 'northern', 'nose', 'not', 'note', 'nothing', 'notice', 'notion',
                'novel', 'now', 'nowhere', "n't", 'nuclear', 'number', 'numerous', 'nurse', 'nut', 'object',
                'objective', 'obligation', 'observation', 'observe', 'observer', 'obtain', 'obvious', 'obviously',
                'occasion', 'occasionally', 'occupation', 'occupy', 'occur', 'ocean', 'odd', 'odds', 'of', 'off',
                'offense', 'offensive', 'offer', 'office', 'officer', 'official', 'often', 'oh', 'oil', 'ok', 'okay',
                'old', 'Olympic', 'on', 'once', 'one', 'ongoing', 'onion', 'online', 'only', 'onto', 'open', 'opening',
                'operate', 'operating', 'operation', 'operator', 'opinion', 'opponent', 'opportunity', 'oppose',
                'opposite', 'opposition', 'option', 'or', 'orange', 'order', 'ordinary', 'organic', 'organization',
                'organize', 'orientation', 'origin', 'original', 'originally', 'other', 'others', 'otherwise', 'ought',
                'our', 'ourselves', 'out', 'outcome', 'outside', 'oven', 'over', 'overall', 'overcome', 'overlook',
                'owe', 'own', 'owner', 'pace', 'pack', 'package', 'page', 'pain', 'painful', 'paint', 'painter',
                'painting', 'pair', 'pale', 'Palestinian', 'palm', 'pan', 'panel', 'pant', 'paper', 'parent', 'park',
                'parking', 'part', 'participant', 'participate', 'participation', 'particular', 'particularly',
                'partly', 'partner', 'partnership', 'party', 'pass', 'passage', 'passenger', 'passion', 'past', 'patch',
                'path', 'patient', 'pattern', 'pause', 'pay', 'payment', 'PC', 'peace', 'peak', 'peer', 'penalty',
                'people', 'pepper', 'per', 'perceive', 'percentage', 'perception', 'perfect', 'perfectly', 'perform',
                'performance', 'perhaps', 'period', 'permanent', 'permission', 'permit', 'person', 'personal',
                'personality', 'personally', 'personnel', 'perspective', 'persuade', 'pet', 'phase', 'phenomenon',
                'philosophy', 'phone', 'photo', 'photograph', 'photographer', 'phrase', 'physical', 'physically',
                'physician', 'piano', 'pick', 'picture', 'pie', 'piece', 'pile', 'pilot', 'pine', 'pink', 'pipe',
                'pitch', 'place', 'plan', 'plane', 'planet', 'planning', 'plant', 'plastic', 'plate', 'platform',
                'play', 'player', 'please', 'pleasure', 'plenty', 'plot', 'plus', 'PM', 'pocket', 'poem', 'poet',
                'poetry', 'point', 'pole', 'police', 'policy', 'political', 'politically', 'politician', 'politics',
                'poll', 'pollution', 'pool', 'poor', 'pop', 'popular', 'population', 'porch', 'port', 'portion',
                'portrait', 'portray', 'pose', 'position', 'positive', 'possess', 'possibility', 'possible', 'possibly',
                'post', 'pot', 'potato', 'potential', 'potentially', 'pound', 'pour', 'poverty', 'powder', 'power',
                'powerful', 'practical', 'practice', 'pray', 'prayer', 'precisely', 'predict', 'prefer', 'preference',
                'pregnancy', 'pregnant', 'preparation', 'prepare', 'prescription', 'presence', 'present',
                'presentation', 'preserve', 'president', 'presidential', 'press', 'pressure', 'pretend', 'pretty',
                'prevent', 'previous', 'previously', 'price', 'pride', 'priest', 'primarily', 'primary', 'prime',
                'principal', 'principle', 'print', 'prior', 'priority', 'prison', 'prisoner', 'privacy', 'private',
                'probably', 'problem', 'procedure', 'proceed', 'process', 'produce', 'producer', 'product',
                'production', 'profession', 'professional', 'professor', 'profile', 'profit', 'program', 'progress',
                'project', 'prominent', 'promise', 'promote', 'prompt', 'proof', 'proper', 'properly', 'property',
                'proportion', 'proposal', 'propose', 'proposed', 'prosecutor', 'prospect', 'protect', 'protection',
                'protein', 'protest', 'proud', 'prove', 'provide', 'provider', 'province', 'provision', 'psychological',
                'psychologist', 'psychology', 'public', 'publication', 'publicly', 'publish', 'publisher', 'pull',
                'punishment', 'purchase', 'pure', 'purpose', 'pursue', 'push', 'put', 'qualify', 'quality', 'quarter',
                'quarterback', 'question', 'quick', 'quickly', 'quiet', 'quietly', 'quit', 'quite', 'quote', 'race',
                'racial', 'radical', 'radio', 'rail', 'rain', 'raise', 'range', 'rank', 'rapid', 'rapidly', 'rare',
                'rarely', 'rate', 'rather', 'rating', 'ratio', 'raw', 'reach', 'react', 'reaction', 'read', 'reader',
                'reading', 'ready', 'real', 'reality', 'realize', 'really', 'reason', 'reasonable', 'recall', 'receive',
                'recent', 'recently', 'recipe', 'recognition', 'recognize', 'recommend', 'recommendation', 'record',
                'recording', 'recover', 'recovery', 'recruit', 'red', 'reduce', 'reduction', 'refer', 'reference',
                'reflect', 'reflection', 'reform', 'refugee', 'refuse', 'regard', 'regarding', 'regardless', 'regime',
                'region', 'regional', 'register', 'regular', 'regularly', 'regulate', 'regulation', 'reinforce',
                'reject', 'relate', 'relation', 'relationship', 'relative', 'relatively', 'relax', 'release',
                'relevant', 'relief', 'religion', 'religious', 'rely', 'remain', 'remaining', 'remarkable', 'remember',
                'remind', 'remote', 'remove', 'repeat', 'repeatedly', 'replace', 'reply', 'report', 'reporter',
                'represent', 'representation', 'representative', 'Republican', 'reputation', 'request', 'require',
                'requirement', 'research', 'researcher', 'resemble', 'reservation', 'resident', 'resist', 'resistance',
                'resolution', 'resolve', 'resort', 'resource', 'respect', 'respond', 'respondent', 'response',
                'responsibility', 'responsible', 'rest', 'restaurant', 'restore', 'restriction', 'result', 'retain',
                'retire', 'retirement', 'return', 'reveal', 'revenue', 'review', 'revolution', 'rhythm', 'rice', 'rich',
                'rid', 'ride', 'rifle', 'right', 'ring', 'rise', 'risk', 'river', 'road', 'rock', 'role', 'roll',
                'romantic', 'roof', 'room', 'root', 'rope', 'rose', 'rough', 'roughly', 'round', 'route', 'routine',
                'row', 'rub', 'rule', 'run', 'running', 'rural', 'rush', 'Russian', 'sacred', 'sad', 'safe', 'safety',
                'sake', 'salad', 'salary', 'sale', 'sales', 'salt', 'same', 'sample', 'sanction', 'sand', 'satellite',
                'satisfaction', 'satisfy', 'sauce', 'save', 'saving', 'say', 'scale', 'scandal', 'scared', 'scenario',
                'scene', 'schedule', 'scheme', 'scholar', 'scholarship', 'school', 'science', 'scientific', 'scientist',
                'scope', 'score', 'scream', 'screen', 'script', 'sea', 'search', 'season', 'seat', 'second', 'secret',
                'secretary', 'section', 'sector', 'secure', 'security', 'see', 'seed', 'seek', 'seem', 'segment',
                'seize', 'select', 'selection', 'self', 'sell', 'Senate', 'senator', 'send', 'senior', 'sense',
                'sensitive', 'sentence', 'separate', 'sequence', 'series', 'serious', 'seriously', 'serve', 'service',
                'session', 'set', 'setting', 'settle', 'settlement', 'seven', 'several', 'severe', 'sex', 'sexual',
                'shade', 'shadow', 'shake', 'shall', 'shape', 'share', 'sharp', 'she', 'sheet', 'shelf', 'shell',
                'shelter', 'shift', 'shine', 'ship', 'shirt', 'shit', 'shock', 'shoe', 'shoot', 'shooting', 'shop',
                'shopping', 'shore', 'short', 'shortly', 'shot', 'should', 'shoulder', 'shout', 'show', 'shower',
                'shrug', 'shut', 'sick', 'side', 'sigh', 'sight', 'sign', 'signal', 'significance', 'significant',
                'significantly', 'silence', 'silent', 'silver', 'similar', 'similarly', 'simple', 'simply', 'sin',
                'since', 'sing', 'singer', 'single', 'sink', 'sir', 'sister', 'sit', 'site', 'situation', 'six', 'size',
                'ski', 'skill', 'skin', 'sky', 'slave', 'sleep', 'slice', 'slide', 'slight', 'slightly', 'slip', 'slow',
                'slowly', 'small', 'smart', 'smell', 'smile', 'smoke', 'smooth', 'snap', 'snow', 'so', 'so-called',
                'soccer', 'social', 'society', 'soft', 'software', 'soil', 'solar', 'soldier', 'solid', 'solution',
                'solve', 'some', 'somebody', 'somehow', 'someone', 'something', 'sometimes', 'somewhat', 'somewhere',
                'son', 'song', 'soon', 'sophisticated', 'sorry', 'sort', 'soul', 'sound', 'soup', 'source', 'south',
                'southern', 'Soviet', 'space', 'Spanish', 'speak', 'speaker', 'special', 'specialist', 'species',
                'specific', 'specifically', 'speech', 'speed', 'spend', 'spending', 'spin', 'spirit', 'spiritual',
                'split', 'spokesman', 'sport', 'spot', 'spread', 'spring', 'square', 'squeeze', 'stability', 'stable',
                'staff', 'stage', 'stair', 'stake', 'stand', 'standard', 'standing', 'star', 'stare', 'start', 'state',
                'statement', 'station', 'statistics', 'status', 'stay', 'steady', 'steal', 'steel', 'step', 'stick',
                'still', 'stir', 'stock', 'stomach', 'stone', 'stop', 'storage', 'store', 'storm', 'story', 'straight',
                'strange', 'stranger', 'strategic', 'strategy', 'stream', 'street', 'strength', 'strengthen', 'stress',
                'stretch', 'strike', 'string', 'strip', 'stroke', 'strong', 'strongly', 'structure', 'struggle',
                'student', 'studio', 'study', 'stuff', 'stupid', 'style', 'subject', 'submit', 'subsequent',
                'substance', 'substantial', 'succeed', 'success', 'successful', 'successfully', 'such', 'sudden',
                'suddenly', 'sue', 'suffer', 'sufficient', 'sugar', 'suggest', 'suggestion', 'suicide', 'suit',
                'summer', 'summit', 'sun', 'super', 'supply', 'support', 'supporter', 'suppose', 'supposed', 'Supreme',
                'sure', 'surely', 'surface', 'surgery', 'surprise', 'surprised', 'surprising', 'surprisingly',
                'surround', 'survey', 'survival', 'survive', 'survivor', 'suspect', 'sustain', 'swear', 'sweep',
                'sweet', 'swim', 'swing', 'switch', 'symbol', 'symptom', 'system', 'table', 'tablespoon', 'tactic',
                'tail', 'take', 'tale', 'talent', 'talk', 'tall', 'tank', 'tap', 'tape', 'target', 'task', 'taste',
                'tax', 'taxpayer', 'tea', 'teach', 'teacher', 'teaching', 'team', 'tear', 'teaspoon', 'technical',
                'technique', 'technology', 'teen', 'teenager', 'telephone', 'telescope', 'television', 'tell',
                'temperature', 'temporary', 'ten', 'tend', 'tendency', 'tennis', 'tension', 'tent', 'term', 'terms',
                'terrible', 'territory', 'terror', 'terrorism', 'terrorist', 'test', 'testify', 'testimony', 'testing',
                'text', 'than', 'thank', 'thanks', 'that', 'the', 'theater', 'their', 'them', 'theme', 'themselves',
                'then', 'theory', 'therapy', 'there', 'therefore', 'these', 'they', 'thick', 'thin', 'thing', 'think',
                'thinking', 'third', 'thirty', 'this', 'those', 'though', 'thought', 'thousand', 'threat', 'threaten',
                'three', 'throat', 'through', 'throughout', 'throw', 'thus', 'ticket', 'tie', 'tight', 'time', 'tiny',
                'tip', 'tire', 'tired', 'tissue', 'title', 'to', 'tobacco', 'today', 'toe', 'together', 'tomato',
                'tomorrow', 'tone', 'tongue', 'tonight', 'too', 'tool', 'tooth', 'top', 'topic', 'toss', 'total',
                'totally', 'touch', 'tough', 'tour', 'tourist', 'tournament', 'toward', 'towards', 'tower', 'town',
                'toy', 'trace', 'track', 'trade', 'tradition', 'traditional', 'traffic', 'tragedy', 'trail', 'train',
                'training', 'transfer', 'transform', 'transformation', 'transition', 'translate', 'transportation',
                'travel', 'treat', 'treatment', 'treaty', 'tree', 'tremendous', 'trend', 'trial', 'tribe', 'trick',
                'trip', 'troop', 'trouble', 'truck', 'true', 'truly', 'trust', 'truth', 'try', 'tube', 'tunnel', 'turn',
                'TV', 'twelve', 'twenty', 'twice', 'twin', 'two', 'type', 'typical', 'typically', 'ugly', 'ultimate',
                'ultimately', 'unable', 'uncle', 'under', 'undergo', 'understand', 'understanding', 'unfortunately',
                'uniform', 'union', 'unique', 'unit', 'United', 'universal', 'universe', 'university', 'unknown',
                'unless', 'unlike', 'unlikely', 'until', 'unusual', 'up', 'upon', 'upper', 'urban', 'urge', 'us', 'use',
                'used', 'useful', 'user', 'usual', 'usually', 'utility', 'vacation', 'valley', 'valuable', 'value',
                'variable', 'variation', 'variety', 'various', 'vary', 'vast', 'vegetable', 'vehicle', 'venture',
                'version', 'versus', 'very', 'vessel', 'veteran', 'via', 'victim', 'victory', 'video', 'view', 'viewer',
                'village', 'violate', 'violation', 'violence', 'violent', 'virtually', 'virtue', 'virus', 'visible',
                'vision', 'visit', 'visitor', 'visual', 'vital', 'voice', 'volume', 'volunteer', 'vote', 'voter', 'vs',
                'vulnerable', 'wage', 'wait', 'wake', 'walk', 'wall', 'wander', 'want', 'war', 'warm', 'warn',
                'warning', 'wash', 'waste', 'watch', 'water', 'wave', 'way', 'we', 'weak', 'wealth', 'wealthy',
                'weapon', 'wear', 'weather', 'wedding', 'week', 'weekend', 'weekly', 'weigh', 'weight', 'welcome',
                'welfare', 'well', 'west', 'western', 'wet', 'what', 'whatever', 'wheel', 'when', 'whenever', 'where',
                'whereas', 'whether', 'which', 'while', 'whisper', 'white', 'who', 'whole', 'whom', 'whose', 'why',
                'wide', 'widely', 'widespread', 'wife', 'wild', 'will', 'willing', 'win', 'wind', 'window', 'wine',
                'wing', 'winner', 'winter', 'wipe', 'wire', 'wisdom', 'wise', 'wish', 'with', 'withdraw', 'within',
                'without', 'witness', 'woman', 'wonder', 'wonderful', 'wood', 'wooden', 'word', 'work', 'worker',
                'working', 'works', 'workshop', 'world', 'worried', 'worry', 'worth', 'would', 'wound', 'wrap', 'write',
                'writer', 'writing', 'wrong', 'yard', 'yeah', 'year', 'yell', 'yellow', 'yes', 'yesterday', 'yet',
                'yield', 'you', 'young', 'your', 'yours', 'yourself', 'youth', 'zone']

BOT_ANSI_ART = """
██████╗ ██╗   ██╗ ██████╗██╗  ██╗██████╗  ██████╗ ████████╗
██╔══██╗██║   ██║██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗╚══██╔══╝
██║  ██║██║   ██║██║     █████╔╝ ██████╔╝██║   ██║   ██║   
██║  ██║██║   ██║██║     ██╔═██╗ ██╔══██╗██║   ██║   ██║   
██████╔╝╚██████╔╝╚██████╗██║  ██╗██████╔╝╚██████╔╝   ██║   
╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   
""".strip()


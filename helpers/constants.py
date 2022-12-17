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

DICES = [
    '<:dice_1:895391506158997575>',
    '<:dice_2:895391525259841547>',
    '<:dice_3:895391547003117628>',
    '<:dice_4:895391573670498344>',
    '<:dice_5:895391597108285440>',
    '<:dice_6:895391621728854056>',
]

COINS_STRING = ['<:heads:895391679044005949> Heads!', '<:tails:895391716356522057> Tails!']

USER_FLAGS = {
    'staff': '<:staff:895391901778346045> Discord Staff',
    'partner': '<:partnernew:895391927271309412> Partnered Server Owner',
    'hypesquad': '<:hypesquad:895391957638070282> HypeSquad Events',
    'bug_hunter': '<:bughunter:895392105386631249> Discord Bug Hunter',
    'hypesquad_bravery': '<:bravery:895392137225584651> HypeSquad Bravery',
    'hypesquad_brilliance': '<:brilliance:895392183950131200> HypeSquad Brilliance',
    'hypesquad_balance': '<:balance:895392209564733492> HypeSquad Balance',
    'early_supporter': '<:supporter:895392239356903465> Early Supporter',
    'bug_hunter_level_2': '<:bughunter_gold:895392270369579078> Discord Bug Hunter',
    'verified_bot_developer': '<:earlybotdev:895392298895032364> Early Verified Bot Developer',
    'verified_bot': '<:verified_bot:897876151219912754> Verified Bot',
    'discord_certified_moderator': '<:certified_moderator:895393984308981930> Certified Moderator',
    'premium_since': '<:booster4:895413288219861032>',
}

CONTENT_FILTER = {
    discord.ContentFilter.disabled: "Don't scan any media content",
    discord.ContentFilter.no_role: "Scan media content from members without a role.",
    discord.ContentFilter.all_members: "Scan media content from all members.",
}

VERIFICATION_LEVEL = {
    discord.VerificationLevel.none: '<:none_verification:895818789919285268>',
    discord.VerificationLevel.low: '<:low_verification:895818719362699274>',
    discord.VerificationLevel.medium: '<:medium_verification:895818719362686976>',
    discord.VerificationLevel.high: '<:high_verification:895818719387865109>',
    discord.VerificationLevel.highest: '<:highest_verification:895818719530450984>',
}

YOUTUBE_BARS = (
    ('<a:bar_start_full:895394028999311370>', '<a:bar_start_mid:895394052378361866>', None),
    (
        '<a:bar_center_full:895394087094599711>',
        '<a:bar_center_mid:895394130891526205>',
        '<a:bar_center_empty:895394159169515590>',
    ),
    ('<a:bar_end_full:895394185832697876>', '<a:bar_end_mid:895394210595868692>', '<a:bar_end_empty:895394240308338719>'),
)

GUILD_BOOST_LEVEL_EMOJI = {
    '0': '<:Level0_guild:895394281559306240>',
    '1': '<:Level1_guild:895394308243464203>',
    '2': '<:Level2_guild:895394334164254780>',
    '3': '<:Level3_guild:895394362933006396>',
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

st_nt = namedtuple(
    'statuses',
    [
        'ONLINE',
        'IDLE',
        'DND',
        'OFFLINE',
        'ONLINE_WEB',
        'IDLE_WEB',
        'DND_WEB',
        'OFFLINE_WEB',
        'ONLINE_MOBILE',
        'IDLE_MOBILE',
        'DND_MOBILE',
        'OFFLINE_MOBILE',
    ],
)

statuses = st_nt(
    ONLINE='<:desktop_online:897644406344130600>',
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
    OFFLINE_MOBILE='<:mobile_offline:897644403345227776>',
)

CAG_UP = 'https://cdn.discordapp.com/attachments/879251951714467840/896293818096291840/Sv6kz8f.png'
CAG_DOWN = 'https://cdn.discordapp.com/attachments/879251951714467840/896297890396389377/wvUPp3d.png'
SPINNING_MAG_GLASS = 'https://cdn.discordapp.com/attachments/879251951714467840/896903391085748234/DZhQwnD.gif'

# fmt: off
DONE = [
    '<:done:912190157942308884>', '<:done:912190217102970941>', '<a:done:912190284698361876>',
    '<a:done:912190377757376532>', '<:done:912190445289877504>', '<a:done:912190496791728148>',
    '<a:done:912190546192265276>', '<a:done:912190649493749811>', '<:done:912190753084694558>',
    '<:done:912190821321814046>', '<a:done:912190898241167370>', '<a:done:912190952200871957>',
    '<a:done:912191063589027880>', '<a:done:912191153326145586>', '<:done:912191209919897700>',
    '<:done:912191260356407356>', '<a:done:912191386575577119>', '<:done:912191480351825920>',
    '<:done:912191682534047825>', '<a:done:912192596305129522>', '<a:done:912192718212583464>',
]

COMMON_DISCRIMINATORS = [
    '0001', '0002', '0003', '0004', '0005', '0006', '0007', '0008', '0009', '1111', '2222',
    '3333', '4444', '5555', '6666', '7777', '8888', '9999', '1010', '2020', '3030', '4040',
    '5050', '6060', '7070', '8080', '9090', '1001', '2002', '3003', '5004', '5005', '6006',
    '7007', '8008', '9009', '1000', '2000', '3000', '4000', '5000', '6000', '7000', '8000',
    '9000', '1337', '6969', '0420', '2021', '0666', '0333',
]

COMMON_WORDS = [
    'abandon', 'ability', 'able', 'abortion', 'about', 'above', 'abroad', 'absence', 'absolute', 'absolutely', 'absorb',
    'academic', 'accept', 'access', 'accident', 'accompany', 'accomplish', 'according', 'account', 'accurate', 'accuse',
    'achievement', 'acid', 'acknowledge', 'acquire', 'across', 'act', 'action', 'active', 'activist', 'activity',
    'actress', 'actual', 'actually', 'ad', 'adapt', 'add', 'addition', 'additional', 'address', 'adequate', 'adjust',
    'administration', 'administrator', 'admire', 'admission', 'admit', 'adolescent', 'adopt', 'adult', 'advance',
    'advantage', 'adventure', 'advertising', 'advice', 'advise', 'adviser', 'advocate', 'affair', 'affect', 'afford',
    'African', 'African-American', 'after', 'afternoon', 'again', 'against', 'age', 'agency', 'agenda', 'agent',
    'ago', 'agree', 'agreement', 'agricultural', 'ah', 'ahead', 'aid', 'aide', 'AIDS', 'aim', 'air', 'aircraft',
    'airport', 'album', 'alcohol', 'alive', 'all', 'alliance', 'allow', 'ally', 'almost', 'alone', 'along', 'already',
    'alter', 'alternative', 'although', 'always', 'AM', 'amazing', 'American', 'among', 'amount', 'analysis', 'analyst',
    'ancient', 'and', 'anger', 'angle', 'angry', 'animal', 'anniversary', 'announce', 'annual', 'another', 'answer',
    'anxiety', 'any', 'anybody', 'anymore', 'anyone', 'anything', 'anyway', 'anywhere', 'apart', 'apartment',
    'apparently', 'appeal', 'appear', 'appearance', 'apple', 'application', 'apply', 'appoint', 'appointment',
    'approach', 'appropriate', 'approval', 'approve', 'approximately', 'Arab', 'architect', 'area', 'argue', 'argument',
    'arm', 'armed', 'army', 'around', 'arrange', 'arrangement', 'arrest', 'arrival', 'arrive', 'art', 'article',
    'artistic', 'as', 'Asian', 'aside', 'ask', 'asleep', 'aspect', 'assault', 'assert', 'assess', 'assessment', 'asset',
    'assignment', 'assist', 'assistance', 'assistant', 'associate', 'association', 'assume', 'assumption', 'assure',
    'athlete', 'athletic', 'atmosphere', 'attach', 'attack', 'attempt', 'attend', 'attention', 'attitude', 'attorney',
    'attractive', 'attribute', 'audience', 'author', 'authority', 'auto', 'available', 'average', 'avoid', 'award',
    'awareness', 'away', 'awful', 'baby', 'back', 'background', 'bad', 'badly', 'bag', 'bake', 'balance', 'ball', 'ban',
    'bank', 'bar', 'barely', 'barrel', 'barrier', 'base', 'baseball', 'basic', 'basically', 'basis', 'basket',
    'bathroom', 'battery', 'battle', 'be', 'beach', 'bean', 'bear', 'beat', 'beautiful', 'beauty', 'because', 'become',
    'bedroom', 'beer', 'before', 'begin', 'beginning', 'behavior', 'behind', 'being', 'belief', 'believe', 'bell',
    'below', 'belt', 'bench', 'bend', 'beneath', 'benefit', 'beside', 'besides', 'best', 'bet', 'better', 'between',
    'Bible', 'big', 'bike', 'bill', 'billion', 'bind', 'biological', 'bird', 'birth', 'birthday', 'bit', 'bite',
    'blade', 'blame', 'blanket', 'blind', 'block', 'blood', 'blow', 'blue', 'board', 'boat', 'body', 'bomb', 'bombing',
    'bone', 'book', 'boom', 'boot', 'border', 'born', 'borrow', 'boss', 'both', 'bother', 'bottle', 'bottom',
    'bowl', 'box', 'boy', 'boyfriend', 'brain', 'branch', 'brand', 'bread', 'break', 'breakfast', 'breast', 'breath',
    'brick', 'bridge', 'brief', 'briefly', 'bright', 'brilliant', 'bring', 'British', 'broad', 'broken', 'brother',
    'brush', 'buck', 'budget', 'build', 'building', 'bullet', 'bunch', 'burden', 'burn', 'bury', 'bus', 'business',
    'but', 'butter', 'button', 'buy', 'buyer', 'by', 'cabin', 'cabinet', 'cable', 'cake', 'calculate', 'call', 'camera',
    'campaign', 'campus', 'can', 'Canadian', 'cancer', 'candidate', 'cap', 'capability', 'capable', 'capacity',
    'captain', 'capture', 'car', 'carbon', 'card', 'care', 'career', 'careful', 'carefully', 'carrier', 'carry', 'case',
    'cast', 'cat', 'catch', 'category', 'Catholic', 'cause', 'ceiling', 'celebrate', 'celebration', 'celebrity', 'cell',
    'central', 'century', 'CEO', 'ceremony', 'certain', 'certainly', 'chain', 'chair', 'chairman', 'challenge',
    'champion', 'championship', 'chance', 'change', 'changing', 'channel', 'chapter', 'character', 'characteristic',
    'charge', 'charity', 'chart', 'chase', 'cheap', 'check', 'cheek', 'cheese', 'chef', 'chemical', 'chest', 'chicken',
    'child', 'childhood', 'Chinese', 'chip', 'chocolate', 'choice', 'cholesterol', 'choose', 'Christian', 'Christmas',
    'cigarette', 'circle', 'circumstance', 'cite', 'citizen', 'city', 'civil', 'civilian', 'claim', 'class', 'classic',
    'clean', 'clear', 'clearly', 'client', 'climate', 'climb', 'clinic', 'clinical', 'clock', 'close', 'closely',
    'clothes', 'clothing', 'cloud', 'club', 'clue', 'cluster', 'coach', 'coal', 'coalition', 'coast', 'coat', 'code',
    'cognitive', 'cold', 'collapse', 'colleague', 'collect', 'collection', 'collective', 'college', 'colonial', 'color',
    'combination', 'combine', 'come', 'comedy', 'comfort', 'comfortable', 'command', 'commander', 'comment',
    'commission', 'commit', 'commitment', 'committee', 'common', 'communicate', 'communication', 'community', 'company',
    'comparison', 'compete', 'competition', 'competitive', 'competitor', 'complain', 'complaint', 'complete',
    'complex', 'complicated', 'component', 'compose', 'composition', 'comprehensive', 'computer', 'concentrate',
    'concept', 'concern', 'concerned', 'concert', 'conclude', 'conclusion', 'concrete', 'condition', 'conduct',
    'confidence', 'confident', 'confirm', 'conflict', 'confront', 'confusion', 'Congress', 'congressional', 'connect',
    'consciousness', 'consensus', 'consequence', 'conservative', 'consider', 'considerable', 'consideration', 'consist',
    'constant', 'constantly', 'constitute', 'constitutional', 'construct', 'construction', 'consultant', 'consume',
    'consumption', 'contact', 'contain', 'container', 'contemporary', 'content', 'contest', 'context', 'continue',
    'contract', 'contrast', 'contribute', 'contribution', 'control', 'controversial', 'controversy', 'convention',
    'conversation', 'convert', 'conviction', 'convince', 'cook', 'cookie', 'cooking', 'cool', 'cooperation', 'cop',
    'copy', 'core', 'corn', 'corner', 'corporate', 'corporation', 'correct', 'correspondent', 'cost', 'cotton', 'couch',
    'council', 'counselor', 'count', 'counter', 'country', 'county', 'couple', 'courage', 'course', 'court', 'cousin',
    'coverage', 'cow', 'crack', 'craft', 'crash', 'crazy', 'cream', 'create', 'creation', 'creative', 'creature',
    'crew', 'crime', 'criminal', 'crisis', 'criteria', 'critic', 'critical', 'criticism', 'criticize', 'crop', 'cross',
    'crucial', 'cry', 'cultural', 'culture', 'cup', 'curious', 'current', 'currently', 'curriculum', 'custom',
    'cut', 'cycle', 'dad', 'daily', 'damage', 'dance', 'danger', 'dangerous', 'dare', 'dark', 'darkness', 'data',
    'daughter', 'day', 'dead', 'deal', 'dealer', 'dear', 'death', 'debate', 'debt', 'decade', 'decide', 'decision',
    'declare', 'decline', 'decrease', 'deep', 'deeply', 'deer', 'defeat', 'defend', 'defendant', 'defense', 'defensive',
    'define', 'definitely', 'definition', 'degree', 'delay', 'deliver', 'delivery', 'demand', 'democracy', 'Democrat',
    'demonstrate', 'demonstration', 'deny', 'department', 'depend', 'dependent', 'depending', 'depict', 'depression',
    'deputy', 'derive', 'describe', 'description', 'desert', 'deserve', 'design', 'designer', 'desire', 'desk',
    'despite', 'destroy', 'destruction', 'detail', 'detailed', 'detect', 'determine', 'develop', 'developing',
    'device', 'devote', 'dialogue', 'die', 'diet', 'differ', 'difference', 'different', 'differently', 'difficult',
    'dig', 'digital', 'dimension', 'dining', 'dinner', 'direct', 'direction', 'directly', 'director', 'dirt', 'dirty',
    'disagree', 'disappear', 'disaster', 'discipline', 'discourse', 'discover', 'discovery', 'discrimination',
    'discussion', 'disease', 'dish', 'dismiss', 'disorder', 'display', 'dispute', 'distance', 'distant', 'distinct',
    'distinguish', 'distribute', 'distribution', 'district', 'diverse', 'diversity', 'divide', 'division', 'divorce',
    'do', 'doctor', 'document', 'dog', 'domestic', 'dominant', 'dominate', 'door', 'double', 'doubt', 'down',
    'dozen', 'draft', 'drag', 'drama', 'dramatic', 'dramatically', 'draw', 'drawing', 'dream', 'dress', 'drink',
    'driver', 'drop', 'drug', 'dry', 'due', 'during', 'dust', 'duty', 'each', 'eager', 'ear', 'early', 'earn',
    'earth', 'ease', 'easily', 'east', 'eastern', 'easy', 'eat', 'economic', 'economics', 'economist', 'economy',
    'edition', 'editor', 'educate', 'education', 'educational', 'educator', 'effect', 'effective', 'effectively',
    'efficient', 'effort', 'egg', 'eight', 'either', 'elderly', 'elect', 'election', 'electric', 'electricity',
    'element', 'elementary', 'eliminate', 'elite', 'else', 'elsewhere', 'e-mail', 'embrace', 'emerge', 'emergency',
    'emotion', 'emotional', 'emphasis', 'emphasize', 'employ', 'employee', 'employer', 'employment', 'empty', 'enable',
    'encourage', 'end', 'enemy', 'energy', 'enforcement', 'engage', 'engine', 'engineer', 'engineering', 'English',
    'enjoy', 'enormous', 'enough', 'ensure', 'enter', 'enterprise', 'entertainment', 'entire', 'entirely', 'entrance',
    'environment', 'environmental', 'episode', 'equal', 'equally', 'equipment', 'era', 'error', 'escape', 'especially',
    'essential', 'essentially', 'establish', 'establishment', 'estate', 'estimate', 'etc', 'ethics', 'ethnic',
    'evaluate', 'evaluation', 'even', 'evening', 'event', 'eventually', 'ever', 'every', 'everybody', 'everyday',
    'everything', 'everywhere', 'evidence', 'evolution', 'evolve', 'exact', 'exactly', 'examination', 'examine',
    'exceed', 'excellent', 'except', 'exception', 'exchange', 'exciting', 'executive', 'exercise', 'exhibit',
    'exist', 'existence', 'existing', 'expand', 'expansion', 'expect', 'expectation', 'expense', 'expensive',
    'experiment', 'expert', 'explain', 'explanation', 'explode', 'explore', 'explosion', 'expose', 'exposure',
    'expression', 'extend', 'extension', 'extensive', 'extent', 'external', 'extra', 'extraordinary', 'extreme',
    'eye', 'fabric', 'face', 'facility', 'fact', 'factor', 'factory', 'faculty', 'fade', 'fail', 'failure', 'fair',
    'faith', 'fall', 'false', 'familiar', 'family', 'famous', 'fan', 'fantasy', 'far', 'farm', 'farmer', 'fashion',
    'fat', 'fate', 'father', 'fault', 'favor', 'favorite', 'fear', 'feature', 'federal', 'fee', 'feed', 'feel',
    'fellow', 'female', 'fence', 'few', 'fewer', 'fiber', 'fiction', 'field', 'fifteen', 'fifth', 'fifty', 'fight',
    'fighting', 'figure', 'file', 'fill', 'film', 'final', 'finally', 'finance', 'financial', 'find', 'finding', 'fine',
    'finish', 'fire', 'firm', 'first', 'fish', 'fishing', 'fit', 'fitness', 'five', 'fix', 'flag', 'flame', 'flat',
    'flee', 'flesh', 'flight', 'float', 'floor', 'flow', 'flower', 'fly', 'focus', 'folk', 'follow', 'following',
    'foot', 'football', 'for', 'force', 'foreign', 'forest', 'forever', 'forget', 'form', 'formal', 'formation',
    'formula', 'forth', 'fortune', 'forward', 'found', 'foundation', 'founder', 'four', 'fourth', 'frame', 'framework',
    'freedom', 'freeze', 'French', 'frequency', 'frequent', 'frequently', 'fresh', 'friend', 'friendly', 'friendship',
    'front', 'fruit', 'frustration', 'fuel', 'full', 'fully', 'fun', 'function', 'fund', 'fundamental', 'funding',
    'funny', 'furniture', 'furthermore', 'future', 'gain', 'galaxy', 'gallery', 'game', 'gang', 'gap', 'garage',
    'garlic', 'gas', 'gate', 'gather', 'gay', 'gaze', 'gear', 'gender', 'gene', 'general', 'generally', 'generate',
    'genetic', 'gentleman', 'gently', 'German', 'gesture', 'get', 'ghost', 'giant', 'gift', 'gifted', 'girl',
    'give', 'given', 'glad', 'glance', 'glass', 'global', 'glove', 'go', 'goal', 'God', 'gold', 'golden', 'golf',
    'government', 'governor', 'grab', 'grade', 'gradually', 'graduate', 'grain', 'grand', 'grandfather', 'grandmother',
    'grass', 'grave', 'gray', 'great', 'greatest', 'green', 'grocery', 'ground', 'group', 'grow', 'growing', 'growth',
    'guard', 'guess', 'guest', 'guide', 'guideline', 'guilty', 'gun', 'guy', 'habit', 'habitat', 'hair', 'half', 'hall',
    'handful', 'handle', 'hang', 'happen', 'happy', 'hard', 'hardly', 'hat', 'hate', 'have', 'he', 'head', 'headline',
    'health', 'healthy', 'hear', 'hearing', 'heart', 'heat', 'heaven', 'heavily', 'heavy', 'heel', 'height',
    'hell', 'hello', 'help', 'helpful', 'her', 'here', 'heritage', 'hero', 'herself', 'hey', 'hi', 'hide', 'high',
    'highly', 'highway', 'hill', 'him', 'himself', 'hip', 'hire', 'his', 'historian', 'historic', 'historical',
    'hit', 'hold', 'hole', 'holiday', 'holy', 'home', 'homeless', 'honest', 'honey', 'honor', 'hope', 'horizon',
    'horse', 'hospital', 'host', 'hot', 'hotel', 'hour', 'house', 'household', 'housing', 'how', 'however', 'huge',
    'humor', 'hundred', 'hungry', 'hunter', 'hunting', 'hurt', 'husband', 'hypothesis', 'I', 'ice', 'idea', 'ideal',
    'identify', 'identity', 'ie', 'if', 'ignore', 'ill', 'illegal', 'illness', 'illustrate', 'image', 'imagination',
    'immediate', 'immediately', 'immigrant', 'immigration', 'impact', 'implement', 'implication', 'imply', 'importance',
    'impose', 'impossible', 'impress', 'impression', 'impressive', 'improve', 'improvement', 'in', 'incentive',
    'include', 'including', 'income', 'incorporate', 'increase', 'increased', 'increasing', 'increasingly',
    'indeed', 'independence', 'independent', 'index', 'Indian', 'indicate', 'indication', 'individual', 'industrial',
    'infant', 'infection', 'inflation', 'influence', 'inform', 'information', 'ingredient', 'initial', 'initially',
    'injury', 'inner', 'innocent', 'inquiry', 'inside', 'insight', 'insist', 'inspire', 'install', 'instance',
    'institution', 'institutional', 'instruction', 'instructor', 'instrument', 'insurance', 'intellectual',
    'intend', 'intense', 'intensity', 'intention', 'interaction', 'interest', 'interested', 'interesting', 'internal',
    'Internet', 'interpret', 'interpretation', 'intervention', 'interview', 'into', 'introduce', 'introduction',
    'invest', 'investigate', 'investigation', 'investigator', 'investment', 'investor', 'invite', 'involve', 'involved',
    'Iraqi', 'Irish', 'iron', 'Islamic', 'island', 'Israeli', 'issue', 'it', 'Italian', 'item', 'its', 'itself',
    'jail', 'Japanese', 'jet', 'Jew', 'Jewish', 'job', 'join', 'joint', 'joke', 'journal', 'journalist', 'journey',
    'judge', 'judgment', 'juice', 'jump', 'junior', 'jury', 'just', 'justice', 'justify', 'keep', 'key', 'kick', 'kid',
    'killer', 'killing', 'kind', 'king', 'kiss', 'kitchen', 'knee', 'knife', 'knock', 'know', 'knowledge', 'lab',
    'labor', 'laboratory', 'lack', 'lady', 'lake', 'land', 'landscape', 'language', 'lap', 'large', 'largely', 'last',
    'later', 'Latin', 'latter', 'laugh', 'launch', 'law', 'lawn', 'lawsuit', 'lawyer', 'lay', 'layer', 'lead', 'leader',
    'leading', 'leaf', 'league', 'lean', 'learn', 'learning', 'least', 'leather', 'leave', 'left', 'leg', 'legacy',
    'legend', 'legislation', 'legitimate', 'lemon', 'length', 'less', 'lesson', 'let', 'letter', 'level', 'liberal',
    'license', 'lie', 'life', 'lifestyle', 'lifetime', 'lift', 'light', 'like', 'likely', 'limit', 'limitation',
    'line', 'link', 'lip', 'list', 'listen', 'literally', 'literary', 'literature', 'little', 'live', 'living', 'load',
    'local', 'locate', 'location', 'lock', 'long', 'long-term', 'look', 'loose', 'lose', 'loss', 'lost', 'lot', 'lots',
    'love', 'lovely', 'lover', 'low', 'lower', 'luck', 'lucky', 'lunch', 'lung', 'machine', 'mad', 'magazine', 'mail',
    'mainly', 'maintain', 'maintenance', 'major', 'majority', 'make', 'maker', 'makeup', 'male', 'mall', 'man',
    'management', 'manager', 'manner', 'manufacturer', 'manufacturing', 'many', 'map', 'margin', 'mark', 'market',
    'marriage', 'married', 'marry', 'mask', 'mass', 'massive', 'master', 'match', 'material', 'math', 'matter', 'may',
    'mayor', 'me', 'meal', 'mean', 'meaning', 'meanwhile', 'measure', 'measurement', 'meat', 'mechanism', 'media',
    'medication', 'medicine', 'medium', 'meet', 'meeting', 'member', 'membership', 'memory', 'mental', 'mention',
    'mere', 'merely', 'mess', 'message', 'metal', 'meter', 'method', 'Mexican', 'middle', 'might', 'military', 'milk',
    'mind', 'mine', 'minister', 'minor', 'minority', 'minute', 'miracle', 'mirror', 'miss', 'missile', 'mission',
    'mix', 'mixture', 'mm-hmm', 'mode', 'model', 'moderate', 'modern', 'modest', 'mom', 'moment', 'money', 'monitor',
    'mood', 'moon', 'moral', 'more', 'moreover', 'morning', 'mortgage', 'most', 'mostly', 'mother', 'motion',
    'motor', 'mount', 'mountain', 'mouse', 'mouth', 'move', 'movement', 'movie', 'Mr', 'Mrs', 'Ms', 'much', 'multiple',
    'muscle', 'museum', 'music', 'musical', 'musician', 'Muslim', 'must', 'mutual', 'my', 'myself', 'mystery', 'myth',
    'name', 'narrative', 'narrow', 'nation', 'national', 'native', 'natural', 'naturally', 'nature', 'near', 'nearby',
    'necessarily', 'necessary', 'neck', 'need', 'negative', 'negotiate', 'negotiation', 'neighbor', 'neighborhood',
    'nerve', 'nervous', 'net', 'network', 'never', 'nevertheless', 'new', 'newly', 'news', 'newspaper', 'next', 'nice',
    'nine', 'no', 'nobody', 'nod', 'noise', 'nomination', 'none', 'nonetheless', 'nor', 'normal', 'normally', 'north',
    'nose', 'not', 'note', 'nothing', 'notice', 'notion', 'novel', 'now', 'nowhere', 'n\'t', 'nuclear', 'number',
    'nurse', 'nut', 'object', 'objective', 'obligation', 'observation', 'observe', 'observer', 'obtain', 'obvious',
    'occasion', 'occasionally', 'occupation', 'occupy', 'occur', 'ocean', 'odd', 'odds', 'of', 'off', 'offense',
    'offer', 'office', 'officer', 'official', 'often', 'oh', 'oil', 'ok', 'okay', 'old', 'Olympic', 'on', 'once', 'one',
    'onion', 'online', 'only', 'onto', 'open', 'opening', 'operate', 'operating', 'operation', 'operator', 'opinion',
    'opportunity', 'oppose', 'opposite', 'opposition', 'option', 'or', 'orange', 'order', 'ordinary', 'organic',
    'organize', 'orientation', 'origin', 'original', 'originally', 'other', 'others', 'otherwise', 'ought', 'our',
    'out', 'outcome', 'outside', 'oven', 'over', 'overall', 'overcome', 'overlook', 'owe', 'own', 'owner', 'pace',
    'package', 'page', 'pain', 'painful', 'paint', 'painter', 'painting', 'pair', 'pale', 'Palestinian', 'palm', 'pan',
    'pant', 'paper', 'parent', 'park', 'parking', 'part', 'participant', 'participate', 'participation', 'particular',
    'partly', 'partner', 'partnership', 'party', 'pass', 'passage', 'passenger', 'passion', 'past', 'patch', 'path',
    'pattern', 'pause', 'pay', 'payment', 'PC', 'peace', 'peak', 'peer', 'penalty', 'people', 'pepper', 'per',
    'percentage', 'perception', 'perfect', 'perfectly', 'perform', 'performance', 'perhaps', 'period', 'permanent',
    'permit', 'person', 'personal', 'personality', 'personally', 'personnel', 'perspective', 'persuade', 'pet', 'phase',
    'philosophy', 'phone', 'photo', 'photograph', 'photographer', 'phrase', 'physical', 'physically', 'physician',
    'pick', 'picture', 'pie', 'piece', 'pile', 'pilot', 'pine', 'pink', 'pipe', 'pitch', 'place', 'plan', 'plane',
    'planning', 'plant', 'plastic', 'plate', 'platform', 'play', 'player', 'please', 'pleasure', 'plenty', 'plot',
    'PM', 'pocket', 'poem', 'poet', 'poetry', 'point', 'pole', 'police', 'policy', 'political', 'politically',
    'politics', 'poll', 'pollution', 'pool', 'poor', 'pop', 'popular', 'population', 'porch', 'port', 'portion',
    'portray', 'pose', 'position', 'positive', 'possess', 'possibility', 'possible', 'possibly', 'post', 'pot',
    'potential', 'potentially', 'pound', 'pour', 'poverty', 'powder', 'power', 'powerful', 'practical', 'practice',
    'prayer', 'precisely', 'predict', 'prefer', 'preference', 'pregnancy', 'pregnant', 'preparation', 'prepare',
    'presence', 'present', 'presentation', 'preserve', 'president', 'presidential', 'press', 'pressure', 'pretend',
    'prevent', 'previous', 'previously', 'price', 'pride', 'priest', 'primarily', 'primary', 'prime', 'principal',
    'print', 'prior', 'priority', 'prison', 'prisoner', 'privacy', 'private', 'probably', 'problem', 'procedure',
    'process', 'produce', 'producer', 'product', 'production', 'profession', 'professional', 'professor', 'profile',
    'program', 'progress', 'project', 'prominent', 'promise', 'promote', 'prompt', 'proof', 'proper', 'properly',
    'proportion', 'proposal', 'propose', 'proposed', 'prosecutor', 'prospect', 'protect', 'protection', 'protein',
    'proud', 'prove', 'provide', 'provider', 'province', 'provision', 'psychological', 'psychologist', 'psychology',
    'publication', 'publicly', 'publish', 'publisher', 'pull', 'punishment', 'purchase', 'pure', 'purpose', 'pursue',
    'put', 'qualify', 'quality', 'quarter', 'quarterback', 'question', 'quick', 'quickly', 'quiet', 'quietly', 'quit',
    'quote', 'race', 'racial', 'radical', 'radio', 'rail', 'rain', 'raise', 'range', 'rank', 'rapid', 'rapidly', 'rare',
    'rate', 'rather', 'rating', 'ratio', 'raw', 'reach', 'react', 'reaction', 'read', 'reader', 'reading', 'ready',
    'reality', 'realize', 'really', 'reason', 'reasonable', 'recall', 'receive', 'recent', 'recently', 'recipe',
    'recognize', 'recommend', 'recommendation', 'record', 'recording', 'recover', 'recovery', 'recruit', 'red',
    'reduction', 'refer', 'reference', 'reflect', 'reflection', 'reform', 'refugee', 'refuse', 'regard', 'regarding',
    'regime', 'region', 'regional', 'register', 'regular', 'regularly', 'regulate', 'regulation', 'reinforce', 'reject',
    'relation', 'relationship', 'relative', 'relatively', 'relax', 'release', 'relevant', 'relief', 'religion',
    'rely', 'remain', 'remaining', 'remarkable', 'remember', 'remind', 'remote', 'remove', 'repeat', 'repeatedly',
    'reply', 'report', 'reporter', 'represent', 'representation', 'representative', 'Republican', 'reputation',
    'require', 'requirement', 'research', 'researcher', 'resemble', 'reservation', 'resident', 'resist', 'resistance',
    'resolve', 'resort', 'resource', 'respect', 'respond', 'respondent', 'response', 'responsibility', 'responsible',
    'restaurant', 'restore', 'restriction', 'result', 'retain', 'retire', 'retirement', 'return', 'reveal', 'revenue',
    'revolution', 'rhythm', 'rice', 'rich', 'rid', 'ride', 'rifle', 'right', 'ring', 'rise', 'risk', 'river', 'road',
    'role', 'roll', 'romantic', 'roof', 'room', 'root', 'rope', 'rose', 'rough', 'roughly', 'round', 'route', 'routine',
    'rub', 'rule', 'run', 'running', 'rural', 'rush', 'Russian', 'sacred', 'sad', 'safe', 'safety', 'sake', 'salad',
    'sale', 'sales', 'salt', 'same', 'sample', 'sanction', 'sand', 'satellite', 'satisfaction', 'satisfy', 'sauce',
    'saving', 'say', 'scale', 'scandal', 'scared', 'scenario', 'scene', 'schedule', 'scheme', 'scholar', 'scholarship',
    'science', 'scientific', 'scientist', 'scope', 'score', 'scream', 'screen', 'script', 'sea', 'search', 'season',
    'second', 'secret', 'secretary', 'section', 'sector', 'secure', 'security', 'see', 'seed', 'seek', 'seem',
    'seize', 'select', 'selection', 'self', 'sell', 'Senate', 'senator', 'send', 'senior', 'sense', 'sensitive',
    'separate', 'sequence', 'series', 'serious', 'seriously', 'serve', 'service', 'session', 'set', 'setting', 'settle',
    'seven', 'several', 'severe', 'sex', 'sexual', 'shade', 'shadow', 'shake', 'shall', 'shape', 'share', 'sharp',
    'sheet', 'shelf', 'shell', 'shelter', 'shift', 'shine', 'ship', 'shirt', 'shit', 'shock', 'shoe', 'shoot',
    'shop', 'shopping', 'shore', 'short', 'shortly', 'shot', 'should', 'shoulder', 'shout', 'show', 'shower', 'shrug',
    'sick', 'side', 'sigh', 'sight', 'sign', 'signal', 'significance', 'significant', 'significantly', 'silence',
    'silver', 'similar', 'similarly', 'simple', 'simply', 'sin', 'since', 'sing', 'singer', 'single', 'sink', 'sir',
    'sit', 'site', 'situation', 'six', 'size', 'ski', 'skill', 'skin', 'sky', 'slave', 'sleep', 'slice', 'slide',
    'slightly', 'slip', 'slow', 'slowly', 'small', 'smart', 'smell', 'smile', 'smoke', 'smooth', 'snap', 'snow', 'so',
    'soccer', 'social', 'society', 'soft', 'software', 'soil', 'solar', 'soldier', 'solid', 'solution', 'solve', 'some',
    'somehow', 'someone', 'something', 'sometimes', 'somewhat', 'somewhere', 'son', 'song', 'soon', 'sophisticated',
    'sort', 'soul', 'sound', 'soup', 'source', 'south', 'southern', 'Soviet', 'space', 'Spanish', 'speak', 'speaker',
    'specialist', 'species', 'specific', 'specifically', 'speech', 'speed', 'spend', 'spending', 'spin', 'spirit',
    'split', 'spokesman', 'sport', 'spot', 'spread', 'spring', 'square', 'squeeze', 'stability', 'stable', 'staff',
    'stair', 'stake', 'stand', 'standard', 'standing', 'star', 'stare', 'start', 'state', 'statement', 'station',
    'status', 'stay', 'steady', 'steal', 'steel', 'step', 'stick', 'still', 'stir', 'stock', 'stomach', 'stone', 'stop',
    'store', 'storm', 'story', 'straight', 'strange', 'stranger', 'strategic', 'strategy', 'stream', 'street',
    'strengthen', 'stress', 'stretch', 'strike', 'string', 'strip', 'stroke', 'strong', 'strongly', 'structure',
    'student', 'studio', 'study', 'stuff', 'stupid', 'style', 'subject', 'submit', 'subsequent', 'substance',
    'succeed', 'success', 'successful', 'successfully', 'such', 'sudden', 'suddenly', 'sue', 'suffer', 'sufficient',
    'suggest', 'suggestion', 'suicide', 'suit', 'summer', 'summit', 'sun', 'super', 'supply', 'support', 'supporter',
    'supposed', 'Supreme', 'sure', 'surely', 'surface', 'surgery', 'surprise', 'surprised', 'surprising',
    'surround', 'survey', 'survival', 'survive', 'survivor', 'suspect', 'sustain', 'swear', 'sweep', 'sweet', 'swim',
    'switch', 'symbol', 'symptom', 'system', 'table', 'tablespoon', 'tactic', 'tail', 'take', 'tale', 'talent', 'talk',
    'tank', 'tap', 'tape', 'target', 'task', 'taste', 'tax', 'taxpayer', 'tea', 'teach', 'teacher', 'teaching', 'team',
    'teaspoon', 'technical', 'technique', 'technology', 'teen', 'teenager', 'telephone', 'telescope', 'television',
    'temperature', 'temporary', 'ten', 'tend', 'tendency', 'tennis', 'tension', 'tent', 'term', 'terms', 'terrible',
    'terror', 'terrorism', 'terrorist', 'test', 'testify', 'testimony', 'testing', 'text', 'than', 'thank', 'thanks',
    'the', 'theater', 'their', 'them', 'theme', 'themselves', 'then', 'theory', 'therapy', 'there', 'therefore',
    'they', 'thick', 'thin', 'thing', 'think', 'thinking', 'third', 'thirty', 'this', 'those', 'though', 'thought',
    'threat', 'threaten', 'three', 'throat', 'through', 'throughout', 'throw', 'thus', 'ticket', 'tie', 'tight', 'time',
    'tip', 'tire', 'tired', 'tissue', 'title', 'to', 'tobacco', 'today', 'toe', 'together', 'tomato', 'tomorrow',
    'tongue', 'tonight', 'too', 'tool', 'tooth', 'top', 'topic', 'toss', 'total', 'totally', 'touch', 'tough', 'tour',
    'tournament', 'toward', 'towards', 'tower', 'town', 'toy', 'trace', 'track', 'trade', 'tradition', 'traditional',
    'tragedy', 'trail', 'train', 'training', 'transfer', 'transform', 'transformation', 'transition', 'translate',
    'travel', 'treat', 'treatment', 'treaty', 'tree', 'tremendous', 'trend', 'trial', 'tribe', 'trick', 'trip', 'troop',
    'truck', 'true', 'truly', 'trust', 'truth', 'try', 'tube', 'tunnel', 'turn', 'TV', 'twelve', 'twenty', 'twice',
    'two', 'type', 'typical', 'typically', 'ugly', 'ultimate', 'ultimately', 'unable', 'uncle', 'under', 'undergo',
    'understanding', 'unfortunately', 'uniform', 'union', 'unique', 'unit', 'United', 'universal', 'universe',
    'unknown', 'unless', 'unlike', 'unlikely', 'until', 'unusual', 'up', 'upon', 'upper', 'urban', 'urge', 'us', 'use',
    'useful', 'user', 'usual', 'usually', 'utility', 'vacation', 'valley', 'valuable', 'value', 'variable', 'variation',
    'various', 'vary', 'vast', 'vegetable', 'vehicle', 'venture', 'version', 'versus', 'very', 'vessel', 'veteran',
    'victim', 'victory', 'video', 'view', 'viewer', 'village', 'violate', 'violation', 'violence', 'violent',
    'virtue', 'virus', 'visible', 'vision', 'visit', 'visitor', 'visual', 'vital', 'voice', 'volume', 'volunteer',
    'voter', 'vs', 'vulnerable', 'wage', 'wait', 'wake', 'walk', 'wall', 'wander', 'want', 'war', 'warm', 'warn',
    'wash', 'waste', 'watch', 'water', 'wave', 'way', 'we', 'weak', 'wealth', 'wealthy', 'weapon', 'wear', 'weather',
    'week', 'weekend', 'weekly', 'weigh', 'weight', 'welcome', 'welfare', 'well', 'west', 'western', 'wet', 'what',
    'wheel', 'when', 'whenever', 'where', 'whereas', 'whether', 'which', 'while', 'whisper', 'white', 'who', 'whole',
    'whose', 'why', 'wide', 'widely', 'widespread', 'wife', 'wild', 'will', 'willing', 'win', 'wind', 'window', 'wine',
    'winner', 'winter', 'wipe', 'wire', 'wisdom', 'wise', 'wish', 'with', 'withdraw', 'within', 'without', 'witness',
    'wonder', 'wonderful', 'wood', 'wooden', 'word', 'work', 'worker', 'working', 'works', 'workshop', 'world',
    'worry', 'worth', 'would', 'wound', 'wrap', 'write', 'writer', 'writing', 'wrong', 'yard', 'yeah', 'year', 'yell',
    'yes', 'yesterday', 'yet', 'yield', 'you', 'young', 'your', 'yours', 'yourself', 'youth', 'zone', 
]
# fmt: on

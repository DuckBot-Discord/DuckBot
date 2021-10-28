import datetime
import logging
import os
import traceback
from collections import defaultdict, deque, namedtuple

import typing
from openrobot.api_wrapper import AsyncClient as ORBClient
import tekore as tk
from typing import (
    List,
    Optional, Union
)

from dotenv import load_dotenv
import asyncpg
import asyncpraw

import aiohttp
import discord
import topgg
from discord.ext import commands
from discord.ext.commands.errors import (
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    NoEntryPointError
)
from asyncdagpi import Client as DagpiClient
from asyncdagpi import ImageFeatures
import asyncgur

from DuckBot import errors
from DuckBot.helpers.helper import LoggingEventsFlags
from DuckBot.helpers.context import CustomContext

initial_extensions = (
    'jishaku',
)

load_dotenv()

token_spotify = tk.request_client_token(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(message)s')

os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'
os.environ['JISHAKU_USE_BRAILLE_J'] = 'True'
os.environ['JISHAKU_HIDE'] = 'True'
target_type = Union[discord.Member, discord.User, discord.PartialEmoji, discord.Guild, discord.Invite, str]


async def create_db_pool() -> asyncpg.Pool:
    credentials = {
        "user": f"{os.getenv('PSQL_USER')}",
        "password": f"{os.getenv('PSQL_PASSWORD')}",
        "database": f"{os.getenv('PSQL_DB')}",
        "host": f"{os.getenv('PSQL_HOST')}",
        "port": f"{os.getenv('PSQL_PORT')}"
    }

    return await asyncpg.create_pool(**credentials)


class DuckBot(commands.Bot):
    PRE: tuple = ('db.',)

    def user_blacklisted(self, ctx: CustomContext):
        try:
            is_blacklisted = self.blacklist[ctx.author.id]
        except KeyError:
            is_blacklisted = False
        if ctx.author.id == self.owner_id:
            is_blacklisted = False

        if is_blacklisted is False:
            return True
        else:
            raise errors.UserBlacklisted

    def maintenance_mode(self, ctx: CustomContext):
        if not self.maintenance or ctx.author.id == bot.owner_id:
            return True
        else:
            raise errors.BotUnderMaintenance

    def __init__(self) -> None:
        intents = discord.Intents.all()
        # noinspection PyDunderSlots,PyUnresolvedReferences
        intents.typing = False

        super().__init__(
            intents=intents,
            command_prefix=self.get_pre,
            case_insensitive=True,
            activity=discord.Streaming(name="db.help", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            enable_debug_events=True,
            strip_after_prefix=True,

        )

        self.spotify = tk.Spotify(token_spotify, asynchronous=True)

        self.db: asyncpg.Pool = self.loop.run_until_complete(create_db_pool())

        self.reddit = asyncpraw.Reddit(client_id=os.getenv('ASYNC_PRAW_CID'),
                                       client_secret=os.getenv('ASYNC_PRAW_CS'),
                                       user_agent=os.getenv('ASYNC_PRAW_UA'),
                                       username=os.getenv('ASYNC_PRAW_UN'),
                                       password=os.getenv('ASYNC_PRAW_PA'))

        log_wh = self.log_webhooks = namedtuple('log_wh', ['default', 'message', 'member', 'join_leave', 'voice', 'server'])

        self.add_check(self.user_blacklisted)
        self.add_check(self.maintenance_mode)

        self.owner_id = 349373972103561218

        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Bot based stuff
        self.invite_url = "https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope" \
                          "=bot%20applications.commands "
        self.vote_top_gg = "https://top.gg/bot/788278464474120202#/"
        self.vote_bots_gg = "https://discord.bots.gg/bots/788278464474120202"
        self.repo = "https://github.com/LeoCx1000/discord-bots"
        self.maintenance = None
        self.noprefix = False
        self.started = False
        self.persistent_views_added = False
        self.uptime = datetime.datetime.utcnow()
        self.last_rall = datetime.datetime.utcnow()
        self.allowed_mentions = discord.AllowedMentions(replied_user=False)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.top_gg = topgg.DBLClient(self, os.getenv('TOPGG_TOKEN'))
        self.dev_mode = True if os.getenv('DEV_MODE') == 'yes' else False
        self.orb = ORBClient(token=os.getenv('OPENROBOT_KEY'))
        self.dagpi_cooldown = commands.CooldownMapping.from_cooldown(60, 60, commands.BucketType.default)
        self.dagpi_client = DagpiClient(os.getenv('DAGPI_TOKEN'))

        # Cache stuff
        self.lavalink = None
        self.invites = None
        self.prefixes = {}
        self.blacklist = {}
        self.afk_users = {}
        self.auto_un_afk = {}
        self.welcome_channels = {}
        self.suggestion_channels = {}
        self.counting_channels = {}
        self.counting_rewards = {}
        self.saved_messages = {}
        self.common_discrims = []
        self.log_channels: typing.Dict[int, log_wh] = {}
        self.log_cache = defaultdict(lambda: defaultdict(list))
        self.guild_loggings: typing.Dict[int, LoggingEventsFlags] = {}
        self.imgur = asyncgur.Imgur(client_id=os.getenv('IMGUR_CL_ID'))

        for ext in initial_extensions:
            self._load_extension(ext)

    def _load_extension(self, name: str) -> None:
        try:
            self.load_extension(name)
        except (ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed):
            traceback.print_exc()
            print()  # Empty line

    def _dynamic_cogs(self) -> None:
        for filename in os.listdir(f"{os.getenv('COGS_PATH')}"):
            if filename.endswith(".py"):
                cog = filename[:-3]
                logging.info(f"Trying to load cog: {cog}")
                self._load_extension(f'DuckBot.cogs.{cog}')

    async def get_pre(self, bot, message: discord.Message, raw_prefix: Optional[bool] = False) -> List[str]:
        if not message:
            return commands.when_mentioned_or(*self.PRE)(bot, message) if not raw_prefix else self.PRE
        if not message.guild:
            return commands.when_mentioned_or(*self.PRE)(bot, message) if not raw_prefix else self.PRE
        try:
            prefix = self.prefixes[message.guild.id]
        except KeyError:
            prefix = [x['prefix'] for x in
                      await bot.db.fetch('SELECT prefix FROM pre WHERE guild_id = $1', message.guild.id)] or self.PRE
            self.prefixes[message.guild.id] = prefix

        if await bot.is_owner(message.author) and bot.noprefix is True:
            return commands.when_mentioned_or(*prefix, "")(bot, message) if not raw_prefix else prefix
        return commands.when_mentioned_or(*prefix)(bot, message) if not raw_prefix else prefix

    async def fetch_prefixes(self, message):
        return tuple([x['prefix'] for x in
                      await self.db.fetch('SELECT prefix FROM pre WHERE guild_id = $1', message.guild.id)]) or self.PRE

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    # Event based
    async def on_ready(self) -> None:
        logging.info("\033[42m======[ BOT ONLINE! ]=======\033[0m")
        logging.info("\033[42mLogged in as " + self.user.name + "\033[0m")
        logging.info('\033[0m')
        if not self.started:
            self.started = True

            _temp_prefixes = defaultdict(list)
            for x in await bot.db.fetch('SELECT * FROM pre'):
                _temp_prefixes[x['guild_id']].append(x['prefix'] or self.PRE)
            self.prefixes = dict(_temp_prefixes)

            for guild in self.guilds:
                try:
                    self.prefixes[guild.id]
                except KeyError:
                    self.prefixes[guild.id] = self.PRE

            values = await self.db.fetch("SELECT user_id, is_blacklisted FROM blacklist")
            for value in values:
                self.blacklist[value['user_id']] = (value['is_blacklisted'] or False)

            values = await self.db.fetch("SELECT guild_id, welcome_channel FROM prefixes")
            for value in values:
                self.welcome_channels[value['guild_id']] = (value['welcome_channel'] or None)

            self.afk_users = dict(
                [(r['user_id'], True) for r in (await self.db.fetch('SELECT user_id, start_time FROM afk')) if
                 r['start_time']])
            self.auto_un_afk = dict(
                [(r['user_id'], r['auto_un_afk']) for r in (await self.db.fetch('SELECT user_id, auto_un_afk FROM afk'))
                 if r['auto_un_afk'] is not None])
            self.suggestion_channels = dict([(r['channel_id'], r['image_only']) for r in
                                             (await self.db.fetch('SELECT channel_id, image_only FROM suggestions'))])
            self.counting_channels = dict((x['guild_id'], {'channel': x['channel_id'],
                                                           'number': x['current_number'],
                                                           'last_counter': x['last_counter'],
                                                           'delete_messages': x['delete_messages'],
                                                           'reset': x['reset_on_fail'],
                                                           'last_message_id': None,
                                                           'messages': deque(maxlen=100)})
                                          for x in await self.db.fetch('SELECT * FROM count_settings'))

            for x in await bot.db.fetch('SELECT * FROM counting'):
                try:
                    self.counting_rewards[x['guild_id']].add(x['reward_number'])
                except KeyError:
                    self.counting_rewards[x['guild_id']] = {x['reward_number']}

            for entry in await self.db.fetch('SELECT * FROM log_channels'):
                guild_id = entry['guild_id']

                self.log_channels[guild_id] = self.log_webhooks(default=entry['default_channel'],
                                                                message=entry['message_channel'],
                                                                join_leave=entry['join_leave_channel'],
                                                                member=entry['member_channel'],
                                                                voice=entry['voice_channel'],
                                                                server=entry['server_channel'])

                flags = dict(await bot.db.fetchrow('SELECT message_delete, message_purge, message_edit, member_join, member_leave, member_update, user_ban, user_unban, '
                                                   'user_update, invite_create, invite_delete, voice_join, voice_leave, voice_move, voice_mod, emoji_create, emoji_delete, '
                                                   'emoji_update, sticker_create, sticker_delete, sticker_update, server_update, stage_open, stage_close, channel_create, '
                                                   'channel_delete, channel_edit, role_create, role_delete, role_edit FROM logging_events WHERE guild_id = $1', guild_id))
                self.guild_loggings[guild_id] = LoggingEventsFlags(**flags)

            print('All cache populated successfully')

            self._dynamic_cogs()

            print('Loading cogs done.')

    async def on_message(self, message: discord.Message) -> Optional[discord.Message]:
        if self.user:
            if message.content == f'<@!{self.user.id}>':  # Sets faster
                prefix = await self.get_pre(self, message, raw_prefix=True)
                if isinstance(prefix, str):
                    return await message.reply(f"For a list of commands do `{prefix}help` 💞")
                elif isinstance(prefix, (tuple, list)):
                    return await message.reply(f"My prefixes here are `{'`, `'.join(prefix)}`"
                                               f"\n For a list of commands do`{prefix[0]}help` 💞")
        await self.process_commands(message)

    def get_mapping(self):
        mapping = {cog: cog.get_commands() for cog in self.cogs.values()}
        mapping[None] = [c for c in self.commands if c.cog is None]
        return mapping

    async def create_gist(self, *, filename: str, description: str, content: str, public: bool = True):
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'DuckBot-Discord',
            'Authorization': f'token {os.getenv("GH_TOKEN")}'
        }

        data = {
            'public': public,
            'files': {
                filename: {
                    'content': content
                }
            },
            'description': description
        }
        output = await self.session.request("POST", "https://api.github.com/gists", json=data, headers=headers)
        info = await output.json()
        return info['html_url']

    async def get_welcome_channel(self, member: discord.Member):
        if not isinstance(member, discord.Member):
            raise errors.NoWelcomeChannel
        try:
            channel = self.welcome_channels[member.guild.id]
        except KeyError:
            raise errors.NoWelcomeChannel

        if not channel:
            raise errors.NoWelcomeChannel

        welcome_channel = member.guild.get_channel(channel) or (await member.guild.fetch_channel(channel))
        if not welcome_channel:
            self.welcome_channels[member.guild.id] = None
            raise errors.NoWelcomeChannel
        return welcome_channel

    async def _fetch_role_icon(self, guild_id: int, role_id: int, size: int = 64) -> str:
        guild = self.get_guild(guild_id)
        if not guild or 'ROLE_ICONS' not in guild.features:
            return None
        role = guild.get_role(role_id)
        if not role:
            return None

        resp = await guild._state.http.get_roles(guild.id)
        role_asset = {r['id']: r['icon'] for r in resp}[str(role_id)]

        if not role_asset:
            return None

        return f"https://cdn.discordapp.com/role-icons/{role_id}/{role_asset}.png?size={size}"

    async def dagpi_request(self, ctx: CustomContext, target: target_type = None, *, feature: ImageFeatures, **kwargs) -> discord.File:
        bucket = self.dagpi_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(commands.Cooldown(60, 60), retry_after, commands.BucketType.default)
        target = target or ctx.author
        url = getattr(target, 'display_avatar', None) or getattr(target, 'icon', None) or getattr(target, 'guild', None) or target
        url = getattr(getattr(url, 'icon', url), 'url', url)
        request = await self.dagpi_client.image_process(feature, url, **kwargs)
        return discord.File(fp=request.image, filename=f"DuckBot-{str(feature)}.{request.format}")

    def update_log(self, deliver_type: str, webhook_url: str, guild_id: int):
        if deliver_type == 'default':
            self.log_channels[guild_id]._replace(default=webhook_url)
        elif deliver_type == 'message':
            self.log_channels[guild_id]._replace(message=webhook_url)
        elif deliver_type == 'member':
            self.log_channels[guild_id]._replace(member=webhook_url)
        elif deliver_type == 'join_leave':
            self.log_channels[guild_id]._replace(join_leave=webhook_url)
        elif deliver_type == 'voice':
            self.log_channels[guild_id]._replace(voice=webhook_url)
        elif deliver_type == 'server':
            self.log_channels[guild_id]._replace(server=webhook_url)

    async def upload_imgur(self, *, title: str = 'By DuckBot', name: str = 'By DuckBot', description: str = 'Uploaded by DuckBot Discord', image: typing.Union[str, bytes] = None, video: typing.Union[str, bytes] = None):
        if not image and not video:
            raise AttributeError('You did not provide an image or video!')
        url, response = await self.imgur.upload_image(title=title, name=name, description=description, image=image, video=video)
        if response.success is True and response.status == 200:
            return url.link
        raise discord.HTTPException(response=response, message='Could not upload to Imgur')


if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot = DuckBot()
    bot.run(TOKEN, reconnect=True)

import datetime
import logging
import os
import traceback
import tekore as tk
from typing import (
    List,
    Optional
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

from DuckBot import errors
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

os.environ['JISHAKU_HIDE'] = 'True'


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

    def blacklist(self, ctx: CustomContext):
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

    def __init__(self) -> None:
        self.invites = None
        intents = discord.Intents(members=True, dm_typing=False, guild_typing=False,
                                  **{k: v for k, v in dict(discord.Intents.default()).items()
                                     if k not in ('members', 'guild_typing', 'dm_typing')})

        super().__init__(
            intents=intents,
            command_prefix=self.get_pre,
            case_insensitive=True,
            activity=discord.Activity(type=discord.ActivityType.listening, name='db.help'),
            enable_debug_events=True,
            strip_after_prefix=True
        )

        self.spotify = tk.Spotify(token_spotify, asynchronous=True)

        self.db: asyncpg.Pool = self.loop.run_until_complete(create_db_pool())

        self.reddit = asyncpraw.Reddit(client_id=os.getenv('ASYNC_PRAW_CID'),
                                       client_secret=os.getenv('ASYNC_PRAW_CS'),
                                       user_agent=os.getenv('ASYNC_PRAW_UA'),
                                       username=os.getenv('ASYNC_PRAW_UN'),
                                       password=os.getenv('ASYNC_PRAW_PA'))

        self.add_check(self.blacklist)

        self.owner_id = 349373972103561218

        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Bot based stuff
        self.invite_url = "https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope" \
                          "=bot%20applications.commands "
        self.vote_top_gg = "https://top.gg/bot/788278464474120202#/"
        self.vote_bots_gg = "https://discord.bots.gg/bots/788278464474120202"
        self.repo = "https://github.com/LeoCx1000/discord-bots"
        self.maintenance = False
        self.noprefix = False
        self.started = False
        self.persistent_views_added = False
        self.uptime = datetime.datetime.utcnow()
        self.last_rall = datetime.datetime.utcnow()
        self.prefixes = {}
        self.blacklist = {}
        self.afk_users = {}
        self.welcome_channels = {}
        self.allowed_mentions = discord.AllowedMentions(replied_user=False)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.top_gg = topgg.DBLClient(self, os.getenv('TOPGG_TOKEN'))

        for ext in initial_extensions:
            self._load_extension(ext)
        self._dynamic_cogs()

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
            prefix = (await self.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1',
                                             message.guild.id)) or self.PRE
            prefix = prefix if prefix[0] else self.PRE

            self.prefixes[message.guild.id] = prefix

        if await bot.is_owner(message.author) and bot.noprefix is True:
            return commands.when_mentioned_or(*prefix, "")(bot, message) if not raw_prefix else prefix
        return commands.when_mentioned_or(*prefix)(bot, message) if not raw_prefix else prefix

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    # Event based
    async def on_ready(self) -> None:
        logging.info("\033[42m======[ BOT ONLINE! ]=======\033[0m")
        logging.info("\033[42mLogged in as " + self.user.name + "\033[0m")
        logging.info('\033[0m')
        if not self.started:
            self.started = True

            values = await self.db.fetch("SELECT guild_id, prefix FROM prefixes")

            for value in values:
                if value['prefix']:
                    self.prefixes[value['guild_id']] = (
                            (value['prefix'] if value['prefix'][0] else self.PRE) or self.PRE)

            for guild in self.guilds:
                if not guild.unavailable:
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

            self.afk_users = dict([(r['user_id'], True) for r in (await self.db.fetch('SELECT user_id FROM afk'))])

    async def on_message(self, message: discord.Message) -> Optional[discord.Message]:
        if all((self.maintenance is True, message.author.id != self.owner_id)):
            return

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


if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot = DuckBot()
    bot.run(TOKEN, reconnect=True)

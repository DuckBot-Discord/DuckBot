import datetime
import io
import json
import logging
import os
import re
import traceback
from collections import defaultdict
from typing import (
    List,
    Optional,
    Union,
    Any
)

import aiohttp
import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands.errors import (
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    NoEntryPointError
)
from dotenv import load_dotenv

from ozbot import helpers, slash_utils

initial_extensions = (
    'jishaku',
)

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(message)s')

os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'
os.environ['JISHAKU_USE_BRAILLE_J'] = 'True'
os.environ['JISHAKU_HIDE'] = 'True'
target_type = Union[discord.Member, discord.User, discord.PartialEmoji, discord.Guild, discord.Invite, str]


class Ozbot(slash_utils.Bot):
    PRE: tuple = ('!', )

    def __init__(self) -> None:
        intents = discord.Intents.all()
        # noinspection PyDunderSlots,PyUnresolvedReferences
        intents.typing = False

        super().__init__(
            intents=intents,
            command_prefix=self.get_pre,
            case_insensitive=True,
            activity=discord.Activity(type=discord.ActivityType.watching, name="over OZ"),
            enable_debug_events=True,
            strip_after_prefix=True,
            slash_command_guilds=[706624339595886683]

        )

        self.owner_id = 349373972103561218

        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Bot based stuff
        self.uptime = datetime.datetime.utcnow()
        self.last_rall = datetime.datetime.utcnow()
        self.allowed_mentions = discord.AllowedMentions.none()
        self.session: aiohttp.ClientSession = None

        # Cache stuff
        self.prefixes = {}

        for ext in initial_extensions:
            self._load_extension(ext)

        self.loop.create_task(self.populate_cache())
        self.loop.create_task(self.dynamic_load_cogs())
        self.db: asyncpg.Pool = self.loop.run_until_complete(self.create_db_pool())

    def _load_extension(self, name: str) -> None:
        try:
            self.load_extension(name)
        except (ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed):
            traceback.print_exc()
            print()  # Empty line

    async def dynamic_load_cogs(self) -> None:
        for filename in os.listdir(f"cogs"):
            if filename.endswith(".py"):
                cog = filename[:-3]
                logging.info(f"Trying to load cog: {cog}")
                self._load_extension(f'cogs.{cog}')
        logging.info('Loading cogs done.')
        self.dispatch('restart_complete')

    async def get_pre(self, bot, message: discord.Message, raw_prefix: Optional[bool] = False) -> List[str]:
        if not message:
            return commands.when_mentioned_or(*self.PRE)(bot, message) if not raw_prefix else self.PRE
        if not message.guild:
            return commands.when_mentioned_or(*self.PRE)(bot, message) if not raw_prefix else self.PRE
        try:
            prefix = self.prefixes[message.guild.id]
        except KeyError:
            prefix = [x['prefix'] for x in await bot.db.fetch('SELECT prefix FROM pre WHERE guild_id = $1', message.guild.id)] or self.PRE
            self.prefixes[message.guild.id] = prefix
        return commands.when_mentioned_or(*prefix)(bot, message) if not raw_prefix else prefix

    async def on_ready(self) -> None:
        e = "\033[0m"
        s = "\033[42m"
        logging.info("======[ BOT ONLINE! ]=======")
        logging.info("\033[42mLogged in as " + self.user.name + "\033[0m")

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        traceback_string = traceback.format_exc()
        for line in traceback_string.split('\n'):
            logging.info(line)
        await self.wait_until_ready()
        error_channel = self.get_channel(880181130408636456)
        to_send = f"```yaml\nAn error occurred in an {event_method} event``````py" \
                  f"\n{traceback_string}\n```"
        if len(to_send) < 2000:
            try:
                await error_channel.send(to_send)

            except (discord.Forbidden, discord.HTTPException):

                await error_channel.send(f"```yaml\nAn error occurred in an {event_method} event``````py",
                                         file=discord.File(io.StringIO(traceback_string), filename='traceback.py'))
        else:
            await error_channel.send(f"```yaml\nAn error occurred in an {event_method} event``````py",
                                     file=discord.File(io.StringIO(traceback_string), filename='traceback.py'))

    async def setup(self):
        return

    async def on_interaction(self, interaction: discord.Interaction):
        return

    async def populate_cache(self):
        _temp_prefixes = defaultdict(list)
        for x in await self.db.fetch('SELECT * FROM pre'):
            _temp_prefixes[x['guild_id']].append(x['prefix'] or self.PRE)
        self.prefixes = dict(_temp_prefixes)
        logging.info('All cache populated successfully')

        async def _populate_guild_cache():
            await self.wait_until_ready()
            for guild in self.guilds:
                try:
                    self.prefixes[guild.id]
                except KeyError:
                    self.prefixes[guild.id] = self.PRE
        self.loop.create_task(_populate_guild_cache())
        self.dispatch('cache_ready')

    async def start(self, *args, **kwargs):
        self.session = aiohttp.ClientSession()
        await super().start(*args, **kwargs)

    async def close(self):
        await self.db.close()
        await self.session.close()
        await super().close()

    async def create_db_pool(self) -> asyncpg.Pool:
        credentials = {
            "user": f"{os.getenv('PSQL_USER')}",
            "password": f"{os.getenv('PSQL_PASSWORD')}",
            "database": f"{os.getenv('PSQL_DB')}",
            "host": f"{os.getenv('PSQL_HOST')}"
        }

        try:
            return await asyncpg.create_pool(**credentials)
        except Exception as e:
            logging.error("Could not create database pool", exc_info=e)
        finally:
            logging.info('Database successful.')
            self.dispatch('pool_create')


if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot = Ozbot()

    @bot.check
    async def oz_only(ctx: commands.Context) -> bool:
        if await bot.is_owner(ctx.author):
            return True
        if not ctx.guild:
            raise helpers.NotOz
        if ctx.guild.id != 706624339595886683:
            raise helpers.NotOz
        return True


    bot.run(TOKEN, reconnect=True)

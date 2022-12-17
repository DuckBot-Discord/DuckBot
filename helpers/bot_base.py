import contextlib
import datetime
import io
import logging
import os
import re
import sys
import traceback
import typing
from collections import defaultdict, deque
from typing import Dict, Iterable, List, Optional, Any, TYPE_CHECKING, Type

import aiohttp
import aiohttp.web
import asyncpg
import asyncpraw
import discord
import topgg
from asyncdagpi.client import Client as DagpiClient
from discord.ext import commands
from dotenv import load_dotenv
from discord.ext import commands

from cogs.economy.helper_classes import Wallet
from helpers import constants
from helpers.context import CustomContext
from helpers.helper import LoggingEventsFlags

if TYPE_CHECKING:
    from cogs.moderation.snipe import SimpleMessage
else:
    SimpleMessage = None

initial_extensions = ("jishaku",)

extensions = (
    "cogs.beta",
    "cogs.logs",
    "cogs.economy",
    "cogs.events",
    "cogs.fun",
    "cogs.guild_config",
    "cogs.hideout",
    "cogs.image_manipulation",
    "cogs.info",
    "cogs.management",
    "cogs.modmail",
    "cogs.test",
    "cogs.utility",
    "cogs.moderation",
)
load_dotenv()


def col(color=None, /, *, fmt=0, bg=False):
    base = "\u001b["
    if fmt != 0:
        base += "{fmt};"
    if color is None:
        base += "{color}m"
        color = 0
    else:
        if bg is True:
            base += "4{color}m"
        else:
            base += "3{color}m"
    return base.format(fmt=fmt, color=color)


def get_or_fail(var: str) -> str:
    v = os.getenv(var)
    if v is None:
        raise Exception(f"{var!r} is not set in the .env file")
    return v


class LoggingConfig:
    __slots__ = ("default", "message", "member", "join_leave", "voice", "server")

    def __init__(self, default, message, member, join_leave, voice, server):
        self.default = default
        self.message = message
        self.member = member
        self.join_leave = join_leave
        self.voice = voice
        self.server = server

    def _replace(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class BaseDuck(commands.AutoShardedBot):
    PRE: tuple = ("db.",)
    logger = logging.getLogger("logging")
    _ext_log = logging.getLogger("extensions")
    user: discord.ClientUser

    def __init__(self, pool: asyncpg.Pool, session: aiohttp.ClientSession) -> None:
        intents = discord.Intents.all()
        # noinspection PyDunderSlots,PyUnresolvedReferences
        intents.typing = False

        super().__init__(
            intents=intents,
            command_prefix=self.get_pre,
            case_insensitive=True,
            activity=discord.Streaming(name="db.help", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            strip_after_prefix=True,
            chunk_guilds_at_startup=False,
        )

        self.db = pool
        self.session = session

        self.log_webhooks: Type[LoggingConfig] = LoggingConfig
        self.allowed_mentions = discord.AllowedMentions.none()

        self.reddit = asyncpraw.Reddit(
            client_id=get_or_fail("ASYNC_PRAW_CID"),
            client_secret=get_or_fail("ASYNC_PRAW_CS"),
            user_agent=get_or_fail("ASYNC_PRAW_UA"),
            username=get_or_fail("ASYNC_PRAW_UN"),
            password=get_or_fail("ASYNC_PRAW_PA"),
        )

        self.owner_id = 349373972103561218

        # noinspection PyProtectedMember
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Bot based stuff
        self.invite_url = (
            "https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope"
            "=bot%20applications.commands "
        )
        self.vote_top_gg = "https://top.gg/bot/788278464474120202"
        self.vote_bots_gg = "https://discord.bots.gg/bots/788278464474120202"
        self.repo = "https://github.com/DuckBot-Discord/DuckBot"
        self.maintenance = None
        self.noprefix = False
        self.persistent_views_added = False
        self.uptime = self.last_rall = datetime.datetime.utcnow()
        self.top_gg = topgg.client.DBLClient(get_or_fail("TOPGG_TOKEN"))
        self.dev_mode = True if os.getenv("DEV_MODE") == "yes" else False
        self.dagpi_cooldown = commands.CooldownMapping.from_cooldown(60, 60, commands.BucketType.default)
        self.dagpi_client = DagpiClient(get_or_fail("DAGPI_TOKEN"))
        self.constants = constants

        # Cache stuff
        self.prefixes: Dict[int, Iterable[str]] = {}
        self.blacklist = {}
        self.afk_users = {}
        self.auto_un_afk = {}
        self.welcome_channels = {}
        self.suggestion_channels = {}
        self.dm_webhooks = defaultdict(str)
        self.wallets: typing.Dict[str, Wallet] = {}
        self.counting_channels = {}
        self.counting_rewards = {}
        self.saved_messages = {}
        self.common_discrims = []
        self.log_channels: typing.Dict[int, LoggingConfig] = {}
        self.log_cache = defaultdict(lambda: defaultdict(list))
        self.guild_loggings: typing.Dict[int, LoggingEventsFlags] = {}
        self.snipes: typing.Dict[int, typing.Dict[int, typing.Deque[SimpleMessage]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=50))
        )

        self.global_mapping = commands.CooldownMapping.from_cooldown(10, 12, commands.BucketType.user)

        self.invites: Dict[int, Dict[str, discord.Invite]] = {}
        if TYPE_CHECKING:
            self.expiring_invites = {}
            self.shortest_invite: int = 0
            self.last_update: int = 0

    async def setup_hook(self) -> None:
        await self.populate_cache()

        for ext in initial_extensions:
            await self.load_extension(ext, _raise=False)

        for ext in extensions:
            await self.load_extension(ext, _raise=False)

    async def get_pre(self, bot, message: discord.Message, raw_prefix: Optional[bool] = False) -> Iterable[str]:
        if not message:
            return commands.when_mentioned_or(*self.PRE)(bot, message) if not raw_prefix else self.PRE
        if not message.guild:
            return commands.when_mentioned_or(*self.PRE)(bot, message) if not raw_prefix else self.PRE
        try:
            prefix = self.prefixes[message.guild.id]
        except KeyError:
            prefix = [
                x["prefix"] for x in await bot.db.fetch("SELECT prefix FROM pre WHERE guild_id = $1", message.guild.id)
            ] or self.PRE
            self.prefixes[message.guild.id] = prefix

        should_noprefix = False
        if not message.content.startswith(("jishaku", "eval", "jsk", "ev", "rall", "dev", "rmsg")):
            pass
        elif not message.guild:
            should_noprefix = True
        elif not message.guild.get_member(788278464474120202):
            should_noprefix = True

        if await bot.is_owner(message.author) and (bot.noprefix is True or should_noprefix):
            return commands.when_mentioned_or(*prefix, "")(bot, message) if not raw_prefix else prefix
        return commands.when_mentioned_or(*prefix)(bot, message) if not raw_prefix else prefix

    async def fetch_prefixes(self, message):
        prefixes = [x["prefix"] for x in await self.db.fetch("SELECT prefix FROM pre WHERE guild_id = $1", message.guild.id)]
        if not prefixes:
            await self.db.execute(
                "INSERT INTO pre (guild_id, prefix) VALUES ($1, $2)",
                message.guild.id,
                self.PRE[0],
            )
            return tuple(await self.fetch_prefixes(message))
        return tuple(prefixes)

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    async def on_ready(self) -> None:
        self.logger.info(f"{col(2)}======[ BOT ONLINE! ]======={col()}")
        self.logger.info(f"{col(2, bg=True)}Logged in as {self.user} {col()}")

    async def on_message(self, message: discord.Message) -> None:
        await self.wait_until_ready()
        if self.user:
            if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
                prefix = await self.get_pre(self, message, raw_prefix=True)
                if isinstance(prefix, str):
                    await message.reply(f"For a list of commands do `{prefix}help` 💞")
                elif isinstance(prefix, (tuple, list)):
                    await message.reply(
                        f"My prefixes here are `{'`, `'.join(prefix[0:10])}`\n"
                        f"For a list of commands do`{prefix[0]}help` 💞"[0:2000]
                    )
        await self.process_commands(message)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        traceback_string = ''.join(traceback.format_exception(*(einfo := sys.exc_info())))
        self.logger.error('Unhandled exception in event %s', event_method, exc_info=einfo)
        await self.wait_until_ready()

        error_channel: discord.TextChannel = self.get_channel(880181130408636456)  # type: ignore # known ID

        to_send = f"```yaml\nAn error occurred in an {event_method} event``````py" f"\n{traceback_string}\n```"
        if len(to_send) < 2000:
            try:
                await error_channel.send(to_send)

            except (discord.Forbidden, discord.HTTPException):

                await error_channel.send(
                    f"```yaml\nAn error occurred in an {event_method} event``````py",
                    file=discord.File(
                        io.BytesIO(traceback_string.encode()),
                        filename="traceback.py",
                    ),
                )
        else:
            await error_channel.send(
                f"```yaml\nAn error occurred in an {event_method} event``````py",
                file=discord.File(
                    io.BytesIO(traceback_string.encode()),
                    filename="traceback.py",
                ),
            )

    async def populate_cache(self):
        _temp_prefixes = defaultdict(list)
        for x in await self.db.fetch("SELECT * FROM pre"):
            _temp_prefixes[x["guild_id"]].append(x["prefix"] or self.PRE)
        self.prefixes = dict(_temp_prefixes)

        async def _populate_guild_cache():
            await self.wait_until_ready()
            for guild in self.guilds:
                try:
                    self.prefixes[guild.id]
                except KeyError:
                    self.prefixes[guild.id] = self.PRE

        self.loop.create_task(_populate_guild_cache())

        values = await self.db.fetch("SELECT user_id, is_blacklisted FROM blacklist")
        for value in values:
            self.blacklist[value["user_id"]] = value["is_blacklisted"] or False

        values = await self.db.fetch("SELECT guild_id, welcome_channel FROM prefixes")
        for value in values:
            self.welcome_channels[value["guild_id"]] = value["welcome_channel"] or None

        self.afk_users = dict(
            [(r["user_id"], True) for r in (await self.db.fetch("SELECT user_id, start_time FROM afk")) if r["start_time"]]
        )
        self.auto_un_afk = dict(
            [
                (r["user_id"], r["auto_un_afk"])
                for r in (await self.db.fetch("SELECT user_id, auto_un_afk FROM afk"))
                if r["auto_un_afk"] is not None
            ]
        )
        self.suggestion_channels = dict(
            [
                (r["channel_id"], r["image_only"])
                for r in (await self.db.fetch("SELECT channel_id, image_only FROM suggestions"))
            ]
        )
        self.counting_channels = dict(
            (
                x["guild_id"],
                {
                    "channel": x["channel_id"],
                    "number": x["current_number"],
                    "last_counter": x["last_counter"],
                    "delete_messages": x["delete_messages"],
                    "reset": x["reset_on_fail"],
                    "last_message_id": None,
                    "messages": deque(maxlen=100),
                },
            )
            for x in await self.db.fetch("SELECT * FROM count_settings")
        )

        for x in await self.db.fetch("SELECT * FROM counting"):
            try:
                self.counting_rewards[x["guild_id"]].add(x["reward_number"])
            except KeyError:
                self.counting_rewards[x["guild_id"]] = {x["reward_number"]}

        for entry in await self.db.fetch("SELECT * FROM log_channels"):
            guild_id = entry["guild_id"]
            await self.db.execute(
                "INSERT INTO logging_events(guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
                entry["guild_id"],
            )

            self.log_channels[guild_id] = LoggingConfig(
                default=entry["default_channel"],
                message=entry["message_channel"],
                join_leave=entry["join_leave_channel"],
                member=entry["member_channel"],
                voice=entry["voice_channel"],
                server=entry["server_channel"],
            )

            flags = dict(
                await self.db.fetchrow(
                    "SELECT message_delete, message_purge, message_edit, member_join, member_leave, member_update, user_ban, user_unban, "
                    "user_update, invite_create, invite_delete, voice_join, voice_leave, voice_move, voice_mod, emoji_create, emoji_delete, "
                    "emoji_update, sticker_create, sticker_delete, sticker_update, server_update, stage_open, stage_close, channel_create, "
                    "channel_delete, channel_edit, role_create, role_delete, role_edit FROM logging_events WHERE guild_id = $1",
                    guild_id,
                )
            )
            self.guild_loggings[guild_id] = LoggingEventsFlags(**flags)

        self.logger.info(f"{col(2)}All cache populated successfully")
        self.dispatch("cache_ready")

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)

    async def load_extension(self, name: str, *, package: Optional[str] = None, _raise: bool = True) -> None:
        self._ext_log.info(f"{col(7)}Attempting to load {col(7, fmt=4)}{name}{col()}")
        try:
            await super().load_extension(name, package=package)
            self._ext_log.info(f"{col(2)}Loaded extension {col(2, fmt=4)}{name}{col()}")
        except Exception as e:
            self._ext_log.error(f"Failed to load extension {name}", exc_info=e)
            if _raise:
                raise e

    async def unload_extension(self, name: str, *, package: Optional[str] = None, _raise: bool = True) -> None:
        self._ext_log.info(f"{col(7)}Attempting to unload extension {col(7, fmt=4)}{name}{col()}")
        try:
            await super().unload_extension(name, package=package)
            self._ext_log.info(f"{col(2)}Unloaded extension {col(2, fmt=4)}{name}{col()}")
        except Exception as e:
            self._ext_log.error(f"Failed to unload extension {name}", exc_info=e)
            if _raise:
                raise e

    async def reload_extension(self, name: str, *, package: Optional[str] = None, _raise: bool = True) -> None:
        self._ext_log.info(f"{col(7)}Attempting to reload extension {col(7, fmt=4)}{name}{col()}")
        try:
            await super().reload_extension(name, package=package)
            self._ext_log.info(f"{col(2)}Reloaded extension {col(2, fmt=4)}{name}{col()}")
        except Exception as e:
            self._ext_log.error(f"Failed to reload extension {name}", exc_info=e)
            if _raise:
                raise e

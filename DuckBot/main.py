import datetime
import logging
import os
import traceback
from typing import Final, List, Optional

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands.errors import (
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    NoEntryPointError
)

initial_extensions = (
    'jishaku',
)


class CustomContext(commands.Context):

    @staticmethod
    def tick(opt: bool, text: str = None) -> str:
        ticks = {
            True: '<:greenTick:596576670815879169>',
            False: '<:redTick:596576672149667840>',
            None: '<:greyTick:860644729933791283>',
        }
        emoji = ticks.get(opt, "<:redTick:596576672149667840>")
        if text:
            return f"{emoji} {text}"
        return emoji

    @staticmethod
    def default_tick(opt: bool, text: str = None) -> str:
        ticks = {
            True: '✅',
            False: '❌',
            None: '➖',
        }
        emoji = ticks.get(opt, "❌")
        if text:
            return f"{emoji} {text}"
        return emoji

    @staticmethod
    def square_tick(opt: bool, text: str = None) -> str:
        ticks = {
            True: '🟩',
            False: '🟥',
            None: '⬛',
        }
        emoji = ticks.get(opt, "🟥")
        if text:
            return f"{emoji} {text}"
        return emoji

class DuckBot(commands.Bot):
    PRE: str = 'db.'

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            intents=intents,
            command_prefix=self.get_pre,
            case_insensitive=True,
            activity=discord.Activity(type=discord.ActivityType.listening, name='db.help')
        )
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

        self.session = aiohttp.ClientSession(loop=self.loop)

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
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog = filename[:-3]
                logging.info(f"Trying to load cog: {cog}")
                self._load_extension(f'cogs.{cog}')

    async def get_pre(self, bot, message: discord.Message, raw_prefix: Optional[bool] = False) -> List[str]:
        if not message:
            return commands.when_mentioned_or(self.PRE)(bot, message) if not raw_prefix else self.PRE
        if not message.guild:
            return commands.when_mentioned_or(self.PRE)(bot, message) if not raw_prefix else self.PRE
        try:
            prefix = self.prefixes[message.guild.id]
        except KeyError:
            prefix = await self.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1', message.guild.id)
            if not prefix:
                prefix = self.PRE

            self.prefixes[message.guild.id] = prefix

        if await bot.is_owner(message.author) and bot.noprefix is True:
            return commands.when_mentioned_or(prefix, "")(bot, message) if not raw_prefix else prefix
        return commands.when_mentioned_or(prefix)(bot, message) if not raw_prefix else prefix

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    # Event based
    async def on_ready(self) -> None:
        logging.info("\033[42m======[ BOT ONLINE! ]=======")
        logging.info("Logged in as " + self.user.name)
        logging.info('\033[0m')
        if not self.started:
            self.started = True

            values = await self.db.fetch("SELECT guild_id, prefix FROM prefixes")
            for value in values:
                self.prefixes[value['guild_id']] = value['prefix']
            for guild in self.guilds:
                try:
                    self.prefixes[guild.id]
                except KeyError:
                    self.prefixes[guild.id] = self.PRE

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

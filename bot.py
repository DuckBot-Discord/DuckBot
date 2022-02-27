import re
import logging
import discord

from typing import List
from discord.ext import commands
from collections import defaultdict
from dotenv import load_dotenv

from cogs.utils.context import DuckContext
from cogs.utils.helpers import col


load_dotenv()
fmt = f'{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)


class DuckBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.typing = False  # noqa

        super().__init__(
            command_prefix=('dbb.', 'Dbb.', 'DBB.'),
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=intents
        )
        self.prefix_cache = defaultdict(set)
        self.logger = logging.getLogger('DuckBot.main')

    async def get_prefix(self, message: discord.Message, raw: bool = False) -> List[str]:
        """
        Returns the prefixes for the given message.
        if raw is True, returns the prefixes without the bots mention.
        """
        meth = commands.when_mentioned_or if raw is False else lambda *pres: lambda _, __: list(pres)

        if message.guild:
            prefixes = self.prefix_cache.get(message.guild.id) or self.command_prefix
        else:
            prefixes = self.command_prefix

        return meth(*prefixes)(self, message)

    async def get_context(self, message, *, cls=DuckContext):
        return await super().get_context(message, cls=cls)

    async def on_connect(self):
        self.logger.info(f'{col(2)}Logged in as {self.user}! ({self.user.id})')

    async def on_ready(self):
        self.logger.info(f'{col(2)}All guilds are chunked and ready to go!')

    async def on_message(self, message):
        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            prefixes = await self.get_prefix(message, raw=True)
            return await message.reply(
                f"My prefixes here are `{'`, `'.join(prefixes[0:10])}`\n"
                f"For a list of commands do`{prefixes[0]}help` 💞"[0:2000])
        await self.process_commands(message)

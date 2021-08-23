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


class DuckBot(commands.Bot):
    PRE: Final[str] = 'db.'
    
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            intents=intents,
            command_prefix=self.get_pre,
            case_insensitive=True
        )
        self.owner_id = 349373972103561218
        
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        
        # Bot based stuff
        self.invite_url="https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope=bot%20applications.commands"
        self.vote_top_gg="https://top.gg/bot/788278464474120202#/"
        self.vote_bots_gg="https://discord.bots.gg/bots/788278464474120202"
        self.repo="https://github.com/LeoCx1000/discord-bots"
        self.maintenance = False
        self.noprefix  = False
        self.started = False
        self.persistent_views_added = False
        self.uptime = datetime.datetime.utcnow()
        self.last_rall = datetime.datetime.utcnow()
        
        self.session = aiohttp.ClientSession(loop=self.loop)
        
        for ext in initial_extensions:
            self._load_extension(ext)
        self._dynamic_cogs()
        
    def _load_extension(self, name: str) -> None:
        try:
            self.load_extension(name)
        except (ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed):
            traceback.print_exc()
            print() # Empty line
    
    def _dynamic_cogs(self) -> None:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog = filename[:-3]
                self._load_extension(cog)
        
    async def get_pre(self, bot, message: discord.Message, raw_prefix: Optional[bool] = False) -> List[str]:
        if not message.guild:
            return commands.when_mentioned_or(self.PRE)(bot,message)
        prefix = await bot.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1', message.guild.id)
        if await bot.is_owner(message.author) and bot.noprefix == True:
            if prefix:
                return commands.when_mentioned_or(prefix, "")(bot,message) if not raw_prefix else (prefix, "")
            else:
                return commands.when_mentioned_or(self.PRE, "")(bot,message) if not raw_prefix else (self.PRE, "")
        
        prefix = prefix or self.PRE
        return commands.when_mentioned_or(prefix)(bot,message)
    
    
    # Event based 
    async def on_ready(self) -> None:
        logging.info("\033[42m======[ BOT ONLINE! ]=======")
        logging.info ("Logged in as " + self.user.name)
        logging.info('\033[0m')
        if not self.started:
            self.started = True
            await self.wait_until_ready()
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='db.help'))
            
    async def on_message(self, message: discord.Message) -> None:
        if any((self.maintenance == True, message.author.id != self.owner_id)):
            return
        
        if self.user:
            if message.content == f'<@!{self.user.id}>':  # Sets faster
                prefix = await self.get_pre(self, message, raw_prefix=True)
                return await message.reply(f"For a list of commands do `{prefix}help` 💞")
        
        await self.process_commands(message)

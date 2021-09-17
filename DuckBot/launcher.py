import logging
import os

# Async stuff seperate
import asyncpg
import asyncpraw
from discord.ext import commands
from dotenv import load_dotenv

# Local imports always at bottom
from main import DuckBot
import errors

os.environ['JISHAKU_HIDE'] = 'True'

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(message)s')


if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')

    bot = DuckBot()

    bot.run(TOKEN, reconnect=True)

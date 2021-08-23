import logging
import os

# Async stuff seperate
import asyncpg
from dotenv import load_dotenv

# Local imports always at bottom
from main import DuckBot

os.environ['JISHAKU_HIDE'] = 'True'

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(message)s')


async def create_db_pool() -> asyncpg.Pool:
    credentials = {
        "user": f"{os.getenv('PSQL_USER')}",
        "password": f"{os.getenv('PSQL_PASSWORD')}",
        "database": f"{os.getenv('PSQL_DB')}",
        "host": f"{os.getenv('PSQL_HOST')}"
    }

    return await asyncpg.create_pool(**credentials)


if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')

    bot = DuckBot()
    bot.db = bot.loop.run_until_complete(create_db_pool())
    bot.run(TOKEN, reconnect=True)

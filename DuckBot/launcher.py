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
    bot.reddit = asyncpraw.Reddit(client_id=os.getenv('ASYNC_PRAW_CID'),
                                  client_secret=os.getenv('ASYNC_PRAW_CS'),
                                  user_agent=os.getenv('ASYNC_PRAW_UA'),
                                  username=os.getenv('ASYNC_PRAW_UN'),
                                  password=os.getenv('ASYNC_PRAW_PA'))
    bot.db = bot.loop.run_until_complete(create_db_pool())

    @bot.check
    def blacklist(ctx: commands.Context):
        try:
            is_blacklisted = bot.blacklist[ctx.author.id]
        except KeyError:
            is_blacklisted = False
        if ctx.author.id == bot.owner_id:
            is_blacklisted = False

        if is_blacklisted is False:
            return True
        else:
            raise errors.UserBlacklisted

    bot.run(TOKEN, reconnect=True)

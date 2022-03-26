from __future__ import annotations

import logging
import os
import aiohttp
import asyncio

from bot import DuckBot
from dotenv import load_dotenv
from utils.helpers import col

load_dotenv()

os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'true'
os.environ['JISHAKU_RETAIN'] = 'true'


def _get_or_fail(env_var: str) -> str:
    val = os.environ.get(env_var)
    if not val:
        raise RuntimeError(f'{env_var!r} not set in .env file. Set it.')
    return val


TOKEN = _get_or_fail('TOKEN')
URI = _get_or_fail('POSTGRES')
ERROR_WEBHOOK_URL = _get_or_fail('ERROR_WEBHOOK_URL')

logging.basicConfig(
    level=logging.INFO,
    format=f'{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s'
)

log = logging.getLogger('DuckBot.launcher')

async def run_bot() -> None:
    pool = await DuckBot.setup_pool(uri=URI)
    duck = None
    try:
        async with aiohttp.ClientSession() as session:
            async with DuckBot(session=session, pool=pool, error_webhook_url=ERROR_WEBHOOK_URL) as duck:
                await duck.start(TOKEN, reconnect=True, verbose=False)
    except Exception as e:
        return log.error('Failed to start bot', exc_info=e)
    finally:
        if duck and not duck.is_closed():
            log.info('Closing the bot')
            await duck.close()
        
    
if __name__ == '__main__':
    asyncio.run(run_bot())

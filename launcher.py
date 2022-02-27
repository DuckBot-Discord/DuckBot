from __future__ import annotations

import logging
import os
import aiohttp
import asyncio
from dotenv import load_dotenv

from bot import DuckBot
from utils.helpers import col

load_dotenv()

TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    raise RuntimeError('No token found in .env')

URI = os.environ.get('POSTGRES')
if not URI:
    raise RuntimeError('No URI found in .env')

log = logging.getLogger('DuckBot.launcher')

async def run_bot() -> None:
    try:
        pool = await DuckBot.setup_pool(uri=URI)
    except Exception as e:
        log.error(f'Failed to setup pool', exc_info=e)
        return
    else:
        log.info(f'{col(2)}Database pool created successfully!')

    duck = None
    try:
        async with aiohttp.ClientSession() as session:
            duck = DuckBot(session=session, pool=pool)
            await duck.start(TOKEN, reconnect=True)
    except Exception as e:
        return log.error('Failed to start bot', exc_info=e)
    finally:
        if duck and not duck.is_closed():
            log.info('Closing the bot')
            await duck.close()
        
    
if __name__ == '__main__':
    asyncio.run(run_bot())

from __future__ import annotations

import os
import aiohttp
import asyncio
import traceback
from dotenv import load_dotenv

from bot import DuckBot

load_dotenv()

TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    raise RuntimeError('No token found in .env')

async def run_bot() -> None:
    try:
        pool = await DuckBot.setup_pool(uri='postgresql://duck:duck@localhost:5432/duck')
    except:
        traceback.print_exc()
        return

    duck = None
    try:
        async with aiohttp.ClientSession() as session:
            duck = DuckBot(session=session, pool=pool)
            await duck.start(TOKEN, reconnect=True)
    except Exception:
        return traceback.print_exc()
    finally:
        if duck and not duck.is_closed():
            await duck.close()
        
    
if __name__ == '__main__':
    asyncio.run(run_bot())
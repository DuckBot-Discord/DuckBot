from __future__ import annotations

import asyncio
import traceback
import aiohttp
from bot import DuckBot


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
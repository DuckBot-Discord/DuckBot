from __future__ import annotations

import os
import aiohttp
import asyncio

from bot import DuckBot
from dotenv import load_dotenv

load_dotenv('utils/.env')
# (jsk flags are now in the .env)


def _get_or_fail(env_var: str) -> str:
    val = os.environ.get(env_var)
    if not val:
        raise RuntimeError(f'{env_var!r} not set in .env file. Set it.')
    return val


TOKEN = _get_or_fail('TOKEN')
URI = _get_or_fail('POSTGRES')
ERROR_WH = _get_or_fail('ERROR_WEBHOOK_URL')


async def run_bot() -> None:
    async with aiohttp.ClientSession() as session, DuckBot.temporary_pool(uri=URI) as pool, DuckBot(session=session, pool=pool, error_wh=ERROR_WH) as duck:
        await duck.start(TOKEN, reconnect=True, verbose=False)


if __name__ == '__main__':
    asyncio.run(run_bot())

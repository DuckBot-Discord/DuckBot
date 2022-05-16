from __future__ import annotations

import logging
import os
import aiohttp
import asyncio

from bot import DuckBot
from dotenv import load_dotenv
from utils.helpers import col

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

logging.basicConfig(
    level=logging.INFO,
    format=f'{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s{col()}',
)

log = logging.getLogger('DuckBot.launcher')


async def run_bot(to_dump: str | None, to_load: str | None, run: bool) -> None:
    async with aiohttp.ClientSession() as session, DuckBot.temporary_pool(uri=URI) as pool, DuckBot(
        session=session, pool=pool, error_wh=ERROR_WH
    ) as duck:
        if to_dump:
            await duck.dump_translations(to_dump)
        elif to_load:
            await duck.load_translations(to_load)
        elif run:
            await duck.start(TOKEN, reconnect=True, verbose=False)


if __name__ == '__main__':
    asyncio.run(run_bot(to_dump=None, to_load=None, run=True))

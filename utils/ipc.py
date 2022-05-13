from logging import getLogger
from bot import DuckBot
from .ipc_routes import DuckBotIPC


log = getLogger('DuckBot.ipc')


async def setup(bot: DuckBot):
    bot.ipc = DuckBotIPC(bot)
    try:
        await bot.ipc.start(port=4435)
    except:
        log.info('failed to start IPC')
        raise
    else:
        log.info('Started IPC server.')


async def teardown(bot: DuckBot):
    log.info('Stopping IPC server.')
    try:
        await bot.ipc.close()  # type: ignore
    finally:
        bot.ipc = None

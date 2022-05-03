from bot import DuckBot
from .ipc_routes import DuckBotIPC


async def setup(bot: DuckBot):
    bot.ipc = DuckBotIPC(bot)
    await bot.ipc.start(port=4435)


async def teardown(bot: DuckBot):
    try:
        await bot.ipc.close()  # type: ignore
    finally:
        bot.ipc = None

from discord.ext import commands, tasks

from DuckBot.__main__ import DuckBot


class IpcBase(commands.Cog):

    def __init__(self, bot: DuckBot):
        self.bot = bot
        self.channel_count = 0
        self.counter.start()

    def cog_unload(self) -> None:
        self.counter.stop()

    @tasks.loop(seconds=10)
    async def counter(self) -> None:
        self.channel_count = len(list(self.bot.get_all_channels()))

    @counter.before_loop
    async def before_counter(self) -> None:
        await self.bot.wait_until_ready()

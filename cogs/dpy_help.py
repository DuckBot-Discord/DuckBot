from logging import getLogger
import os
import discord
from discord.ext import commands
from bot import DuckBot

logger = getLogger(__name__)
DISCORD_PY_HELP_FORUM = 985299059441025044
INTERNAL_ADDRESS = os.getenv("INTERNAL_ADDRESS")


class HelpWatcher(commands.Cog):
    def __init__(self, bot: DuckBot) -> None:
        super().__init__()
        self.bot = bot

    async def emit_warning(self, user_id: int, thread_id: int, owner_id: int):
        """Emits a warning to the webserver that the GlobalNotes bot is running.

        https://github.com/DuckBot-Discord/GlobalNotes
        """
        payload = {
            'user_id': user_id,
            'thread_id': thread_id,
            'owner_id': owner_id,
        }
        async with self.bot.session.post(
            f'{INTERNAL_ADDRESS}/inhelp',
            json=payload,
        ) as resp:
            logger.debug("payload %s response %s", payload, await resp.read())

    @commands.Cog.listener()
    async def on_typing(
        self,
        channel: discord.abc.MessageableChannel,
        user: discord.abc.User,
        when: ...,
    ):
        if isinstance(channel, discord.Thread) and channel.parent_id == DISCORD_PY_HELP_FORUM:
            await self.emit_warning(user_id=user.id, thread_id=channel.id, owner_id=channel.owner_id)

    @commands.Cog.listener()
    async def on_thread_member_join(
        self,
        member: discord.ThreadMember,
    ):

        if isinstance(member.thread, discord.Thread) and member.thread.parent_id == DISCORD_PY_HELP_FORUM:
            await self.emit_warning(user_id=member.id, thread_id=member.thread_id, owner_id=member.thread.owner_id)

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ):
        if isinstance(message.channel, discord.Thread) and message.channel.parent_id == DISCORD_PY_HELP_FORUM:
            await self.emit_warning(
                user_id=message.author.id,
                thread_id=message.channel.id,
                owner_id=message.channel.owner_id,
            )


async def setup(bot: DuckBot):
    if INTERNAL_ADDRESS:
        await bot.add_cog(HelpWatcher(bot))

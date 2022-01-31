import discord
from discord.ext import commands

from DuckBot.helpers import constants
from ._base import EventsBase


class SuggestionChannels(EventsBase):

    @commands.Cog.listener('on_message')
    async def on_suggestion_receive(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.bot.suggestion_channels:
            return
        if self.bot.suggestion_channels[message.channel.id] is True and not message.attachments and \
                not message.channel.permissions_for(message.author).manage_messages:
            await message.delete(delay=0)
            return await message.channel.send(
                f'⚠ | {message.author.mention} this **suggestions channel** is set to **image-only** mode!',
                delete_after=5)

        await message.add_reaction(constants.UPVOTE)
        await message.add_reaction(constants.DOWNVOTE)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if channel.id in self.bot.suggestion_channels:
            await self.bot.db.execute('DELETE FROM suggestions WHERE channel_id = $1', channel.id)


import random

import discord
from discord.ext import commands
from typing import List

from DuckBot.__main__ import DuckBot, CustomContext


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    @commands.command(name='enable-suggestions', aliases=['enable_suggestions'])
    async def enable_suggestions(self, ctx: CustomContext,
                                 channel: discord.TextChannel,
                                 image_only: bool):
        self.bot.suggestion_channels[channel.id] = image_only
        await self.bot.db.execute('INSERT INTO suggestions (channel_id, image_only) VALUES ($1, $2) ON CONFLICT '
                                  '(channel_id) DO UPDATE SET image_only = $2', channel.id, image_only)
        await ctx.send(f'💞 | **Enabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **{"disabled" if image_only is False else "enabled"}**.')

    @commands.command(name='disable-suggestions', aliases=['disable_suggestions'])
    async def disable_suggestions(self, ctx: CustomContext,
                                  channel: discord.TextChannel):
        try:
            self.bot.suggestion_channels.pop(channel.id)
        except KeyError:
            pass
        await self.bot.db.execute('DELETE FROM suggestions WHERE channel_id = $1', channel.id)
        await ctx.send(f'💞 | **Disabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **N/A**.')

    @commands.Cog.listener('on_message')
    async def on_suggestion_receive(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.bot.suggestion_channels:
            return
        if self.bot.suggestion_channels[message.channel.id] is True and not message.attachments and not message.channel.permissions_for(message.author).manage_messages:
            await message.delete(delay=0)
            return await message.channel.send(f'⚠ | {message.author.mention} this **suggestions channel** is set to **image-only** mode!', delete_after=5)

        await message.add_reaction('<:upvote:893588750242832424>')
        await message.add_reaction('<:downvote:893588792164892692>')

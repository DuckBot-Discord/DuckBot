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

    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, add_reactions=True)
    @commands.command(name='enable-suggestions', aliases=['enable_suggestions'])
    async def enable_suggestions(self, ctx: CustomContext,
                                 channel: discord.TextChannel,
                                 image_only: bool):
        self.bot.suggestion_channels[channel.id] = image_only
        await self.bot.db.execute('INSERT INTO suggestions (channel_id, image_only) VALUES ($1, $2) ON CONFLICT '
                                  '(channel_id) DO UPDATE SET image_only = $2', channel.id, image_only)
        await ctx.send(f'💞 | **Enabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **{"disabled" if image_only is False else "enabled"}**.')

    @commands.has_permissions(manage_channels=True)
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

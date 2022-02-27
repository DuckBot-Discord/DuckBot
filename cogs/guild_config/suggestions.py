import discord
from discord.ext import commands

from DuckBot.__main__ import CustomContext
from ._base import ConfigBase


class Suggestions(ConfigBase):

    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, add_reactions=True)
    @commands.command(name='enable-suggestions', aliases=['enable_suggestions'])
    async def enable_suggestions(self, ctx: CustomContext,
                                 channel: discord.TextChannel,
                                 image_only: bool):
        """
        Enables "Suggestion mode" - which is, the bot will react with an upvote and downvote reaction, for people to vote.
        _It is recommended to use the `%PRE%slowmode <short_time>` command to accompany this one, as to not flood the channel with reactions.
        **Note:** If image-only is set to `yes`, the bot will delete all messages without attachments, and warn the user.
        """
        self.bot.suggestion_channels[channel.id] = image_only
        await self.bot.db.execute('INSERT INTO suggestions (channel_id, image_only) VALUES ($1, $2) ON CONFLICT '
                                  '(channel_id) DO UPDATE SET image_only = $2', channel.id, image_only)
        await ctx.send(f'💞 | **Enabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **{"disabled" if image_only is False else "enabled"}**.')

    @commands.has_permissions(manage_channels=True)
    @commands.command(name='disable-suggestions', aliases=['disable_suggestions'])
    async def disable_suggestions(self, ctx: CustomContext,
                                  channel: discord.TextChannel):
        """
        Disables "suggestion mode" for a channel.
        """
        try:
            self.bot.suggestion_channels.pop(channel.id)
        except KeyError:
            pass
        await self.bot.db.execute('DELETE FROM suggestions WHERE channel_id = $1', channel.id)
        await ctx.send(f'💞 | **Disabled** suggestions mode for {channel.mention}'
                       f'\n📸 | With image-only mode **N/A**.')

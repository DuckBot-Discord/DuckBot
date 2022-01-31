import asyncio
from collections import namedtuple

import discord
import typing
from discord.ext import commands, tasks

from DuckBot.__main__ import DuckBot

from ._base import LoggingBase


class MessageLogs(LoggingBase):

    @commands.Cog.listener('on_message_delete')
    async def logger_on_message_delete(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild or message.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[message.guild.id].message_delete:
            return
        if message.guild.id in self.bot.log_channels:
            embed = discord.Embed(title=f'Message deleted in #{message.channel}',
                                  description=(message.content or '\u200b')[0:4000],
                                  colour=discord.Colour.red(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"Channel: {message.channel.id}")
            if message.attachments:
                embed.add_field(name='Attachments:', value='\n'.join([a.filename for a in message.attachments]), inline=False)
            if message.stickers:
                embed.add_field(name='Stickers:', value='\n'.join([a.name for a in message.stickers]), inline=False)
            self.log(embed, guild=message.guild, send_to=self.send_to.message)

    @commands.Cog.listener('on_raw_bulk_message_delete')
    async def logger_on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if not payload.guild_id or payload.guild_id not in self.bot.log_channels or not self.bot.guild_loggings[payload.guild_id].message_purge:
            return
        embed = discord.Embed(title=f'{len(payload.message_ids)} messages purged in #{self.bot.get_channel(payload.channel_id)}',
                              colour=discord.Colour.red(), timestamp=discord.utils.utcnow())
        msgs = []
        for message in payload.cached_messages:
            if message.author.bot:
                continue
            if message.attachments:
                attachment = f'{len(message.attachments)} attachments: ' + message.attachments[0].filename
            elif message.stickers:
                attachment = 'Sticker: ' + message.stickers[0].name
            else:
                attachment = None
            message = f"{discord.utils.remove_markdown(str(message.author))} > {message.content or attachment or '-'}"
            if len(message) > 200:
                message = message[0:200] + '...'
            msgs.append(message)
            if len('\n'.join(msgs)[0:4096]) > 4000:
                break
        embed.description = '\n'.join(msgs)[0:4000]
        embed.add_field(name='Showing: ', value=f"{len(msgs)}/{len(payload.message_ids)} messages.", inline=False)
        embed.set_footer(text=f'Channel: {payload.channel_id}')
        self.log(embed, guild=payload.guild_id, send_to=self.send_to.message)

    @commands.Cog.listener('on_message_edit')
    async def logger_on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[after.guild.id].message_edit:
            return
        if not self.bot.guild_loggings[before.guild.id].message_edit:
            return
        if before.guild.id in self.bot.log_channels:
            if before.content == after.content and before.attachments == after.attachments and before.stickers == after.stickers:
                return
            embed = discord.Embed(title=f'Message edited in #{before.channel}',
                                  colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
            embed.set_footer(text=f"Channel: {before.channel.id}")

            embed.add_field(name='**__Before:__**', value=before.content[0:1024], inline=False)
            embed.add_field(name='**__After:__**', value=after.content[0:1024], inline=False)
            if before.attachments and before.attachments != after.attachments:
                af = after.attachments
                attachments = []
                for a in before.attachments:
                    if a in af:
                        attachments.append(a.filename)
                    else:
                        attachments.append(f"[Removed] ~~{a.filename}~~")
                embed.add_field(name='Attachments:', value='\n'.join(attachments), inline=False)
            embed.add_field(name='Jump:', value=f'[[Jump to message]]({after.jump_url})', inline=False)
            self.log(embed, guild=before.guild, send_to=self.send_to.message)

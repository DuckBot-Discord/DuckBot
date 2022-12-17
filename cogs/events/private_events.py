import re

import discord
from discord.ext import commands

from ._base import EventsBase


class PrivateEvents(EventsBase):
    @commands.Cog.listener('on_message')
    async def emoji_sender(self, message: discord.Message):
        if not await self.bot.is_owner(message.author) or self.bot.user.id != 788278464474120202:
            return
        ic = '\u200b'
        content = message.content
        emojis = re.findall(r';(?P<name>[a-zA-Z0-9]{1,32}?);', message.content)
        for em_name in emojis:
            emoji = discord.utils.find(lambda em: em.name.lower() == em_name.lower(), self.bot.emojis)
            if not emoji or not emoji.is_usable():
                emoji = None
            content = content.replace(f';{em_name};', f'{str(emoji or f";{ic}{em_name}{ic};")}', 1)
        if content.replace(ic, '') != message.content:
            await message.channel.send(content)

    @commands.Cog.listener('on_guild_join')
    async def server_join_message(self, guild: discord.Guild):
        channel = self.bot.get_channel(904797860841812050)
        embed = discord.Embed(
            title='Joined Server',
            colour=discord.Colour.green(),
            timestamp=discord.utils.utcnow(),
            description=f'**Name:** {discord.utils.escape_markdown(guild.name)} • {guild.id}'
            f'\n**Owner:** {guild.owner} • {guild.owner_id}',
        )
        embed.add_field(
            name='Members',
            value=f'👥 {len([m for m in guild.members if not m.bot])} • 🤖 {len([m for m in guild.members if m.bot])}\n**Total:** {guild.member_count}',
        )
        await channel.send(embed=embed)

    @commands.Cog.listener('on_guild_remove')
    async def server_leave_message(self, guild: discord.Guild):
        channel = self.bot.get_channel(904797860841812050)
        embed = discord.Embed(
            title='Left Server',
            colour=discord.Colour.red(),
            timestamp=discord.utils.utcnow(),
            description=f'**Name:** {discord.utils.escape_markdown(guild.name)} • {guild.id}'
            f'\n**Owner:** {guild.owner} • {guild.owner_id}',
        )
        embed.add_field(
            name='Members',
            value=f'👥 {len([m for m in guild.members if not m.bot])} • 🤖 {len([m for m in guild.members if m.bot])}\n**Total:** {guild.member_count}',
        )
        await channel.send(embed=embed)

    @commands.Cog.listener('on_message')
    async def nsfw_protector(self, message: discord.Message):
        if self.bot.user.id != 788278464474120202:
            return
        if message.channel.id != 939677888809140294 or message.author.bot:
            return
        if not all([a.is_spoiler() for a in message.attachments]):
            await message.reply(
                'Please mark **all** your images as spoiler.',
                allowed_mentions=discord.AllowedMentions.all(),
                delete_after=10,
            )
            await message.delete()

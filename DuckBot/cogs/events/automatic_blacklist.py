import logging

import discord
from discord.ext import commands

from DuckBot.__main__ import CustomContext
from ._base import EventsBase


class AutoBlacklist(EventsBase):

    @commands.Cog.listener('on_command')
    async def on_command(self, ctx: CustomContext):
        await self.bot.db.execute(
            "INSERT INTO commands (guild_id, user_id, command, timestamp) VALUES ($1, $2, $3, $4)",
            getattr(ctx.guild, 'id', None), ctx.author.id, ctx.command.qualified_name, ctx.message.created_at)

        bucket = self.bot.global_mapping.get_bucket(ctx.message)
        current = ctx.message.created_at.timestamp()
        retry_after = bucket.update_rate_limit(current)
        author_id = ctx.author.id
        if retry_after and author_id != self.bot.owner_id:
            self._auto_spam_count[author_id] += 1
            if self._auto_spam_count[author_id] >= 5:
                await self.add_to_blacklist(author_id)
                del self._auto_spam_count[author_id]
                await self.log_rl_excess(ctx, ctx.message, retry_after, auto_block=True)
            else:
                await self.log_rl_excess(ctx, ctx.message, retry_after)
            return
        else:
            self._auto_spam_count.pop(author_id, None)

    async def log_rl_excess(self, ctx, message, retry_after, *, auto_block=False):
        guild_name = getattr(ctx.guild, 'name', 'No Guild (DMs)')
        guild_id = getattr(ctx.guild, 'id', None)
        fmt = 'User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs'
        logging.warning(fmt, message.author, message.author.id, guild_name, guild_id, retry_after)
        if not auto_block:
            return

        await self.bot.wait_until_ready()
        embed = discord.Embed(title='Auto-blocked Member', colour=0xDDA453)
        embed.add_field(name='Member', value=f'{message.author} (ID: {message.author.id})', inline=False)
        embed.add_field(name='Guild Info', value=f'{guild_name} (ID: {guild_id})', inline=False)
        embed.add_field(name='Channel Info', value=f'{message.channel} (ID: {message.channel.id}', inline=False)
        embed.timestamp = discord.utils.utcnow()
        channel = self.bot.get_channel(904797860841812050)
        await channel.send(embed=embed)

    async def add_to_blacklist(self, user_id, reason: str = 'spamming commands (automatic action).'
                                                            '\nJoin the support server if at my bio to appeal'):
        self.bot.blacklist[user_id] = True
        await self.bot.db.execute(
            "INSERT INTO blacklist(user_id, is_blacklisted, reason) VALUES ($1, $2, $3) "
            "ON CONFLICT (user_id) DO UPDATE SET is_blacklisted = $2, reason = $3",
            user_id, True, reason)

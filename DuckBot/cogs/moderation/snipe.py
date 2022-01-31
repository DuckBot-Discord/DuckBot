import asyncio

import discord
from discord.ext import commands


from ._base import ModerationBase
from ...helpers.context import CustomContext
from ...helpers.time_inputs import human_timedelta


def require_snipe(should_be: bool = True):
    async def predicate(ctx: CustomContext) -> bool:
        snipe = await ctx.bot.db.fetchval('SELECT snipe_enabled FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if bool(snipe) is should_be:
            return True
        else:
            raise commands.BadArgument(f'Snipe is {"not" if should_be is True else ""} enabled on this server.')
    return commands.check(predicate)  # type: ignore


class SimpleAuthor:
    """ A more memory efficient slotted class to store the
    author information of a message. """
    __slots__ = ('id', 'name', 'discriminator', 'avatar_url')

    def __init__(self, member: discord.Member):
        self.name = member.name
        self.discriminator = member.discriminator
        self.avatar_url = member.display_avatar.url

    def __str__(self) -> str:
        return f"{self.name}#{self.discriminator}"


class SimpleMessage:
    """ A more memory efficient and non-slotted class to store
     only the information I need for the snipe command. """
    __slots__ = ('content', 'author', 'embeds', 'timestamp', 'components')

    def __init__(self, message: discord.Message):
        if message.content:
            self.content = message.content
        elif message.attachments:
            self.content = '**Attachments:** ' + ', '.join(a.filename for a in message.attachments)
        elif message.stickers:
            self.content = '**Stickers:** ' + ', '.join(s.name for s in message.stickers)
        else:
            self.content = None
        self.author = SimpleAuthor(message.author)
        self.embeds = message.embeds
        self.timestamp = message.created_at
        self.components = message.components


class Snipe(ModerationBase):
    snipe_checks = (commands.is_owner(), commands.has_permissions(manage_guild=True))

    @require_snipe()
    @commands.group(name='snipe', invoke_without_command=True)
    async def snipe(self, ctx: CustomContext, index: int = 1):
        try:
            message = self.bot.snipes[ctx.channel.id][-index]
            embed = discord.Embed(description=message.content or '_No content in message_',
                                  timestamp=message.timestamp, colour=ctx.color)
            embed.set_author(name=f'{message.author} said in #{ctx.channel}', icon_url=message.author.avatar_url)
            embed.set_footer(text=f'Message sent {human_timedelta(message.timestamp)}, '
                                  f'Index {index}/{len(self.bot.snipes[ctx.channel.id])}')
            view = None
            if message.components:
                view = discord.ui.View.from_message(message, timeout=0)
                for child in view.children:
                    child.disabled = True
            await ctx.send(embeds=[embed] + message.embeds, view=view)
        except (KeyError, IndexError):
            raise commands.BadArgument(f'No message found at index {index}')

    @require_snipe(False)
    @commands.check_any(*snipe_checks)
    @snipe.command(name='enable')
    async def snipe_enable(self, ctx):
        await self.bot.db.execute('INSERT INTO prefixes (guild_id, snipe_enabled) VALUES ($1, TRUE) ON CONFLICT (guild_id) DO UPDATE SET snipe_enabled = TRUE', ctx.guild.id)
        await ctx.send('✅ **snipe** has been enabled!')

    @require_snipe()
    @commands.check_any(*snipe_checks)
    @snipe.command(name='disable')
    async def snipe_disable(self, ctx):
        await self.bot.db.execute("UPDATE prefixes SET snipe_enabled = FALSE WHERE guild_id = $1", ctx.guild.id)
        await ctx.send('❌ **snipe** has been disabled!')
        await self.snipe_guild_remove(ctx.guild)

    @commands.Cog.listener('on_message_delete')
    async def snipe_hook(self, message: discord.Message):
        if await self.bot.db.fetchval('SELECT snipe_enabled FROM prefixes WHERE guild_id = $1', message.guild.id):
            self.bot.snipes[message.channel.id].append(SimpleMessage(message))

    @commands.Cog.listener('on_guild_channel_delete')
    async def snipe_channel_delete(self, channel: discord.TextChannel):
        if channel.id in self.bot.snipes:
            del self.bot.snipes[channel.id]

    @commands.Cog.listener('on_guild_remove')
    async def snipe_guild_remove_listener(self, guild: discord.Guild):
        await self.snipe_guild_remove(guild)

    async def snipe_guild_remove(self, guild: discord.Guild):
        for channel in guild.text_channels:
            if channel.id in self.bot.snipes:
                del self.bot.snipes[channel.id]

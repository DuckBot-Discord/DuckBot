import contextlib

import discord
from discord.ext import commands
from jishaku.paginators import WrappedPaginator

from DuckBot.helpers import time_inputs
from ._base import EventsBase


class AfkHandler(EventsBase):

    @commands.Cog.listener('on_message')
    async def on_afk_user_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if message.author.id in self.bot.afk_users:
            try:
                if self.bot.auto_un_afk[message.author.id] is False:
                    return
            except KeyError:
                pass

            self.bot.afk_users.pop(message.author.id)

            info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', message.author.id)
            await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, null, null) '
                                      'ON CONFLICT (user_id) DO UPDATE SET start_time = null, reason = null',
                                      message.author.id)

            await message.channel.send(
                f'**Welcome back, {message.author.mention}, afk since: {discord.utils.format_dt(info["start_time"], "R")}**'
                f'\n**With reason:** {info["reason"]}', delete_after=10)

            await message.add_reaction('👋')

    @commands.Cog.listener('on_message')
    async def on_afk_user_mention(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if message.mentions:
            pinged_afk_user_ids = list(set([u.id for u in message.mentions]).intersection(self.bot.afk_users))
            paginator = WrappedPaginator(prefix='', suffix='')
            for user_id in pinged_afk_user_ids:
                member = message.guild.get_member(user_id)
                if member and member.id != message.author.id:
                    info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', user_id)
                    paginator.add_line(
                        f'**woah there, {message.author.mention}, it seems like {member.mention} has been afk '
                        f'for {time_inputs.human_timedelta(info["start_time"], accuracy=3, brief=True)}!**'
                        f'\n**With reason:** {info["reason"]}\n')

            if paginator.pages:
                with contextlib.suppress(discord.HTTPException):
                    await message.add_reaction('‼')

            for page in paginator.pages:
                await message.reply(page, allowed_mentions=discord.AllowedMentions(replied_user=True,
                                                                                   users=False,
                                                                                   roles=False,
                                                                                   everyone=False),
                                    delete_after=30)

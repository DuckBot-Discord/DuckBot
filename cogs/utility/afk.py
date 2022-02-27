import discord
from discord.ext import commands

from DuckBot.__main__ import CustomContext
from DuckBot.helpers import constants
from ._base import UtilityBase


class Afk(UtilityBase):

    @commands.command()
    async def afk(self, ctx: CustomContext, *, reason: commands.clean_content = '...'):
        if ctx.author.id in self.bot.afk_users and ctx.author.id in self.bot.auto_un_afk and self.bot.auto_un_afk[ctx.author.id] is True:
            return
        if ctx.author.id not in self.bot.afk_users:
            await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, $2, $3) '
                                      'ON CONFLICT (user_id) DO UPDATE SET start_time = $2, reason = $3',
                                      ctx.author.id, ctx.message.created_at, reason[0:1800])
            self.bot.afk_users[ctx.author.id] = True
            await ctx.send(f'**You are now afk!** {constants.ROO_SLEEP}'
                           f'\n**with reason:** {reason}')
        else:
            self.bot.afk_users.pop(ctx.author.id)

            info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', ctx.author.id)
            await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, null, null) '
                                      'ON CONFLICT (user_id) DO UPDATE SET start_time = null, reason = null',
                                      ctx.author.id)

            await ctx.channel.send(
                f'**Welcome back, {ctx.author.mention}, afk since: {discord.utils.format_dt(info["start_time"], "R")}**'
                f'\n**With reason:** {info["reason"]}', delete_after=10)

            await ctx.message.add_reaction('👋')

    @commands.command(name='auto-afk-remove', aliases=['autoafk', 'aafk'])
    async def auto_un_afk(self, ctx: CustomContext, mode: bool = None):
        """
        Toggles weather to remove the AFK status automatically or not.
        mode: either enabled or disabled. If none, it will toggle it.
        """
        mode = mode or (False if (ctx.author.id in self.bot.auto_un_afk and self.bot.auto_un_afk[
            ctx.author.id] is True) or ctx.author.id not in self.bot.auto_un_afk else True)
        self.bot.auto_un_afk[ctx.author.id] = mode
        await self.bot.db.execute('INSERT INTO afk (user_id, auto_un_afk) VALUES ($1, $2) '
                                  'ON CONFLICT (user_id) DO UPDATE SET auto_un_afk = $2', ctx.author.id, mode)
        return await ctx.send(f'{"Enabled" if mode is True else "Disabled"} automatic AFK removal.'
                              f'\n{"**Remove your AFK status by running the `afk` command while being AFK**" if mode is False else ""}')

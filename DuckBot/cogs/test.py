import discord
from discord.ext import commands

from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers.helper import generate_youtube_bar


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    @commands.command()
    async def bar(self, ctx: CustomContext, position: int, duration: int, length: int):
        await ctx.send(generate_youtube_bar(position, duration, length))

    @commands.command()
    async def afk(self, ctx: CustomContext, reason: commands.clean_content = '...'):
        await self.bot.db.execute('INSERT INTO afk (user_id, start_time, reason) VALUES ($1, $2, $3) '
                                  'ON CONFLICT (user_id) DO UPDATE SET start_time = $2, reason = $3',
                                  ctx.author.id, ctx.message.created_at, reason[0:1800])
        self.bot.afk_users[ctx.author.id] = True
        await ctx.send('**You are now afk!** <:RooSleep:892425348078256138>'
                       f'\n**with reason:** {reason}')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id not in self.bot.afk_users:
            return
        self.bot.afk_users.pop(message.author.id)
        info = await self.bot.db.fetchrow('SELECT * FROM afk WHERE user_id = $1', message.author.id)
        await self.bot.db.execute('DELETE FROM afk WHERE user_id = $1', message.author.id)
        await message.channel.send(f'**Welcome back, {message.author.mention}, afk since: {discord.utils.format_dt(info["start_time"], "R")}**'
                                   f'\n**With reason:** {info["reason"]}')

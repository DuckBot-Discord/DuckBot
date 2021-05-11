import typing, discord, asyncio
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def afk(self, ctx):
        nick = f'{ctx.author.nick}'
        if nick == 'None':
            nick = f'{ctx.author.name}'
        else:
            nick = nick
        if nick.startswith("[AFK] "):
            try:
                await ctx.author.edit(nick=nick.replace('[AFK] ', ''))
                await ctx.send(f'{ctx.author.mention}, **You are no longer afk**', delete_after=15)
            except discord.Forbidden:
                await ctx.message.add_reaction('⚠')
                return
            await ctx.message.delete()
        else:
            try:
                await ctx.author.edit(nick=f'[AFK] {nick}')
            except discord.Forbidden:
                await ctx.message.add_reaction('⚠')
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('⚠')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
                return
            await ctx.send(f'{ctx.author.mention}, **You are afk**', delete_after=15)
            await ctx.message.delete()

def setup(bot):
    bot.add_cog(help(bot))

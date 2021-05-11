import typing, discord, asyncio
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

class afk(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def afk(self, ctx):
        nick = f'{ctx.author.nick}'
        if nick == 'None':
            nick = f'{ctx.author.name}'
        else:
            nick = nick
        if nick.startswith("[AFK] "):
            try:
                await ctx.author.edit(nick=nick.replace('[AFK] ', ''))
                await ctx.send(f'{ctx.author.mention}, **You are no longer afk**', delete_after=4)
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
            await ctx.send(f'{ctx.author.mention}, **You are afk**', delete_after=4)
            await ctx.message.delete()

    @afk.error
    async def afk_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            err = f'{error}'
            await ctx.send(err.replace("discord.ext.commands.errors.CommandOnCooldown:", " "), delete_after=5)
            await asyncio.sleep (5)
            await ctx.message.delete()

def setup(bot):
    bot.add_cog(afk(bot))

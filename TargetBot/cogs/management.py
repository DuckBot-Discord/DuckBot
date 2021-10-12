import os, discord, asyncio, traceback, json, typing
from dotenv import load_dotenv
from discord.ext import commands

class management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=['setstatus', 'ss', 'activity'], invoke_without_subcommand=True)
    @commands.is_owner()
    async def status(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @status.command(name='playing')
    async def status_playing(self, ctx: commands.Context, text):
        await self.bot.change_presence(activity=discord.Game(name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Playing {text}` ")

    @status.command(name='listening')
    async def status_listening(self, ctx: commands.Context, text):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Listening to {text}` ")

    @status.command(name='watching')
    async def status_watching(self, ctx: commands.Context, text):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Watching {text}` ")

    @status.command(name='competing')
    async def status_competing(self, ctx: commands.Context, text):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.competing, name=f'{text}'))
        await ctx.message.add_reaction('✅')
        await ctx.send(f"Activity changed to `Competing in {text}`")

    @commands.command(aliases=['mm'], help="puts the bot under maintenance", usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def maintenance(self, ctx, *, reason: str = None):
        if reason:
            await ctx.message.add_reaction(ctx.toggle(True))
            self.bot.maintenance = reason
        else:
            await ctx.message.add_reaction(ctx.toggle(False))
            self.bot.maintenance = None

def setup(bot):
    bot.add_cog(management(bot))

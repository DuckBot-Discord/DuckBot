import discord, asyncio, typing, aiohttp, random, json, yaml, re, psutil, pkg_resources, time, datetime
from discord.ext import commands, menus
from errors import HigherRole
from jishaku.models import copy_context_with
import contextlib


class test(commands.Cog):
    """🧪 Test commands. 💀 May not work"""
    def __init__(self, bot):
        self.bot = bot

    def get_bot_uptime(self):
        return f"<t:{round(self.bot.uptime.timestamp())}:R>"


    @commands.command(name="raise", help="Testing handling custom errors")
    async def _raise(self, ctx):
        raise HigherRole()

    @commands.command(help="Another error handling test")
    async def test(self, ctx):
        await ctx.send(f"{ctx.author} hi")

    @commands.command()
    async def about(self, ctx):
        """Tells you information about the bot itself."""

        embed = discord.Embed(description='about-me')
        embed.colour = discord.Colour.blurple()

        # statistics
        total_members = 0
        total_unique = len(self.bot.users)

        text = 0
        voice = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1
        l = [(sum(m.bot for m in g.members) / g.member_count)*100 for g in self.bot.guilds]

        embed.add_field(name='Members', value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='Channels', value=f'{text + voice} total\n{text} text\n{voice} voice')

        memory_usage = psutil.Process().memory_full_info().uss / 1024**2
        cpu_usage = psutil.Process().cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')

        version = pkg_resources.get_distribution('discord.py').version
        embed.add_field(name='Bot servers', value=f"**total servers:** {guilds}\n**average server bot%:** {round(sum(l) / len(l), 2)}%")
        embed.add_field(name='Last boot', value=self.get_bot_uptime())
        embed.set_footer(text=f'Made with discord.py v{version}', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(test(bot))

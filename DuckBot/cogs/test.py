import discord
import random
from discord.ext import commands


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """🧪 Test commands. 💀 May not work or not be what you think they'll be."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows you information about the server")
    @commands.is_owner()
    async def si(self, ctx):
        server = ctx.guild
        if ctx.me.guild_permissions.ban_members:
            bans = len(await server.bans())
        else:
            bans = None
        embed = discord.Embed(title=f"Server info - {server}", description=f"""
Name: {server}
<:greyTick:860644729933791283> ID: {server.id}
<:members:658538493470965787> Members: {len(server.members)} (:robot: {len([m for m in server.members if not m.bot])})
:robot: Bots: {len([m for m in server.members if not m.bot])}
<:owner_crown:845946530452209734> Owner: {server.owner}
Created: {discord.utils.format_dt(server.created_at, style="f")} ({discord.utils.format_dt(server.created_at, style='R')})
Region: {server.region}
<:members:858326990725709854> Max members: {server.max_members}
<:bans:878324391958679592> Banned members: {bans or "missing permissions"}
<:status_offline:596576752013279242> Statuses: <:status_online:596576749790429200> 4151 <:status_idle:596576773488115722> 3213 <:status_dnd:596576774364856321> 3307 <:status_streaming:596576747294818305> 0 <:status_offline:596576752013279242> 27186
<:text_channel:876503902554578984> Channels: <:text_channel:876503902554578984> {len(server.text_channels)} <:voice_channel:876503909512933396> {len(server.voice_channels)}
:sunglasses: Animated emojis: {len([x for x in server.emojis if x.animated])}/{server.emoji_limit}
:sunglasses: Non animated emojis: {len([x for x in server.emojis if not x.animated])}/{server.emoji_limit}
<:boost:858326699234164756> Level: {server.premium_tier}
<:boost:858326699234164756> Boosts: {server.premium_subscription_count}
        """)
        await ctx.send(embed=embed)


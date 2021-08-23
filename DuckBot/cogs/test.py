import discord, asyncio, typing, aiohttp, random, json, yaml, re, psutil, pkg_resources, time, datetime
from discord.ext import commands, menus
from jishaku.models import copy_context_with
import contextlib
import wavelink

class Music(commands.Cog):
    """Music cog to hold Wavelink related commands and listeners."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await wavelink.NodePool.create_node(bot=self.bot,
                                            host='wave.link',
                                            port=80,
                                            password='password',
                                            https=False,
                                            identifier='main')

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        print(f'Node: <{node.identifier}> is ready!')

    @commands.command()
    async def play(self, ctx: commands.Context, *, search: wavelink.YouTubeTrack):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if not ctx.voice_client:
            vc: Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: Player = ctx.voice_client

        await vc.play(search)

################################################################################################
################################################################################################
################################################################################################
################################################################################################

class test(commands.Cog):
    """🧪 Test commands. 💀 May not work or not be what you think they'll be."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows you information about the server")
    @commands.is_owner()
    async def si(self, ctx):
        server = ctx.guild
        if ctx.me.guild_permissions.ban_members: bans = len(await server.bans())
        else: bans = None
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

    @commands.command()
    async def banana(self, ctx, member: discord.Member=None):
        member = member or ctx.author
        size = random.uniform(8, 25)
        embed = discord.Embed(color = 0xFFCD71)
        embed.description = f"""
                             8{'=' * int(round(size/2, 0))}D

                             **{member.name}**'s 🍌 is {round(size, 1)} cm
                             """
        embed.set_author(icon_url=member.avatar.url, name=member)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(test(bot))
    bot.add_cog(Music(bot))

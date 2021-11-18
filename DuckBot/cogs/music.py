"""
A spin-off of DaPanda's Music Cog with some extra stuff added
like `search`, `search-next`, `search-now`, etc.
https://github.com/MiroslavRosenov/DaPanda
"""

import datetime
import asyncio
import logging
import math
import typing

import discord
import pomice
import re
import time as t

from discord import Interaction

from DuckBot.__main__ import DuckBot
from DuckBot.errors import *
import jishaku.paginators
from openrobot import api_wrapper as openrobot
from DuckBot.helpers.music.player import QueuePlayer as Player
from async_timeout import timeout
from discord.ext import commands
from DuckBot.helpers import paginator, helper
from DuckBot.helpers.context import CustomContext as Context, CustomContext
from DuckBot.helpers.helper import convert_bytes
from typing import Union

URL_RX = re.compile(r'https?://(?:www\.)?.+')
HH_MM_SS_RE = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{1,2}):(?P<s>\d{1,2})")
MM_SS_RE = re.compile(r"(?P<m>\d{1,2}):(?P<s>\d{1,2})")
HUMAN_RE = re.compile(r"(?:(?P<m>\d+)\s*m\s*)?(?P<s>\d+)\s*[sm]")
OFFSET_RE = re.compile(r"(?P<s>[-+]\d+)\s*s", re.IGNORECASE)


def setup(bot):
    bot.add_cog(Music(bot))


def format_time(milliseconds: Union[float, int]) -> str:
    hours, rem = divmod(int(milliseconds // 1000), 3600)
    minutes, seconds = divmod(rem, 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class MemberMention(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        m = re.search(r"^<@!?(?P<id>[0-9]+)>$", argument)
        if m is None:
            raise commands.BadArgument('You must mention a member!')
        data = m.groupdict()
        user_id = data.get('id')
        return await commands.MemberConverter().convert(ctx, user_id)


class SearchDropdown(discord.ui.Select['SearchMenu']):
    def __init__(self, options):
        super().__init__(placeholder='Select a track', options=options)

    async def callback(self, interaction: Interaction):
        resp: discord.InteractionResponse = interaction.response
        if self.values[0] == 'cancel':
            await self.view.on_timeout('Cancelled!')
            return self.view.stop()
        track = discord.utils.get(self.view.tracks, identifier=self.values[0])
        if not track:
            return await resp.send_message('Something went wrong, please try to select again.', ephemeral=True)
        self.view.track = track
        await interaction.message.delete()
        return self.view.stop()


class SearchMenu(discord.ui.View):
    def __init__(self, ctx: CustomContext, *, tracks: typing.List[pomice.Track]):
        super().__init__()
        self.ctx = ctx
        self.tracks = tracks[0:24]
        self.message: discord.Message = None
        self.track: typing.Optional[pomice.Track] = None
        self.embed: discord.Embed = None
        self.options: typing.List[discord.SelectOption] = []
        self.build_embed()
        self.add_item(SearchDropdown(self.options))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message('This is not your Play Menu!', ephemeral=True)

    async def on_timeout(self, label: str = None) -> None:
        for child in self.children:
            child.disabled = True
            if isinstance(child, discord.ui.Select):
                child.placeholder = label or "Timed out! Please try again."

        if self.message:
            await self.message.edit(view=self)

    def build_embed(self) -> typing.Tuple[discord.Embed, discord.SelectOption]:
        data = []
        for track in self.tracks:
            self.options.append(
                discord.SelectOption(label=track.title[0:100], value=track.identifier, description=track.author[0:100]))
            data.append(f"[{track.title}]({track.uri})")
        self.options.append(discord.SelectOption(label='Cancel', emoji='❌', value='cancel'))
        data = [f"`{i}:` {desc}" for i, desc in enumerate(data, start=1)]
        embed = discord.Embed(title='Select a track to enqueue', description='\n'.join(data))
        self.embed = embed

    async def start(self):
        self.message = await self.ctx.send(embed=self.embed, view=self)


class Music(commands.Cog):
    """
    🎵 Commands related to playing music through the bot in a voice channel.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = '🎵'
        self.select_brief = 'Music Commands'

    async def cog_before_invoke(self, ctx: Context):
        unensured_commands = ('lyrics', 'lyrics user', 'lyrics search', 'current', 'queue', 'nodes', 'toggle', 'role', 'settings', 'dj')
        if (is_guild := ctx.guild is not None) and ctx.command.qualified_name not in unensured_commands:
            await self.ensure_voice(ctx)

        if is_guild and ctx.command.name in ('current', 'queue'):

            if ctx.voice_client is None:
                raise NoPlayer

        return is_guild

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, _, after: discord.VoiceState):
        if not (player := member.guild.voice_client):
            player = self.bot.pomice.get_node().get_player(member.guild.id)

        if not player:
            return

        if member.id == self.bot.user.id and after.channel:

            if not player.is_paused:
                await player.set_pause(True)
                await asyncio.sleep(1)
                await player.set_pause(False)

        if member.id == self.bot.user.id and not after.channel:
            return await player.destroy()

        if member.bot:
            return

        if member.id == player.dj.id and (not after.channel or after.channel != player.channel):
            members = self.get_members(player.channel.id)

            if members:
                for m in members:
                    if m == player.dj:
                        break
                    else:
                        player.dj = m
                        break
                else:
                    await player.destroy()
                    return
            else:
                await player.destroy()
                return

            await player.text_channel.send(f"🎧 **|** {player.dj.mention} is now the DJ!",
                                           allowed_mentions=discord.AllowedMentions.none())
            return

        if after.channel and player.channel and after.channel.id == player.channel.id and player.dj not in player.channel.members and player.dj != member:

            if member.bot:
                return
            player.dj = member

            await player.text_channel.send(f"🎧 **|** {player.dj.mention} is now the DJ!",
                                           allowed_mentions=discord.AllowedMentions.none())
            return

    @commands.Cog.listener()
    async def on_pomice_track_start(self, player: Player, track: pomice.Track):
        player = player or self.bot.pomice.get_node().get_player(track.ctx.guild.id)
        if not player:
            return

        track: pomice.Track = player.current.original
        ctx: Context = track.ctx

        if player.loop == 1:
            return

        if player.loop == 2 and player.queue.is_empty:
            return

        player.message = await ctx.send(embed=self.build_embed(player), reply=False)

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: Player, track: pomice.Track, _):
        player = player or self.bot.pomice.get_node().get_player(track.ctx.guild.id)
        if not player:
            return

        text: discord.TextChannel = player.text_channel
        channel: discord.TextChannel = player.channel
        player.clear_votes()

        if player.loop == 1:
            await player.play(track)
            return

        if player.loop == 2:
            player.queue.put(track)

        try:
            await player.message.delete()
        except (discord.HTTPException, AttributeError):
            pass

        try:
            async with timeout(300):
                track = await player.queue.get_wait()

                try:
                    await player.play(track, ignore_if_playing=True)
                except Exception as e:
                    self.bot.dispatch("pomice_track_end", player, track, "Failed playing the next track in a queue")
                    logging.error(e)
                    raise TrackFailed(track)

        except asyncio.TimeoutError:
            try:
                await player.destroy()
            except:
                return
            else:
                await text.send(f'👋 **|** I\'ve left {channel.mention}, due to inactivity.')

    async def cog_command_error(self, ctx: Context, error):
        message = getattr(error, 'message', None) if hasattr(error, 'custom') else None
        if message:
            await ctx.send(message)

    async def ensure_voice(self, ctx: Context):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        should_connect = ctx.command.name in ('play', 'connect', 'playnext', 'playnow')
        player = ctx.voice_client

        if ctx.command.name in ('connect') and player:
            raise AlreadyConnectedToChannel(ctx)

        if not ctx.author.voice or not (channel := ctx.author.voice.channel):
            raise NoConnection

        if not player:
            if not should_connect:
                raise NoVoiceChannel

            if ctx.guild.afk_channel:
                if channel.id == ctx.guild.afk_channel.id:
                    raise AfkChannel

            permissions = channel.permissions_for(ctx.me)

            if not permissions.connect:
                raise NoPerms('CONNECT', channel)

            if not permissions.speak:
                raise NoPerms('SPEAK', channel)

            if channel.user_limit != 0:
                limit = channel.user_limit
                if len(channel.members) == limit:
                    raise FullVoiceChannel(ctx)

            player = await channel.connect(cls=Player)
            player.text_channel = ctx.channel
            player.dj = ctx.author

        else:
            if int(player.channel.id) != channel.id:
                raise IncorrectChannelError(ctx)
            if int(player.text_channel) != ctx.channel.id:
                raise IncorrectTextChannelError(ctx)

    def get_channel(self, id: int):
        return self.bot.get_channel(id)

    def get_members(self, channel_id: int):
        channel = self.bot.get_channel(int(channel_id))
        return list(member for member in channel.members if not member.bot)

    async def get_tracks(self, ctx: Context, query: str):
        return await ctx.voice_client.get_tracks(query.strip("<>"), ctx=ctx)

    def get_thumbnail(self, track: pomice.Track) -> Union[str, discord.embeds._EmptyEmbed]:
        if (thumbnail := track.info.get("thumbnail")):
            return thumbnail
        elif any(i in track.uri for i in ("youtu.be", "youtube.com")):
            return "https://img.youtube.com/vi/{}/maxresdefault.jpg".format(track.identifier)
        else:
            return discord.embeds.EmptyEmbed

    def build_embed(self, player: pomice.Player):
        track: pomice.Track = player.current

        if not track.spotify:
            track: pomice.Track = player.current.original

        if track.is_stream:
            length = "<:status_streaming:596576747294818305> Live Stream"
        else:
            length = format_time(track.length)

        title = track.title if not track.spotify else str(track.title)
        embed = discord.Embed(title=f"Now playing: {title}", url=track.uri)
        embed.set_thumbnail(url=self.get_thumbnail(track))
        embed.add_field(name="Duration:", value=length)
        embed.add_field(name="Requested by:", value=track.requester.mention)
        embed.add_field(name="Artist:" if not ", " in track.author else "Artists:", value=track.author)

        if track.uri.startswith("https://open.spotify.com/"):
            embed.set_footer(text="Spotify Track",
                             icon_url='https://cdn.discordapp.com/emojis/904696493447974932.png?size=96')

        elif track.uri.startswith("https://soundcloud.com/"):
            embed.set_footer(text="SoundClound Track",
                             icon_url="https://cdn.discordapp.com/emojis/314349923090825216.png?size=96")

        elif track.uri.startswith("https://www.youtube.com/"):
            embed.set_footer(text="YouTube Track",
                             icon_url="https://cdn.discordapp.com/emojis/593301958660718592.png?size=96")

        else:
            pass

        return embed

    async def is_privileged(self, ctx: CustomContext):
        """Check whether the user is an Admin or DJ or alone in a VC."""
        player = ctx.voice_client
        role = (await self.bot.db.fetchval("SELECT dj_id FROM prefixes WHERE guild_id = $1", ctx.guild.id)) or 1
        if any([player.dj.id == ctx.author.id, ctx.author.guild_permissions.manage_messages,
                ctx.author._roles.has(role), role == 1234, ctx.author.id in self.bot.owner_ids]):
            return True
        else:
            return False

    def required(self, ctx: Context):
        """Method which returns required votes based on amount of members in a channel."""
        members = len(self.get_members((ctx.voice_client).channel.id))
        return math.ceil(members / 2.5)

    @commands.command(aliases=["p", "search"])
    async def play(self, ctx: Context, *, query: str):
        """Loads your input and adds it to the queue
        Use the `search` alias to search.
        """
        player = ctx.voice_client

        try:
            results = await self.get_tracks(ctx, query)
        except pomice.TrackLoadError:
            raise LoadFailed

        if not results:
            raise NoMatches

        if isinstance(results, pomice.Playlist):
            tracks = results.tracks
            for track in tracks:
                player.queue.put(track)

            if results.spotify:
                thumbnail = results.thumbnail
            else:
                thumbnail = self.get_thumbnail(results.tracks[0])

            embed = discord.Embed(description=f' Enqueued [{results}]({query}) with {len(tracks)} songs.')
            await ctx.send(embed=embed, footer=False)

        else:
            results: typing.List[pomice.Track]
            if ctx.invoked_with == 'search':
                view = SearchMenu(ctx, tracks=results)
                await view.start()
                await view.wait()
                track = view.track
            else:
                track = results[0]

            if not track:
                return

            player.queue.put(track)
            embed = discord.Embed(description=f"Enqueued [{track.title}]({track.uri})")
            embed.set_thumbnail(url=self.get_thumbnail(track))
            embed.set_footer(text='Use the `search` command to search before playing')
            await ctx.send(embed=embed, footer=False)

        if not player.is_playing:
            await player.play(player.queue.get())

    @commands.command(aliases=["pn", "search-next"])
    async def playnext(self, ctx: Context, *, query: str):
        """Loads your input and adds to the top of the queue
        Use the `search-next` alias to search."""
        player = ctx.voice_client

        try:
            results = await self.get_tracks(ctx, query)
        except pomice.TrackLoadError:
            raise LoadFailed

        if not results:
            raise NoMatches

        if isinstance(results, pomice.Playlist):
            tracks = results.tracks
            for track in reversed(tracks):
                player.queue.put_at_front(track)

            if results.spotify:
                thumbnail = results.thumbnail
            else:
                thumbnail = self.get_thumbnail(results.tracks[0])

            embed = discord.Embed(description=f'Enqueued [{results}]({query}) with {len(tracks)} songs.')
            embed.set_thumbnail(url=thumbnail or discord.embeds.EmptyEmbed)
            await ctx.send(embed=embed, footer=False)

        else:
            results: typing.List[pomice.Track]
            if ctx.invoked_with == 'search-next':
                view = SearchMenu(ctx, tracks=results)
                await view.start()
                await view.wait()
                track = view.track
            else:
                track = results[0]

            if not track:
                return

            player.queue.put_at_front(track)

            embed = discord.Embed(description=f"Enqueued [{track.title}]({track.uri})")
            embed.set_thumbnail(url=self.get_thumbnail(track))
            await ctx.send(embed=embed, footer=False)

        if not player.is_playing:
            track = player.queue.get()
            await player.play(track)

    @commands.command(aliases=["pnow", "search-now"])
    async def playnow(self, ctx: Context, *, query: str):
        """Loads your input and plays it instantly
        Use the `search-now` alias to search!"""
        player = ctx.voice_client

        try:
            results = await self.get_tracks(ctx, query)
        except pomice.TrackLoadError:
            raise LoadFailed

        if not results:
            raise NoMatches

        if isinstance(results, pomice.Playlist):
            tracks = results.tracks
            for track in reversed(tracks):
                player.queue.put_at_front(track)

            if results.spotify:
                thumbnail = results.thumbnail
            else:
                thumbnail = self.get_thumbnail(results.tracks[0])

            embed = discord.Embed(description=f'Enqueued [{results}]({query}) with {len(tracks)} songs.')
            embed.set_thumbnail(url=thumbnail or discord.embeds.EmptyEmbed)
            await ctx.send(embed=embed, footer=False)

        else:
            results: typing.List[pomice.Track]
            if ctx.invoked_with == 'search':
                view = SearchMenu(ctx, tracks=results)
                await view.start()
                await view.wait()
                track = view.track
            else:
                track = results[0]

            if not track:
                return

            player.queue.put_at_front(track)

            embed = discord.Embed(description=f"Enqueued [{track.title}]({track.uri}) as the next song.")
            embed.set_thumbnail(url=self.get_thumbnail(track))
            await ctx.send(embed=embed, footer=False)

        if player.loop == 1:
            player.loop = 0

        if not player.is_playing:
            track = player.queue.get()
            await player.play(track)
        else:
            await player.stop()

    @commands.command(aliases=["join", ])
    async def connect(self, ctx: Context):
        """Connects the bot to your voice channel"""
        await ctx.send(f'🔌 **|** Connected to {ctx.voice_client.channel.mention}')

    @commands.command(aliases=["np", ])
    async def current(self, ctx: Context):
        """Displays info about the current track in the queue"""
        player = ctx.voice_client
        if not player:
            raise NoPlayer

        if not player.is_playing:
            raise NoCurrentTrack

        await ctx.send(embed=self.build_embed(player))

    @commands.command(aliases=["dc"])
    async def disconnect(self, ctx: Context):
        """Disconnects the player from its voice channel."""
        player = ctx.voice_client
        channel = player.channel
        if not await self.is_privileged(ctx):
            raise NotAuthorized

        await player.destroy()
        await ctx.send(f'👋 **|** Disconnected from {channel.mention}')

    @commands.command(aliases=["next"])
    async def skip(self, ctx: Context):
        """Skips the currently playing track"""
        player = ctx.voice_client

        if not player.current:
            raise NoCurrentTrack

        if await self.is_privileged(ctx):
            await player.skip()

        else:
            required = self.required(ctx)

            if required == 1:
                await player.skip()
                return

            if not player.current_vote:
                player.current_vote = ctx.command.name
                player.add_vote(ctx.author)

                embed = discord.Embed(title='A vote has been started')
                embed.description = '{} has started a vote for skipping [{}]({})'.format(ctx.author.mention,
                                                                                         player.current.title,
                                                                                         player.current.uri)
                embed.set_footer(text='Current votes: {} / {}'.format(len(player.votes), required))

                return await ctx.send(embed=embed, footer=False)

            if ctx.author in player.votes:
                raise AlreadyVoted

            player.add_vote(ctx.author)
            if len(player.votes) >= required:
                embed = discord.Embed(title='Vote passed')
                embed.description = 'The required amout of votes ({}) has been reached'.format(required)
                embed.set_footer(text='Current votes: {} / {}'.format(len(player.votes), required))

                await ctx.send(embed=embed, footer=False)
                await player.skip()
            else:
                await ctx.send(f'🎟 **|** **{ctx.author}** has voted')
                embed = discord.Embed(title='Vote added')
                embed.description = '{} has voted for skipping [{}]({})'.format(ctx.author.mention,
                                                                                player.current.title,
                                                                                player.current.uri)
                embed.set_footer(text='Current votes: {} / {}'.format(len(player.votes), required))

                await ctx.send(embed=embed, footer=False)

    @commands.command(name='stop')
    async def stop_playback(self, ctx: Context):
        """Stops the currently playing track and returns to the beginning of the queue"""
        player = ctx.voice_client

        if not player.queue.is_empty:
            player.queue.clear()

        if player.loop == 1:
            player.loop = 0

        await player.stop()
        await ctx.send("🛑 **|** The playback was stopped and queue cleared")

    @commands.command(name='qclear')
    async def clear_queue(self, ctx: Context):
        """Removes all tracks from the queue"""
        player = ctx.voice_client

        if player.queue.is_empty:
            raise QueueIsEmpty

        player.queue.clear()
        await ctx.send("🛑 **|** The playback was stopped and queue cleared")

    @commands.command(aliases=["q", "upcoming"], name='queue')
    async def _queue(self, ctx: Context):
        """Displays the current song queue"""
        player = ctx.voice_client

        if player.queue.is_empty:
            raise QueueIsEmpty

        info = []
        for track in player.queue:
            info.append(f'**[{track.title}]({track.uri})** ({format_time(track.length)})')

        menu = paginator.ViewPaginator(paginator.QueueMenu(info, ctx), ctx=ctx)
        await menu.start()

    @commands.command()
    async def seek(self, ctx: Context, *, time: str):
        """Seeks to a position in the track"""
        player = ctx.voice_client

        if not player.is_playing:
            raise NoCurrentTrack

        milliseconds = 0

        if match := HH_MM_SS_RE.fullmatch(time):
            milliseconds += int(match.group("h")) * 3600000
            milliseconds += int(match.group("m")) * 60000
            milliseconds += int(match.group("s")) * 1000
            new_position = milliseconds

        elif match := MM_SS_RE.fullmatch(time):
            milliseconds += int(match.group("m")) * 60000
            milliseconds += int(match.group("s")) * 1000
            new_position = milliseconds

        elif match := OFFSET_RE.fullmatch(time):
            milliseconds += int(match.group("s")) * 1000

            position = player.position
            new_position = position + milliseconds

        elif match := HUMAN_RE.fullmatch(time):
            if m := match.group("m"):
                if match.group("s") and time.lower().endswith("m"):
                    embed = discord.Embed(title='Invalid timestamp', color=discord.Color.red())
                    embed.add_field(name='Here are the supported timestamps:', value=(
                        "\n```yaml"
                        f"\n{ctx.clean_prefix}seek 01:23:30"
                        f"\n{ctx.clean_prefix}seek 00:32"
                        f"\n{ctx.clean_prefix}seek 2m 4s"
                        f"\n{ctx.clean_prefix}seek 50s"
                        f"\n{ctx.clean_prefix}seek +30s"
                        f"\n{ctx.clean_prefix}seek -23s"
                        "\n```"
                    ))

                    return await ctx.send(embed=embed, footer=False)
                milliseconds += int(m) * 60000
            if s := match.group("s"):
                if time.lower().endswith("m"):
                    milliseconds += int(s) * 60000
                else:
                    milliseconds += int(s) * 1000

            new_position = milliseconds

        else:
            embed = discord.Embed(title='Invalid timestamp', color=discord.Color.red())
            embed.add_field(name='Here are the supported timestamps:', value=(
                "\n```yaml"
                f"\n{ctx.clean_prefix}seek 01:23:30"
                f"\n{ctx.clean_prefix}seek 00:32"
                f"\n{ctx.clean_prefix}seek 2m 4s"
                f"\n{ctx.clean_prefix}seek 50s"
                f"\n{ctx.clean_prefix}seek +30s"
                f"\n{ctx.clean_prefix}seek -23s"
                "\n```"
            ))

            return await ctx.send(embed=embed, footer=False)

        if new_position < 0 or new_position > player.current.length - 1:
            raise InvalidSeek

        await ctx.send("The current track was sought to {}".format(format_time(new_position)))
        await player.seek(new_position)

    @commands.command()
    async def pause(self, ctx: Context):
        """Pauses playback (if possible)"""
        player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        await ctx.send(f"⏸ **|** Playback paused")

    @commands.command()
    async def resume(self, ctx: Context):
        """Resumes playback (if possible)"""
        player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if not player.is_paused:
            raise PlayerIsNotPaused

        await player.set_pause(False)
        await ctx.send("▶ **|** The current track was resumed.")

    @commands.command(aliases=["vol"])
    async def volume(self, ctx: Context, volume: Union[int, str]):
        """Sets the player's volume; If you input "reset", it will set the volume back to default"""
        player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if isinstance(volume, str):
            if volume.lower() == "reset":
                await player.set_volume(100)
                await ctx.send(f"🔊 **|** The volume was reset to **100%**")
            else:
                raise InvalidInput

        if isinstance(volume, int):
            if volume >= 126 or volume <= 0:
                raise InvalidVolume
            await player.set_volume(volume)
            await ctx.send(f"🔊 **|** The volume is now **{volume}%**")

    @commands.command()
    async def shuffle(self, ctx: Context):
        """Randomizes the current order of tracks in the queue"""
        player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if player.queue.is_empty:
            raise NothingToShuffle

        player.queue.shuffle()
        await ctx.send('🔀 **|** The queue was shuffled')

    @commands.group(invoke_without_command=True)
    async def loop(self, ctx: Context, mode: str = None):
        if mode:
            await ctx.send(f'❌ **|** {mode[0:50]} did not match `track`, `queue` or `disable`')
        else:
            player: Player = ctx.voice_client
            if player:
                await ctx.send(f'🔁 **|** The current loop mode is `{["Disabled", "Track", "Queue"][player.loop]}`')

    @loop.command()
    async def track(self, ctx: Context):
        """Starts looping your currently playing track"""
        player: Player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if not player.current:
            raise NoCurrentTrack

        if player.loop == 1:
            raise commands.BadArgument('❌ **|** Loop mode is already set to **track**')

        player.loop = 1
        await ctx.send('🔂 **|** Loop mode set to **track**')

    @loop.command()
    async def queue(self, ctx: Context):
        """Starts looping your currently playing track"""
        player: Player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if player.queue.is_empty:
            raise QueueIsEmpty

        if player.loop == 2:
            raise commands.BadArgument('❌ **|** Loop mode is already set to **playlist**')

        player.loop = 2
        await ctx.send('🔁 **|** Loop mode set to Playlist')

    @loop.command()
    async def disable(self, ctx: Context):
        """Starts looping your currently playing track"""
        player: Player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        if player.loop == 0:
            raise commands.BadArgument('❌ **|** Loop mode is already **disabled**!')

        player.loop = 0
        await ctx.send('➡ **|** Loop mode **disabled**!')

    @commands.command(name='dj-swap')
    async def dj_swap(self, ctx: Context, member: discord.Member = None):
        """Swap the current DJ to another member in the voice channel."""
        player: Player = ctx.voice_client

        if not await self.is_privileged(ctx):
            raise NotAuthorized

        members = self.get_members(player.channel.id)

        if member and member not in members:
            raise commands.BadArgument(f'{member} is not in the voice channel')

        if member and member == player.dj:
            raise commands.BadArgument('You are already the DJ!')

        if len(members) == 1:
            raise commands.BadArgument('You are the only human in the channel!')

        if member:
            player.dj = member
            return await ctx.send(f'The DJ has been assigned to {player.dj.mention}')

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await ctx.send(f'The DJ has been assigned to {m.mention}')

    @commands.command()
    async def nodes(self, ctx: Context):
        nodes = [x for x in self.bot.pomice.nodes.values()]
        raw = []

        for node in nodes:
            stats = node._stats

            before = t.monotonic()
            async with self.bot.session.get(node._rest_uri, timeout=1):
                now = t.monotonic()
                ping = round((now - before) * 1000)
            uptime = str(datetime.timedelta(milliseconds=stats.uptime))
            uptime = uptime.split('.')

            raw.append([
                {'Identifier': '`{}`'.format(node._identifier)},
                {'All Players': '`{}`'.format(stats.players_total)},
                {'Active Players': '`{}`'.format(stats.players_active)},
                {'Free RAM': '`{}`'.format(convert_bytes(stats.free))},
                {'Used RAM': '`{}`'.format(convert_bytes(stats.used))},
                {'All RAM': '`{}`'.format(convert_bytes(stats.allocated))},
                {'Ping': '`{} ms`'.format(ping)},
                {'Available': '`{}`'.format(node._available)},
                {'Uptime': '`{}`'.format(uptime[0])}
            ])

        menu = paginator.ViewPaginator(paginator.NodesMenu(raw, ctx), ctx=ctx)
        await menu.start()

    @staticmethod
    async def deliver_lyrics(ctx: CustomContext, song: openrobot.LyricResult):
        pages = jishaku.paginators.WrappedPaginator(prefix='', suffix='', max_size=4000)
        for line in song.lyrics.split('\n'):
            pages.add_line(line)
        reply = True
        embed = discord.Embed(title=f"Lyrics for `{song.title}`")
        embed.set_author(name=f"song by: {song.artist}")
        for page in pages.pages:
            embed.description = page
            await ctx.send(embed=embed, reply=reply, footer=False)
            embed.title = discord.Embed.Empty
            embed.author.name = discord.Embed.Empty
            embed.author.icon_url = discord.Embed.Empty
            reply = False

    @commands.group()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lyrics(self, ctx: CustomContext):
        """ Shows the lyrics of the currently playing song.

         _Provided by [OpenRobot](https://api.openrobot.xyz/)_ """
        if ctx.invoked_subcommand is not None:
            return
        if not (player := ctx.voice_client):
            player = self.bot.pomice.get_node().get_player(ctx.guild.id)
        if not player:
            raise commands.BadArgument('I am not connected to a voice channel.'
                                       '\nUse `lyrics user [user]` or `lyrics search <query>` to search')
        player: Player
        if not (current := player.current):
            raise commands.BadArgument('There is no song playing in the current voice channel.'
                                       '\nUse `lyrics user [user]` or `lyrics search <query>` to search')

        song = await helper.LyricsConverter().convert(ctx, f"{current.title}")

        if not song.lyrics:
            raise commands.BadArgument(f'No songs found! See `{ctx.clean_prefix}help {ctx.command.qualified_name}`'
                                       f'to find out how to use this command!')
        await self.deliver_lyrics(ctx, song)

    @lyrics.command(name='search')
    async def lyrics_search(self, ctx: Context, *, query: helper.LyricsConverter):
        """ Searches for a song and shows the lyrics. """
        await self.deliver_lyrics(ctx, query)

    @lyrics.command(name='user')
    async def lyrics_user(self, ctx: Context, *, user: discord.Member = None):
        """ Shows the lyrics for a song the user is currently listening to on spotify. """
        member = user or ctx.author
        if not (spotify := discord.utils.find(lambda a: isinstance(a, discord.Spotify), member.activities)):
            raise commands.BadArgument(f'{"This user is" if member != ctx.author else "You are"} not listening to Spotify.')
        await self.deliver_lyrics(ctx, (await helper.LyricsConverter().convert(ctx, spotify.title)))


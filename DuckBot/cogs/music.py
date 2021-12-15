from discord.ext import commands


class Music(commands.Cog):
    """
    🎵 Commands related to playing music through the bot in a voice channel.
    """

    def __init__(self, bot):
        self.bot = bot
        self.select_emoji = '🎵'
        self.select_brief = 'Music Commands'

    async def no_music(self, ctx: commands.Context):
        await ctx.send('Sorry, but the music cog is temporarily disabled due to a bug. We will be back soon!')

    @commands.command(aliases=["p", "search"])
    async def play(self, ctx):
        """Loads your input and adds it to the queue
        Use the `search` alias to search.
        """
        await self.no_music(ctx)

    @commands.command(aliases=["pn", "search-next"])
    async def playnext(self, ctx):
        """Loads your input and adds to the top of the queue
        Use the `search-next` alias to search."""
        await self.no_music(ctx)

    @commands.command(aliases=["pnow", "search-now"])
    async def playnow(self, ctx):
        """Loads your input and plays it instantly
        Use the `search-now` alias to search!"""
        await self.no_music(ctx)

    @commands.command(aliases=["join", ])
    async def connect(self, ctx):
        """Connects the bot to your voice channel"""
        await self.no_music(ctx)

    @commands.command(aliases=["np", ])
    async def current(self, ctx):
        """Displays info about the current track in the queue"""
        await self.no_music(ctx)

    @commands.command(aliases=["next"])
    async def skip(self, ctx):
        """Skips the currently playing track"""
        await self.no_music(ctx)

    @commands.command(name='stop')
    async def stop_playback(self, ctx):
        """Stops the currently playing track and returns to the beginning of the queue"""
        await self.no_music(ctx)

    @commands.command(name='qclear')
    async def clear_queue(self, ctx):
        """Removes all tracks from the queue"""
        await self.no_music(ctx)

    @commands.command(aliases=["q", "upcoming"], name='queue')
    async def _queue(self, ctx):
        """Displays the current song queue"""
        await self.no_music(ctx)

    @commands.command()
    async def seek(self, ctx):
        """Seeks to a position in the track"""
        await self.no_music(ctx)

    @commands.command()
    async def pause(self, ctx):
        """Pauses playback (if possible)"""
        await self.no_music(ctx)

    @commands.command()
    async def resume(self, ctx):
        """Resumes playback (if possible)"""
        await self.no_music(ctx)

    @commands.command(aliases=["vol"])
    async def volume(self, ctx):
        """Sets the player's volume; If you input "reset", it will set the volume back to default"""
        await self.no_music(ctx)

    @commands.command()
    async def shuffle(self, ctx):
        """Randomizes the current order of tracks in the queue"""
        await self.no_music(ctx)

    @commands.group()
    async def loop(self, ctx):
        await self.no_music(ctx)

    @commands.command(name='dj-swap')
    async def dj_swap(self, ctx):
        """Swap the current DJ to another member in the voice channel."""
        await self.no_music(ctx)

    @commands.command()
    async def nodes(self, ctx):
        await self.no_music(ctx)

    @commands.group()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lyrics(self, ctx):
        """ Shows the lyrics of the currently playing song.

         _Provided by [OpenRobot](https://api.openrobot.xyz/)_ """
        await self.no_music(ctx)

    @lyrics.command(name='search')
    async def lyrics_search(self, ctx):
        """ Searches for a song and shows the lyrics. """
        await self.no_music(ctx)

    @lyrics.command(name='user')
    async def lyrics_user(self, ctx):
        """ Shows the lyrics for a song the user is currently listening to on spotify. """
        await self.no_music(ctx)


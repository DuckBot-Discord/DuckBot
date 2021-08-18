import os, discord, asyncio, traceback, json, typing, datetime
from dotenv import load_dotenv
from discord.ext import commands, menus
from jishaku.models import copy_context_with
import contextlib

import functools
import itertools
import math
import discord
import youtube_dl
from async_timeout import timeout

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    # NOW PLAYING
    def create_embed(self):
        embed = (discord.Embed(description=f"""
                 Uploaded by [{self.source.uploader}]({self.source.uploader_url}) | {self.source.duration}
                 Queued by: {self.requester.mention}
                 """,
                 title=f"{self.source.title}",
                 url=self.source.url,
                 color=discord.Color.blurple())
                 .set_image(url=self.source.thumbnail))
        return embed

class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None



class Confirm(menus.Menu):
    """Management-only stuff"""
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result

class bot_management(commands.Cog):
    """🤖Management stuff. Ignore this"""
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(aliases = ['setstatus', 'ss', 'activity'], usage="<playing|listening|watching|competing|clear> [text]")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def status(self, ctx, type: typing.Optional[str] = None,* , argument: typing.Optional[str] = None):

        if type == None:
            embed = discord.Embed(title= "`ERROR` NO STATUS GIVEN!", description="Here is a list of available types:", color = ctx.me.color)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Playing <status>'), value='Sets the status to Playing.', inline=False)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Listening <status>'), value='Sets the status to Listening.', inline=False)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Watching <status>'), value='Sets the status to Watching.', inline=False)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Competing <status>'), value='Sets the status to `Competing in`.', inline=False)
            await ctx.send(embed=embed, delete_after=45)
            await asyncio.sleep(45)
            try: await ctx.message.delete()
            except discord.Forbidden: pass
            return

        type = type.lower()

        if type == "playing":
            if argument !=  None:
                # Setting `Playing ` status
                await self.bot.change_presence(activity=discord.Game(name=f'{argument}'))
                await ctx.message.add_reaction('✅')
                await ctx.send(f"Activity changed to `Playing {argument}` ")

        elif type == "listening":
            if argument !=  None:
                # Setting `Listening ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{argument}'))
                await ctx.send(f"Activity changed to `Listening to {argument}` ")

        elif type == "watching":
            if argument !=  None:
                #Setting `Watching ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{argument}'))
                await ctx.send(f"Activity changed to `Watching {argument}` ", delete_after=10)
                await asyncio.sleep(10)
                try: await ctx.message.delete()
                except discord.Forbidden: pass

        elif type == "competing":
            if argument !=  None:
                #Setting `other ` status
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=f'{argument}'))
                await ctx.send(f"Activity changed to `Competing in {argument}` ")

        elif type == "clear":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name='cleared'))
            await ctx.send(f"Activity cleared")

        else:
            embed = discord.Embed(title= "`ERROR` INVALID TYPE!", description="Here is a list of available types:", color = ctx.me.color)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Playing <status>'), value='Sets the status to Playing.', inline=False)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Listening <status>'), value='Sets the status to `Listening to`.', inline=False)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Watching <status>'), value='Sets the status to `Watching`.', inline=False)
            embed.add_field(name=(f'{ctx.prefix}{ctx.command} Competing <status>'), value='Sets the status to `Competing in`.', inline=False)
            await ctx.send(embed=embed, delete_after=45)
            await asyncio.sleep(45)
            try: await ctx.message.delete()
            except discord.Forbidden: pass

    @commands.command(help = "Adds something to de to-do list", usage="<text>")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def todo(self, ctx, *, message = None):
        channel = self.bot.get_channel(830992446434312192)
        if message == None:
            await ctx.message.add_reaction('⚠')
            return
        if ctx.message.channel == channel:
            await ctx.message.delete()
        embed = discord.Embed(description=message, color=0x47B781)
        await channel.send(embed=embed)
        await ctx.message.add_reaction('✅')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            if after.channel.guild.id == 841298004929806336:
                textchannel = self.bot.get_channel(841298004929806340)
                await textchannel.send(f'<:joined:849392863557189633> {member.name} **joined** __{after.channel.name}__!')
        if before.channel is not None and after.channel is not None:
            if before.channel.guild.id == 841298004929806336 and before.channel.id != after.channel.id:
                textchannel = self.bot.get_channel(841298004929806340)
                await textchannel.send(f'<:moved:848312880666640394> {member.name} **has been moved to** __{after.channel.name}__!')
        if before.channel is not None and after.channel is None:
            if before.channel.guild.id == 841298004929806336:
                textchannel = self.bot.get_channel(841298004929806340)
                await textchannel.send(f'<:left:849392885785821224> {member.name} **left** __{before.channel.name}__!')

    @commands.command(aliases = ['mm','maintenancemode'], help="puts the bot under maintenance", usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def maintenance(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.bot.maintenance = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.bot.maintenance = False
        else:
            if self.bot.maintenance == False:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.bot.maintenance = True
            elif self.bot.maintenance == True:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.bot.maintenance = False

    @commands.command(aliases = ['np','invisprefix', 'sp', 'noprefix'], help="toggles no-prefix mode on or off", usage="[on|off]")
    @commands.is_owner()
    @commands.bot_has_permissions(add_reactions=True)
    async def silentprefix(self, ctx, state: typing.Optional[str] = None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.bot.noprefix = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.bot.noprefix = False
        else:
            if self.bot.noprefix == False:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.bot.noprefix = True
            elif self.bot.noprefix == True:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.bot.noprefix = False


#----------------------------------------------------------------------------#
#------------------------ EXTENSION MANAGEMENT ------------------------------#
#----------------------------------------------------------------------------#

    @commands.command(help="Loads an extension", aliases=['le', 'lc', 'loadcog'], usage="<extension>")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def load(self, ctx, extension = ""):
        embed = discord.Embed(color=ctx.me.color, description = f"⬆ {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.load_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionAlreadyLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension already loaded")
            await message.edit(embed=embed)


        except discord.ext.commands.NoEntryPointError:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ No setup function")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error\n```{traceback_string}```")
            try: await message.edit(embed=embed)
            except:
                embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error ```\n error too long, check the console\n```")
                await message.edit()
            raise e

    @commands.command(help="Unloads an extension", aliases=['unl', 'ue', 'uc'], usage="<extension>")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def unload(self, ctx, extension = ""):
        embed = discord.Embed(color=ctx.me.color, description = f"⬇ {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.unload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not loaded")
            await message.edit(embed=embed)

    @commands.command(help="Reloads an extension", aliases=['rel', 're', 'rc'])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reload(self, ctx, extension = ""):
        embed = discord.Embed(color=ctx.me.color, description = f"🔃 {extension}")
        message = await ctx.send(embed=embed)
        try:
            self.bot.reload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"✅ {extension}")
            await message.edit(embed=embed)
        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not loaded")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.NoEntryPointError:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ No setup function")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error\n```{traceback_string}```")
            try: await message.edit(embed=embed)
            except:
                embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error ```\n error too long, check the console\n```")
                await message.edit()
            raise e

    @commands.command(help="Reloads all extensions", aliases=['relall', 'rall'], usage="[silent|channel]")
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reloadall(self, ctx, argument: typing.Optional[str]):
        self.bot.last_rall = datetime.datetime.utcnow()
        list = ""
        desc = ""
        err = False
        rerel = []
        if argument == 'silent' or argument == 's': silent = True
        else: silent = False
        if argument == 'channel' or argument == 'c': channel = True
        else: channel = False

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                list = f"{list} \n🔃 {filename[:-3]}"

        embed = discord.Embed(color=ctx.me.color, description = list)
        message = await ctx.send(embed=embed)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                    desc = f"{desc} \n✅ {filename[:-3]}"
                except:
                    rerel.append(filename)

        for filename in rerel:
            try:
                self.bot.reload_extension("cogs.{}".format(filename[:-3]))
                desc = f"{desc} \n✅ {filename[:-3]}"

            except discord.ext.commands.ExtensionNotLoaded:
                desc = f"{desc} \n❌ {filename[:-3]} - Not loaded"
            except discord.ext.commands.ExtensionNotFound:
                desc = f"{desc} \n❌ {filename[:-3]} - Not found"
            except discord.ext.commands.NoEntryPointError:
                desc = f"{desc} \n❌ {filename[:-3]} - No setup func"
            except discord.ext.commands.ExtensionFailed as e:
                traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
                desc = f"{desc} \n❌ {filename[:-3]} - Execution error"
                embederr = discord.Embed(color=ctx.me.color, description = f"\n❌ {filename[:-3]} Execution error - Traceback\n```\n{traceback_string}\n```")
                if silent == False:
                    if channel == False: await ctx.author.send(embed=embederr)
                    else: await ctx.send(embed=embederr)
                err = True

        await asyncio.sleep(0.4)
        if err == True:
            if silent == False:
                if channel == False: desc = f"{desc} \n\n📬 {ctx.author.mention}, I sent you all the tracebacks."
                else: desc = f"{desc} \n\n📬 Sent all tracebacks here."
            if silent == True: desc = f"{desc} \n\n📭 silent, no tracebacks sent."
            embed = discord.Embed(color=ctx.me.color, description = desc, title = 'Reloaded some extensions')
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(title = 'Reloaded all extensions', color=ctx.me.color, description = desc)
            await message.edit(embed=embed)


###############################################################################
###############################################################################

    @commands.command(help="Dms a user from any guild", aliases=['md', 'pm', 'id-dm'], usage="[ID]")
    @commands.is_owner()
    async def dm(self, ctx, member: typing.Optional[discord.User], *, message = ""):

        if member == None:
            await ctx.message.add_reaction('⁉')
            await asyncio.sleep(3)
            try: await ctx.message.delete()
            except discord.Forbidden: return
            return
        if member.bot:
            await ctx.message.add_reaction('🤖')
            await asyncio.sleep(3)
            try: await ctx.message.delete()
            except discord.Forbidden: return
            return

        channel = self.bot.get_channel(830991980850446366)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        try:
            if ctx.message.attachments:
                file = ctx.message.attachments[0]
                myfile = await file.to_file()
                embed = discord.Embed(color=0x47B781)
                if message:
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                    await member.send(message, file=myfile)
                else:
                    embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value='_ _')
                    await member.send(file=myfile)
                if ctx.message.attachments:
                    file = ctx.message.attachments[0]
                    spoiler = file.is_spoiler()
                    if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                        embed.set_image(url=file.url)
                    elif spoiler:
                        embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
                    else:
                        embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
                embed.set_footer(text=f'.dm {member.id}')
                await channel.send(embed=embed)
            else:
                await member.send(message)
                embed = discord.Embed(color=0x47B781)
                embed.add_field(name=f'<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}**', value=message)
                embed.set_footer(text=f'.dm {member.id}')
                await channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"{member}'s DMs are closed.")


    @commands.command()
    @commands.is_owner()
    async def sudo(self, ctx: commands.Context, target: discord.User, *, command_string: str):
        """
        Run a command as someone else.

        This will try to resolve to a Member, but will use a User if it can't find one.

        """

        if ctx.guild:
            # Try to upgrade to a Member instance
            # This used to be done by a Union converter, but doing it like this makes
            #  the command more compatible with chaining, e.g. `jsk in .. jsk su ..`
            target_member = None

            with contextlib.suppress(discord.HTTPException):
                target_member = ctx.guild.get_member(target.id) or await ctx.guild.fetch_member(target.id)

            target = target_member or target

        alt_ctx = await copy_context_with(ctx, author=target, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            if alt_ctx.invoked_with is None:
                return await ctx.send('This bot has been hard-configured to ignore this user.')
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.invoke(alt_ctx)

#--------------------------------------------------------------------------------------#
#-------------------- Music stuff stolen from some github... --------------------------#
#-------------------- Owner only tho as its not my own code. --------------------------#
#-------------------- Wouldnt want to just rip off someone's --------------------------#
#-------------------- example as "mine", that ain't fair lol --------------------------#
#--------------------------------------------------------------------------------------#

    @commands.group(help="Music stuff. Owner only tho...", aliases=["m"])
    @commands.guild_only()
    @commands.is_owner()
    async def music(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @music.command(name='join', invoke_without_subcommand=True, aliases=["j"])
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @music.command(name='summon', aliases=["m"])
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.

        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @music.command(name='leave', aliases=['disconnect', 'dc', 'l'])
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @music.command(name='volume', aliases=["v"])
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @music.command(name='now', aliases=['current', 'playing', 'np'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @music.command(name='pause', aliases=["pa"])
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @music.command(name='resume', aliases=["r"])
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @music.command(name='stop', aliases=["st"])
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @music.command(name='skip', aliases=["n", 'sk', 's'])
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @music.command(name='queue', aliases=["q"])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.

        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @music.command(name='shuffle', aliases=["sh"])
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @music.command(name='remove', aliases=["rm"])
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @music.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.

        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @music.command(name='play', aliases=["p"])
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

def setup(bot):
    bot.add_cog(bot_management(bot))

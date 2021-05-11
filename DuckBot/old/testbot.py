from youtube_dl import YoutubeDL
from requests import get
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.utils import get
import discord
from discord.ext import commands


intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.

## WORKS
bot = commands.Bot(command_prefix='t.', case_insensitive=True, intents=intents)

@bot.command()
def search(query):
    with YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
        try: requests.get(arg)
        except: info = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
        else: info = ydl.extract_info(arg, download=False)
    return (info, info['formats'][0]['url'])

@bot.command()
async def join(ctx, voice):
    channel = ctx.author.voice.channel

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

@bot.command()
async def play(ctx, *, query):
    #Solves a problem I'll explain later
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    video, source = search(query)
    voice = get(bot.voice_clients, guild=ctx.guild)

    await join(ctx, voice)

    voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTS), after=lambda e: print('done', e))
    voice.is_playing()

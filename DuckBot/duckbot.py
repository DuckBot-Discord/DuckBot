import os, discord, asyncio, traceback
from dotenv import load_dotenv
from discord.ext import commands
from helpers.helper import failed

intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.

bot = commands.Bot(command_prefix=commands.when_mentioned_or('.', 'duck.', 'duckbot.', 'd.', 'du.', 'db.', 'Duck.', 'D.', 'Duckbot.', '**********'), case_insensitive=True, intents=intents)

bot.remove_command('help')
bot.load_extension('jishaku')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print("======[ BOT ONLINE! ]======")
    print ("Logged in as " + bot.user.name)
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='.help'))


for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension("cogs.{}".format(filename[:-3]))
        except:
            print("========[ WARNING ]========")
            print(f"An error occurred while loading '{filename}'""")


bot.run(TOKEN, reconnect=True)

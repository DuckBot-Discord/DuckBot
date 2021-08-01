import os, discord, asyncio, traceback, datetime, yaml
from dotenv import load_dotenv
from discord.ext import commands

#------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
yaml_data = full_yaml

TOKEN = yaml_data['botToken']

intents = discord.Intents.all() # Enable all intents except for members and presences

bot = commands.Bot(command_prefix=commands.when_mentioned_or('m!'), case_insensitive=True, intents=intents, owner_id=349373972103561218)
bot.load_extension('jishaku')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print ("Logged in as " + bot.user.name)
    print('\033[0m')

print('')
print("\033[93m======[ NORMAL LOAD ]=======")
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension("cogs.{}".format(filename[:-3]))
            print(f'\033[92msuccessfully loaded {filename[:-3]}')
        except:
            print('\033[0m')
            print("\033[31m========[ WARNING ]========")
            print(f"\033[91mAn error occurred while loading '{filename}'""")
            print('\033[0m')
print('\033[0m')
print(TOKEN)
bot.run("ODYxMDE2MjE2NDAyNzg4Mzky.YODp1g.XAYEFWLnie16jMzP1qQhh5MsTs8", reconnect=True)

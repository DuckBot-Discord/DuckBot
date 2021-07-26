import os, discord, asyncio, yaml
from dotenv import load_dotenv
from discord.ext import commands

#------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
yaml_data = full_yaml

async def error_msg(self, ctx):
    await ctx.message.add_reaction('🚫')
    await asyncio.sleep(5)
    try: await ctx.message.delete()
    except: return
    return

intents = discord.Intents.all() # Enable all intents except for members and presences

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!', 't!', '**********'), case_insensitive=True, intents=intents)

bot.remove_command('help')
bot.load_extension('jishaku')

load_dotenv()
TOKEN = yaml_data['botToken']

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print ("Logged in as " + bot.user.name)
    print('\033[0m')
    await bot.wait_until_ready()
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing, name='DM me to contact staff'))
    print("\033[93m======[ DELAYED LOAD ]======")
    for cog in yaml_data['DelayedLoadCogs']:
        try:
            bot.load_extension(f"cogs.{cog}")
            print(f'\033[92msuccessfully loaded {cog}')
        except:
            print('\033[0m')
            print("\033[31m========[ WARNING ]========")
            print(f"\033[91mAn error occurred while loading '{cog}'""")
            print('\033[0m')
    print('\033[0m')

print('')
print("\033[93m======[ NORMAL LOAD ]=======")
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        try:
            if not str(filename[:-3]) in yaml_data['DelayedLoadCogs']:
                bot.load_extension("cogs.{}".format(filename[:-3]))
                print(f'\033[92msuccessfully loaded {filename[:-3]}')
        except:
            print('\033[0m')
            print("\033[31m========[ WARNING ]========")
            print(f"\033[91mAn error occurred while loading '{filename}'""")
            print('\033[0m')
print('\033[0m')


bot.run(TOKEN, reconnect=True)

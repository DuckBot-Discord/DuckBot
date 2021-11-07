import os, discord, asyncio, yaml, asyncpg
from dotenv import load_dotenv
from discord.ext import commands

intents = discord.Intents.all()  # Enable all intents except for members and presences
intents.typing = False  # Subscribe to the privileged members intent.

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!', 'oz!', '**********', '.'), case_insensitive=True,
                   intents=intents)
bot.loaded = False

bot.load_extension('jishaku')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
yaml_data = full_yaml


async def error_msg(self, ctx):
    await ctx.message.add_reaction('🚫')
    await asyncio.sleep(5)
    try:
        await ctx.message.delete()
    except:
        return
    return


async def create_db_pool():
    credentials = {"user": f"{os.getenv('PSQL_USER')}",
                   "password": f"{os.getenv('PSQL_PASSWORD')}",
                   "database": f"{os.getenv('PSQL_DB')}",
                   "host": f"{os.getenv('PSQL_HOST')}"}

    bot.db = await asyncpg.create_pool(**credentials)
    print("connection successful")

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print("Logged in as " + bot.user.name)
    print('\033[0m')
    if bot.loaded == False:
        bot.loaded = True
        await bot.wait_until_ready()
        await bot.change_presence(status=discord.Status.online,
                                  activity=discord.Activity(type=discord.ActivityType.playing,
                                                            name='DM to contact staff'))
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

bot.loop.run_until_complete(create_db_pool())
bot.run(TOKEN, reconnect=True)

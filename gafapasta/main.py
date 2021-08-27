import os, discord, asyncio, traceback, datetime, yaml
from dotenv import load_dotenv
from discord.ext import commands
from asyncrcon import AsyncRCON, AuthenticationException


#------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
yaml_data = full_yaml

TOKEN = yaml_data['botToken']

intents = discord.Intents.all() # Enable all intents except for members and presences

async def get_pre(bot, message):
    if message.channel.id == 861278183369080883:
        return commands.when_mentioned_or("devmc!")(bot,message)
    return commands.when_mentioned_or("mc!")(bot,message)

bot = commands.Bot(command_prefix=get_pre, strip_after_prefix=True, case_insensitive=True, intents=intents, owner_id=349373972103561218)
bot.load_extension('jishaku')

async def create_db_pool():

    credentials = {"user": f"{yaml_data['PSQL_USER']}",
                   "password": f"{yaml_data['PSQL_PASSWORD']}",
                   "database": f"{yaml_data['PSQL_DB']}",
                   "host": f"{yaml_data['PSQL_HOST']}"}
    bot.db = await asyncpg.create_pool(**credentials)
    print("\033[42m\033[34mconnection to database successful")

    await bot.db.execute("CREATE TABLE IF NOT EXISTS whitelist(user_id bigint PRIMARY KEY, message_id bigint, username text);")
    print("\033[42m\033[34mDatabase tables done")
    print('\033[0m')



rcon = AsyncRCON(yaml_data['rconip'], yaml_data['rconpass'])

async def execute_command(imput: str):
    try:
      await rcon.open_connection()
    except AuthenticationException:
        return None
    res = await rcon.command(imput)
    rcon.close()
    return res

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
@commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
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
bot.run(yaml_data['botToken'], reconnect=True)

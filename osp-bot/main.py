import os, discord, asyncio, yaml, datetime, asyncpg
from dotenv import load_dotenv
from discord.ext import commands

#------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
yaml_data = full_yaml

async def create_db_pool():

    credentials = {"user": f"{yaml_data['PSQL_USER']}",
                   "password": f"{yaml_data['PSQL_PASSWORD']}",
                   "database": f"{yaml_data['PSQL_DB']}",
                   "host": f"{yaml_data['PSQL_HOST']}"}
    bot.db = await asyncpg.create_pool(**credentials)
    print("\033[42m\033[34mconnection to database successful")

    await bot.db.execute("CREATE TABLE IF NOT EXISTS userinfo(user_id bigint PRIMARY KEY, birthdate date);")
    print("\033[42m\033[34mDatabase tables done")
    print('\033[0m')

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=commands.when_mentioned_or('o.', '.', '**********'), case_insensitive=True, intents=intents)

bot.load_extension('jishaku')

bot.owner_ids = [326147079275675651, 349373972103561218, 438513695354650626]

bot.maintenance = False
bot.noprefix  = False
bot.started = False

load_dotenv()
TOKEN = yaml_data['botToken']

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print ("Logged in as " + bot.user.name)
    print('\033[0m')
    await bot.wait_until_ready()
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing, name='DM me to contact staff'))
    if bot.started == False:
        bot.started = True
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

@bot.event
async def on_message(message):
    prefixes = ('.')
    if bot.maintenance == True:
        if message.author.id in bot.owner_ids:
            await bot.process_commands(message)
            return
        if message.content.startswith(prefixes):
            await message.add_reaction('<:bot_under_maintenance:857690568368717844>')
        return
    if not message.content.startswith(prefixes) and message.author.id in bot.owner_ids and bot.noprefix == True:
        edited_message = message
        edited_message.content = f".{message.content}"
        await bot.process_commands(edited_message)
    else:
        await bot.process_commands(message)

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

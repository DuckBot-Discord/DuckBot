import os, discord, asyncio, traceback, datetime, asyncpg
from dotenv import load_dotenv
from discord.ext import commands
import logging
logging.basicConfig(level=logging.INFO)

PRE = 'db.'
async def get_pre(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(PRE)(bot,message)
    prefix = await bot.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1', message.guild.id)
    if await bot.is_owner(message.author) and bot.noprefix == True:
        if prefix:
            return commands.when_mentioned_or(prefix, "")(bot,message)
        else:
            return commands.when_mentioned_or(PRE, "")(bot,message)
    if not prefix:
        prefix = PRE
    return commands.when_mentioned_or(prefix)(bot,message)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=get_pre, case_insensitive=True, intents=intents, owner_id=349373972103561218)

bot.invite_url="https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope=bot%20applications.commands"
bot.vote_top_gg="https://top.gg/bot/788278464474120202#/"
bot.vote_bots_gg="https://discord.bots.gg/bots/788278464474120202"
bot.repo="https://github.com/LeoCx1000/discord-bots"
bot.maintenance = False
bot.noprefix  = False
bot.started = False
bot.uptime = datetime.datetime.utcnow()
bot.last_rall = datetime.datetime.utcnow()

os.environ['JISHAKU_HIDE'] = 'True'
bot.load_extension('jishaku')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

async def create_db_pool():

    credentials = {"user": f"{os.getenv('PSQL_USER')}",
                   "password": f"{os.getenv('PSQL_PASSWORD')}",
                   "database": f"{os.getenv('PSQL_DB')}",
                   "host": f"{os.getenv('PSQL_HOST')}"}

    bot.db = await asyncpg.create_pool(**credentials)
    print("connection successful")

    await bot.db.execute("CREATE TABLE IF NOT EXISTS prefixes(guild_id bigint PRIMARY KEY, prefix text);")
    print("table done")

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print ("Logged in as " + bot.user.name)
    print('\033[0m')
    if bot.started==False:
        bot.started=True
        await bot.wait_until_ready()
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='db.help'))

@bot.event
async def on_message(message):
    if bot.maintenance == True and message.author.id != bot.owner_id: return
    await bot.process_commands(message)

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

bot.loop.run_until_complete(create_db_pool())
bot.run(TOKEN, reconnect=True)

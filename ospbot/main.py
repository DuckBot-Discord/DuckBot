import io
import logging
import traceback

import asyncpg
import discord
import os
import yaml

from discord.ext import commands
from dotenv import load_dotenv

# ------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
yaml_data = full_yaml


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(message)s')


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
bot.noprefix = False
bot.started = False

load_dotenv()
TOKEN = yaml_data['botToken']


@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print("Logged in as " + bot.user.name)
    print('\033[0m')
    await bot.wait_until_ready()
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing,
                                                                                      name='DM me to contact staff'))
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
    prefixes = ('.',)
    if bot.maintenance is True:
        if message.author.id in bot.owner_ids:
            await bot.process_commands(message)
            return
        if message.content.startswith(prefixes):
            return
        return
    if not message.content.startswith(prefixes) and message.author.id in bot.owner_ids and bot.noprefix is True:
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


@bot.event
async def on_error(event_method: str, *args, **kwargs) -> None:
    traceback_string = traceback.format_exc()
    for line in traceback_string.split('\n'):
        logging.info(line)
    await bot.wait_until_ready()
    error_channel = bot.get_channel(880181130408636456)
    to_send = f"```yaml\nAn error occurred in an {event_method} event``````py" \
              f"\n{traceback_string}\n```"
    if len(to_send) < 2000:
        try:
            await error_channel.send(to_send)

        except (discord.Forbidden, discord.HTTPException):

            await error_channel.send(f"```yaml\nAn error occurred in an {event_method} event``````py",
                                     file=discord.File(io.StringIO(traceback_string), filename='traceback.py'))
    else:
        await error_channel.send(f"```yaml\nAn error occurred in an {event_method} event``````py",
                                 file=discord.File(io.StringIO(traceback_string), filename='traceback.py'))


bot.loop.run_until_complete(create_db_pool())
bot.run(TOKEN, reconnect=True)

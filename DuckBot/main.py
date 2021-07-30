import os, discord, asyncio, traceback
from dotenv import load_dotenv
from discord.ext import commands

intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.

bot = commands.Bot(command_prefix=commands.when_mentioned_or('\.', '.', 'duck.', 'duckbot.', 'd.', 'du.', 'db.', 'Duck.', 'D.', 'Duckbot.', '**********', 'duckbot '), case_insensitive=True, intents=intents, owner_id=349373972103561218)

bot.invite_url="https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope=bot%20applications.commands"
bot.vote_top_gg="https://top.gg/bot/788278464474120202#/"
bot.vote_bots_gg="https://discord.bots.gg/bots/788278464474120202"
bot.repo="https://github.com/LeoCx1000/discord-bots"

os.environ['JISHAKU_HIDE'] = 'True'
bot.load_extension('jishaku')


bot.maintenance = False
bot.noprefix  = False

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print ("Logged in as " + bot.user.name)
    print('\033[0m')
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='db.help'))

@bot.event
async def on_message(message):
    prefixes = ('\.', '.', 'duck.', 'duckbot.', 'd.', 'du.', 'db.', 'Duck.', 'D.', 'Duckbot.', '**********', 'duckbot ')
    if bot.maintenance == True:
        if message.author.id == bot.owner_id:
            await bot.process_commands(message)
            return
        if message.content.startswith(prefixes):
            await message.add_reaction('<:bot_under_maintenance:857690568368717844>')
        return
    if not message.content.startswith(prefixes) and message.author.id == bot.owner_id and bot.noprefix == True:
        edited_message = message
        edited_message.content = f"duckbot.{message.content}"
        await bot.process_commands(edited_message)
    else:
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


bot.run(TOKEN, reconnect=True)

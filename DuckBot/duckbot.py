import os, discord, asyncio, traceback
from dotenv import load_dotenv
from discord.ext import commands
from helpers.helper import failed

intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.

bot = commands.Bot(command_prefix=commands.when_mentioned_or('.', 'duck.', 'duckbot.', 'd.', 'du.', 'db.', 'Duck.', 'D.', 'Duckbot.', '**********', 'duckbot '), case_insensitive=True, intents=intents, owner_id=349373972103561218)


class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            emby = discord.Embed(description=page)
            await destination.send(embed=emby)

bot.help_command = MyNewHelp()

os.environ['JISHAKU_HIDE'] = 'True'
bot.load_extension('jishaku')


bot.maintenance = False
bot.noprefix  = False

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print("======[ BOT ONLINE! ]======")
    print ("Logged in as " + bot.user.name)
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='db.help'))

@bot.event
async def on_message(message):
    prefixes = ('.', 'duck.', 'duckbot.', 'd.', 'du.', 'db.', 'Duck.', 'D.', 'Duckbot.', '**********', 'duckbot ')
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

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension("cogs.{}".format(filename[:-3]))
        except:
            print("========[ WARNING ]========")
            print(f"An error occurred while loading '{filename}'""")


bot.run(TOKEN, reconnect=True)

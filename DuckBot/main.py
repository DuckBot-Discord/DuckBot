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

class MyHelp(commands.HelpCommand):
    # Formatting
    def get_minimal_command_signature(self, command):
        return '%s%s %s' % (self.clean_prefix, command.qualified_name, command.signature)

    def get_command_name(self, command):
        return '%s' % (command.qualified_name)

   # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(color=0x5865F2, title=f"ℹ {self.context.me.name} help",
        description=f"""```diff
- usage format: <required> [optional]
+ {self.clean_prefix}help [command] - get information on a command
+ {self.clean_prefix}help [category] - get information on a category
```[<:invite:860644752281436171> invite me]({bot.invite_url}) | [<:topgg:870133913102721045> top.gg]({bot.vote_top_gg}) | [<:botsgg:870134146972938310> bots.gg]({bot.vote_bots_gg}) | [<:github:744345792172654643> source]({bot.repo})
_ _""")

        ignored_cogs=['level']
        for cog, commands in mapping.items():
            if cog is None or cog.qualified_name in ignored_cogs: continue
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_name(c) for c in filtered]
            if command_signatures:
                val = "`, `".join(command_signatures)
                embed.add_field(name=cog.qualified_name, value=f"{cog.description}\n`{val}`", inline=True)

        channel = self.get_destination()
        await channel.send(embed=embed)

   # !help <command>
    async def send_command_help(self, command):
        alias = command.aliases
        if alias:
            embed = discord.Embed(color=0x5865F2, title=f"information about: {self.clean_prefix}{command}", description=f"""```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {alias}
description: {command.help}
```""")
        else:
            embed = discord.Embed(color=0x5865F2, title=f"information about {self.clean_prefix}{command}", description=f"""```yaml
      usage: {self.get_minimal_command_signature(command)}
description: {command.help}
```""")
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        command_signatures = [self.get_command_signature(c) for c in entries]
        if command_signatures:
            val = "\n".join(command_signatures)
            embed=discord.Embed(color=0x5865F2, description=f"{cog.description} \n```{val}```", title=f"Commands in {cog.qualified_name}")
            embed.set_footer(text=f"do \"{self.clean_prefix}help [command]\" for more info on a command")
            channel = self.get_destination()
            await channel.send(embed=embed)
        else:
            embed=discord.Embed(color=0x5865F2, description=f"Sorry, nothing's here...", title=f"Commands in {cog.qualified_name}")
            channel = self.get_destination()
            await channel.send(embed=embed)


    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=discord.Embed(color=0x5865F2, description=str(error.original)))


bot.help_command = MyHelp()

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

import os, discord, asyncio, yaml
from dotenv import load_dotenv
from discord.ext import commands

intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.
intents.presences = True  # Subscribe to the privileged members intent.

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!', 'oz!', '**********', '.'), case_insensitive=True, intents=intents)
bot.loaded=False

class MyHelp(commands.HelpCommand):
    # Formatting
    def get_minimal_command_signature(self, command):
        return '%s%s %s' % (self.clean_prefix, command.qualified_name, command.signature)

    def get_command_name(self, command):
        return '%s' % (command.qualified_name)

   # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(color=0x5865F2, title=f"Hello {self.context.author}, this is DuckBot help", description=f"Do `{self.clean_prefix}help [command]` to get information on a command\nDo `{self.clean_prefix}help [category]` to get information on a category\n_ _")
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



bot.load_extension('jishaku')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

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

@bot.event
async def on_ready():
    print("\033[42m======[ BOT ONLINE! ]=======")
    print ("Logged in as " + bot.user.name)
    print('\033[0m')
    if bot.loaded==False:
        bot.loaded=True
        await bot.wait_until_ready()
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing, name='DM to contact staff'))
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

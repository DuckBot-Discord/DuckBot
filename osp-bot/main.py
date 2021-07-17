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

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=commands.when_mentioned_or('.', '**********'), case_insensitive=True, intents=intents)

bot.load_extension('jishaku')

class MyHelp(commands.HelpCommand):
    # Formatting
    def get_minimal_command_signature(self, command):
        return '%s%s %s' % (self.clean_prefix, command.qualified_name, command.signature)

    def get_command_name(self, command):
        return '%s' % (command.qualified_name)
   # !help
    async def send_bot_help(self, mapping):

        embed=discord.Embed(title="Help", description="my prefix is \".\"", color=0x5865F2)
        embed.add_field(name="DM me", value="DM me to get in contact with the OSP Admin Team!", inline=False)
        embed.add_field(name=".rule [rule number]", value="Gives you more information of a specific rule. E.G.: **.Rule 3** would give you more information about Rule number 3.", inline=False)
        embed.add_field(name="Message that mentions me with no other content", value="A randomized message will appear!", inline=False)
        embed.add_field(name="Message that mentions me with other content", value="A randomized response reccomending a DM will appear!", inline=False)
        embed.add_field(name="Says specific trigger word", value="We will send over respective help resources. If there is a missing trigger word you find, message me and we will add it to our database!", inline=False)
        embed.set_footer(text="You can do \".help [command]\" to get more info on a command \nAlso you can do \".help [category]\" to get info on a category")
        channel = self.get_destination()
        await channel.send("Here's my help guide! ```Note: only the messages that start with \".\" are actual commands. Others are response triggers.```DM me if you have questions!", embed=embed)

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

    async def send_error_message(self, error):
        embed = discord.Embed(title="Whoops!", description=error, color=0x5865F2)
        embed.set_footer(text=f"do \"{self.clean_prefix}help\" for help")
        channel = self.get_destination()
        await channel.send(embed=embed)


bot.help_command = MyHelp()

bot.maintenance = False
bot.noprefix  = False

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

@bot.event
async def on_message(message):
    prefixes = ('.')
    if bot.maintenance == True:
        if message.author.id == bot.owner_id:
            await bot.process_commands(message)
            return
        if message.content.startswith(prefixes):
            await message.add_reaction('<:bot_under_maintenance:857690568368717844>')
        return
    if not message.content.startswith(prefixes) and message.author.id == bot.owner_id and bot.noprefix == True:
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

bot.run(TOKEN, reconnect=True)

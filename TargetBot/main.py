import os, discord, asyncio, yaml
from dotenv import load_dotenv
from discord.ext import commands

intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!', 't!', '! ', 't! '), case_insensitive=True, intents=intents)


bot.remove_command("help")
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
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='!guide'))
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
@bot.command()
async def load(ctx, extension):
    if ctx.message.author.id == 349373972103561218:
        try:
            bot.load_extension("cogs.{}".format(extension))
            await ctx.message.add_reaction("✅")
        except discord.ext.commands.ExtensionAlreadyLoaded:
            await ctx.send("Cog already loaded!", delete_after=5)
        except discord.ext.commands.ExtensionNotFound:
            await ctx.message.add_reaction("❓")
        except discord.ext.commands.NoEntryPointError:
            await ctx.send("Cog doesn't have a setup function!", delete_after=5)
        await asyncio.sleep(5)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return
        return
    else: await self.error_msg(ctx)

@load.error
async def load_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.message.add_reaction("❌")
        await ctx.send(f"""```⚠ {error}
[ℹ] for more information check the console```""")
        await asyncio.sleep(3)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return
        return

@bot.command()
async def unload(ctx, extension):
    if ctx.message.author.id == 349373972103561218:
        try:
            bot.unload_extension("cogs.{}".format(extension))
            await ctx.message.add_reaction("✅")
        except discord.ext.commands.ExtensionNotLoaded:
            await ctx.send("Cog wasn't loaded!", delete_after=5)
        await asyncio.sleep(5)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return
        return
    else: await self.error_msg(ctx)

@unload.error
async def unload_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.message.add_reaction("❌")
        await ctx.send(f"""```⚠ {error}
[ℹ] for more information check the console```""")
        await asyncio.sleep(3)
        try: await ctx.message.delete()
        except discord.Forbidden: return
        return

@bot.command()
async def reload(ctx, extension):
    if ctx.message.author.id == 349373972103561218:
        try:
            bot.unload_extension("cogs.{}".format(extension))
        except discord.ext.commands.ExtensionNotLoaded:
            await ctx.send("Cog wasn't loaded, attempting to load", delete_after=5)
        try:
            bot.load_extension("cogs.{}".format(extension))
            await ctx.message.add_reaction("✅")
        except discord.ext.commands.ExtensionAlreadyLoaded:
            await ctx.send("Cog already loaded!", delete_after=5)
        except discord.ext.commands.ExtensionNotFound:
            await ctx.message.add_reaction("❓")
        except discord.ext.commands.NoEntryPointError:
            await ctx.send("Cog doesn't have a setup function!", delete_after=5)
        await asyncio.sleep(5)
        try: await ctx.message.delete()
        except discord.Forbidden: return
        return
    else: await self.error_msg(ctx)

@reload.error
async def reload_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.message.add_reaction("❌")
        await ctx.send(f"""```⚠ {error}
[ℹ] for more information check the console```""")
        await asyncio.sleep(3)
        try: await ctx.message.delete()
        except discord.Forbidden: return
        return
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

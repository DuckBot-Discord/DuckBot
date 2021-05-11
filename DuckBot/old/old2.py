import os
import json
import random
import typing
import discord
import requests
import asyncio
import cleverbotfreeapi
import discord.client
import discord.channel
from random import randint
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext.commands import Bot
from requests.exceptions import RequestException

intents = discord.Intents.default() # Enable all intents except for members and presences
intents.members = True  # Subscribe to the privileged members intent.

def get_prefix(client, message):
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    return prefixes[str(message.guild.id)]

## WORKS
bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, intents=intents)


bot.remove_command("help")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print ("Bot Online!")
    print ("Hello I Am " + bot.user.name)
    print ('-----------')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='.help'))

@bot.command()
@commands.is_owner()
@commands.guild_only()
async def load(ctx, extension):
    if ctx.message.author.id == 349373972103561218:
        bot.load_extension("cogs.{}".format(extension))
        await ctx.message.add_reaction("✅")
        await asyncio.sleep(10)
        await ctx.message.delete()
    else:
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(5)
        await ctx.message.delete()

@load.error
async def load_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.message.add_reaction("❌")
        await asyncio.sleep(10)
        await ctx.message.delete()

@bot.command()
@commands.is_owner()
@commands.guild_only()
async def unload(ctx, extension):
    if ctx.message.author.id == 349373972103561218:
        bot.unload_extension("cogs.{}".format(extension))
        await ctx.message.add_reaction("✅")
        await asyncio.sleep(10)
        await ctx.message.delete()
    else:
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(5)
        await ctx.message.delete()

@unload.error
async def unload_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.message.add_reaction("❌")
        await asyncio.sleep(10)
        await ctx.message.delete()

@bot.command()
@commands.is_owner()
@commands.guild_only()
async def reload(ctx, extension):
    if ctx.message.author.id == 349373972103561218:
        bot.unload_extension("cogs.{}".format(extension))
        bot.load_extension("cogs.{}".format(extension))
        await ctx.message.add_reaction("✅")
        await asyncio.sleep(10)
        await ctx.message.delete()
    else:
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(5)
        await ctx.message.delete()

@reload.error
async def reload_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.message.add_reaction("❌")
        await asyncio.sleep(10)
        await ctx.message.delete()

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        bot.load_extension("cogs.{}".format(filename[:-3]))

####################################
#CUSTOM PREFIX STUFF################
####################################

####### EVENTS #######

@bot.event
async def on_guild_join(guild):
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    prefixes[str(guild.id)] = "."

    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f, indent=4)


@bot.event
async def on_guild_remove(guild):
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    prefixes.pop(str(guild.id))

    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f, indent=4)

@bot.command(aliases=["prefix_change", "set_prefix", "setprefix", "sp"], pass_context=True)
@commands.has_permissions(administrator=True)
async def changeprefix(ctx, *, _prefix):
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    if prefixes[str(ctx.guild.id)] != _prefix:

        prefixes[str(ctx.guild.id)] = _prefix

        with open('prefixes.json', 'w') as f:
            json.dump(prefixes, f, indent=4)

            await ctx.send(f"Prefix set to `{_prefix}`!")
    else:
        await ctx.send(f"That is already the prefix, **{ctx.author.display_name}**.")

@changeprefix.error
async def changeprefix_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(3)
        await ctx.message.delete()

bot.run(TOKEN, reconnect=True)

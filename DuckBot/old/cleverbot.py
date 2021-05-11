import json
import random
import discord
import requests
import cleverbotfreeapi
from random import randint
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    ### CHATBOT ###
    # summons the cleverbot API to hold a conversation for those who have no life

    ###Disabled because it is non-ASYNC and causes issues

    """@commands.command(aliases=['duck', 'db', 'cleverbot', 'r'])
    async def duckbot(self, ctx, *, input):
        response = cleverbotfreeapi.cleverbot(input)
        await ctx.send(response)"""

def setup(bot):
    bot.add_cog(help(bot))

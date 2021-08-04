import json, random, typing, discord, asyncio, yaml, datetime, random
from discord.ext import commands

class events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
        self.yaml_data = full_yaml

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot: return
        if not payload.member.guild: return
        if payload.channel_id != 871109184031178862: return
        

def setup(bot):
    bot.add_cog(events(bot))

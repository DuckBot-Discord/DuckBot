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
        self.bot.get_guild(self.yaml_data['server_id']).get_role(self.yaml_data['staff_role'])
        if not ticket_staff in payload.member.roles: return

        if payload.channel_id != self.yaml_data['log_whitelist']: return

        if str(payload.emoji) == "➕":
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if message.author != message.guild.me or not message.embeds: return
            

def setup(bot):
    bot.add_cog(events(bot))

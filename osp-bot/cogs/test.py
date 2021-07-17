import discord, asyncio, typing, aiohttp, random, json, yaml
from discord.ext import commands, menus

class test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(full_yaml['guildID']).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml

def setup(bot):
    bot.add_cog(test(bot))

import typing, discord, asyncio, yaml
from discord.ext import commands

class promote(commands.Cog):
    """🤖 automated VC-Ban overwrites"""
    def __init__(self, bot):
        self.bot = bot
    #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            yaml_data = yaml.full_load(file)
        self.main_guild = yaml_data['guildID']
        self.vcBanRole = self.bot.get_guild(yaml_data['guildID']).get_role(yaml_data['VcBanRole'])

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if channel.guild.id != self.main_guild: return
        if channel.type is not discord.ChannelType.voice: return
        await channel.set_permissions(self.vcBanRole, connect = False, reason=f'automatic NoVCRole')

def setup(bot):
    bot.add_cog(promote(bot))

import asyncio
import discord
import yaml
from discord.ext import commands


class promote(commands.Cog):
    """🤖 automated VC-Ban overwrites"""

    def __init__(self, bot):
        self.bot = bot
        # ------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            yaml_data = yaml.full_load(file)
        self.main_guild = yaml_data['guildID']
        self.vcBanRole = self.bot.get_guild(yaml_data['guildID']).get_role(yaml_data['VcBanRole'])
        self.MuteRole = self.bot.get_guild(yaml_data['guildID']).get_role(yaml_data['MuteRole'])

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if channel.guild.id != self.main_guild: return
        if channel.type is discord.ChannelType.voice:
            await channel.set_permissions(self.vcBanRole, connect=False, view_channel=False,
                                          reason=f'automatic NoVCRole')
        if channel.type is discord.ChannelType.text:
            await asyncio.sleep(1)
            await channel.set_permissions(self.MuteRole, send_messages=False,
                                          read_messages=False,
                                          add_reactions=False,
                                          reason="Automatic Mute Role")

    @commands.command()
    @commands.is_owner()
    async def fixmuterole(self, ctx):
        for channel in ctx.guild.text_channels:
            if channel.type is discord.ChannelType.text:
                await channel.set_permissions(self.MuteRole, send_messages=False,
                                              read_messages=False,
                                              add_reactions=False,
                                              reason="Automatic Mute Role fix")
                await asyncio.sleep(3)

    @commands.command()
    @commands.is_owner()
    async def fixvcbanrole(self, ctx):
        for channel in ctx.guild.channels:
            if channel.type is discord.ChannelType.voice:
                await channel.set_permissions(self.MuteRole, connect=False,
                                              view_channel=False,
                                              reason="Automatic VC Mute Role fix")
                await asyncio.sleep(3)


def setup(bot):
    bot.add_cog(promote(bot))

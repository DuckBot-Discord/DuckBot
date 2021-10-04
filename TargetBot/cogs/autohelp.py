import aiohttp
import discord
import re
import urllib
import yaml
import yarl
from discord.ext import commands


class automod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            exempt_ids = full_yaml['IgnoredRoles']
            yaml_data = full_yaml
            exempt_roles = []
            for roleid in exempt_ids:
                exempt_roles.append(self.bot.get_guild(yaml_data['guildID']).get_role(roleid))
        self.exempt_roles = exempt_roles
        self.yaml_data = full_yaml
        self.token = full_yaml['sus_url_token']
        self.urlBanRole = self.bot.get_guild(yaml_data['guildID']).get_role(yaml_data['urlBanRole'])

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.guild.id != 717140270789033984:
            return
        if message.channel.permissions_for(message.guild.default_role).send_messages and not \
                message.channel.permissions_for(message.author).manage_messages:
            if any(item in self.exempt_roles for item in message.author.roles):
                return
            if "download" in f"{message.content.lower()}":
                if self.bot.get_guild(717140270789033984).get_role(717144906350592061) in message.author.roles:
                    embed = discord.Embed(title="", description="""I see you're asking about downloads. To access the download channel you need to have a role `Steeler` or higher, but you seem to have the <@&717144906350592061> role.
You can get a `Steeler` or higher subscription here: [patreon.com/stylized](https://www.patreon.com/Stylized).
_if you already have one, unlink and relink your patreon_""", color=message.guild.me.color)
                else:
                    embed = discord.Embed(title="", description="""I see you're asking about downloads. To access the download channel you need to have a role `Steeler` or higher, but you don't seem to have any roles.
If you already purchased a `Steeler` or higher subscription, link your Patreon to Discord. [[more info]](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!)
If your account is already linked, unlink and relink it. [[more info]](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!) about how to get your role.
If you don't already have a `Steeler` or higher subscription, you can get one at [patreon.com/stylized](https://www.patreon.com/Stylized).""",
                                          color=message.guild.me.color)

                embed.set_author(name="Automatic support", icon_url="https://i.imgur.com/GTttbJW.png")
                await message.reply(embed=embed)


def setup(bot):
    bot.add_cog(automod(bot))

import json, random, discord, aiohttp, typing, asyncio, yaml
from random import randint
from discord.ext import commands

class automod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            exempt_ids = full_yaml['ignored_roles']
            exempt_roles = []
            for roleid in exempt_ids:
                exempt_roles.append(self.bot.get_guild(717140270789033984).get_role(roleid))
        self.exempt_roles = exempt_roles
        self.yaml_data = full_yaml

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != 846800131269591091: return
        if message.author.bot or message.guild.id != 717140270789033984: return
        if any(item in self.exempt_roles for item in message.author.roles): return
        if "download" in f"{message.content.lower()}":
            if self.bot.get_guild(717140270789033984).get_role(717144906350592061) in message.author.roles:
                embed=discord.Embed(title="", description="""I see you're asking about downloads. To access the download channel you need to have a role <@&717144765690282015> or higher, but you seem to have the <@&717144906350592061> role.
If you already purchased a <@&717144765690282015> subscription, check [this article](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!) about how to get your role.
If you don't already have a <@&717144765690282015> or higher subscription, you can get one here: [patreon.com/stylized](https://www.patreon.com/Stylized).""", color=message.guild.me.color)
            else:
                embed=discord.Embed(title="", description="""I see you're asking about downloads. To access the download channel you need to have a role <@&717144765690282015> or higher, but you don't seem to have any roles.
If you already purchased a <@&717144765690282015> or higher subscription, check [this article](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!) about how to get your role.
If you don't already have a <@&717144765690282015> or higher subscription, you can get one here: [patreon.com/stylized](https://www.patreon.com/Stylized).""", color=message.guild.me.color)
            embed.set_author(name="Automatic support", icon_url="https://i.imgur.com/GTttbJW.png")
            embed.set_footer(text="this message will delete in 2 minutes")
            await message.channel.send(embed=embed, delete_after=120)
            await message.add_reaction('📩')

def setup(bot):
    bot.add_cog(automod(bot))

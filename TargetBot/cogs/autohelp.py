import json, random, discord, aiohttp, typing, asyncio, yaml, re, urllib, yarl
from random import randint
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

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != 853437050313113600: return
        if message.author.bot: return
        original_message = message.content
        results = re.findall("http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", message.content)
        if results:
            await message.add_reaction('🔃')
            text = message.content
            is_sus = False
            for link in results:
                if urllib.parse.urlparse(link).netloc in self.yaml_data['safe_urls']: continue
                url = urllib.parse.quote(link, safe='')
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(yarl.URL(f"https://ipqualityscore.com/api/json/url/{self.token}/{url}",encoded=True)) as r:
                        data = await r.json()
                        if data['risk_score'] >= 15:
                            text = text.replace(link, "`SUS_LINK`")
                            is_sus = True
            if is_sus == True:
                await message.delete()
                embed = discord.Embed(description=text, color = 0x2F3136)
                embed.set_author(name=message.author, icon_url=message.author.avatar_url)
                await message.channel.send(f"message by {message.author.mention} had a sus link", embed=embed)

                regembed = discord.Embed(description=original_message, color = 0x2F3136)
                regembed.set_author(name=message.author, icon_url=message.author.avatar_url)
                await self.bot.get_channel(757127270874742827).send(f"message by {message.author.mention} had a sus link",embed=regembed)
                return
            else:
                await message.remove_reaction('🔃', self.bot.user)
                await message.add_reaction('✅')

        if any(item in self.exempt_roles for item in message.author.roles): return
        if "download" in f"{message.content.lower()}":
            if self.bot.get_guild(717140270789033984).get_role(717144906350592061) in message.author.roles:
                embed=discord.Embed(title="", description="""I see you're asking about downloads. To access the download channel you need to have a role <@&717144765690282015> or higher, but you seem to have the <@&717144906350592061> role.

You can get a <@&717144765690282015> or higher subscription here: [patreon.com/stylized](https://www.patreon.com/Stylized).
_if you already have one, unlink and relink your patreon_""", color=message.guild.me.color)
            else:
                embed=discord.Embed(title="", description="""I see you're asking about downloads. To access the download channel you need to have a role <@&717144765690282015> or higher, but you don't seem to have any roles.

If you already purchased a <@&717144765690282015> or higher subscription, link your Patreon to Discord. [[more info]](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!)
If your account is already linked, unlink and relink it. [[more info]](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!) about how to get your role.

If you don't already have a <@&717144765690282015> or higher subscription, you can get one at [patreon.com/stylized](https://www.patreon.com/Stylized).""", color=message.guild.me.color)
            embed.set_author(name="Automatic support", icon_url="https://i.imgur.com/GTttbJW.png")
            await message.channel.send(embed=embed)

def setup(bot):
    bot.add_cog(automod(bot))

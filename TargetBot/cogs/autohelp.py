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
        self.urlBanRole = self.bot.get_guild(yaml_data['guildID']).get_role(yaml_data['urlBanRole'])

    @commands.command(aliases=['test'])
    async def urltest(self, ctx, *, url):
        results = re.findall("http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", url)
        if not results:
            await ctx.send('no results found')
            return
        await ctx.message.add_reaction('🔃')
        for link in results:
            url = urllib.parse.quote(link, safe='')
            async with aiohttp.ClientSession() as cs:
                async with cs.get(yarl.URL(f"https://ipqualityscore.com/api/json/url/{self.token}/{url}",encoded=True)) as r:
                    text = await r.json()
                    await ctx.send(text)

        await ctx.message.remove_reaction('🔃', self.bot.user)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.guild.id != 717140270789033984: return
        if self.bot.get_guild(self.yaml_data['guildID']).get_role(self.yaml_data['StaffRole']) in message.author.roles:
            if not "--test" in message.content.lower():
                return
        original_message = message.content
        results = re.findall("http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", message.content)
        if results:
            await message.add_reaction('🔃')
            text = message.content
            is_sus = False
            is_very_sus = False
            spamming = False
            malware = False
            phishing = False
            adult = False
            risk_factor = 0
            sus_links = 0

            for link in results:
                if urllib.parse.urlparse(link).netloc in self.yaml_data['safe_urls']: continue
                if self.urlBanRole in message.author.roles:
                    await message.delete()
                    await message.author.send('You''re not allowed to send URLs that aren''t whitelisted!')
                    await self.bot.get_channel(757127270874742827).send(f"User {message.author.mention} is in <@&859841694169432124> and sent `{link}`, which is not whitelisted.")
                    return
                url = urllib.parse.quote(link, safe='')
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(yarl.URL(f"https://ipqualityscore.com/api/json/url/{self.token}/{url}",encoded=True)) as r:
                        data = await r.json()
                        if data['risk_score'] >= 35:
                            text = text.replace(link, "<:sus:853491206550061056>")
                            is_sus = True
                        if data['risk_score'] >= 90: is_very_sus = True
                        if data['spamming'] == True: spamming = True
                        if data['malware'] == True: malware = True
                        if data['phishing'] == True: phishing=True
                        if data['adult'] == True: adult=True
                        risk_factor = risk_factor + data['risk_score']
                        sus_links = sus_links + 1

            if is_sus == True:
                await message.delete()
                embed = discord.Embed(description=text, color = 0x2F3136)
                embed.set_author(name=message.author, icon_url=message.author.avatar_url)
                flagged_with = ""
                if spamming == True: flagged_with = flagged_with + " spamming,"
                if malware == True: flagged_with = flagged_with + " malware,"
                if phishing == True: flagged_with = flagged_with + " phishing,"
                if adult == True: flagged_with = flagged_with + " nsfw,"
                if flagged_with.endswith(','): flagged_with[:-2]
                if flagged_with != "":
                    embed.set_footer(text=f'Flagged with{flagged_with}')
                await message.channel.send(f"message by {message.author.mention} had a <:sus:853491206550061056> link", embed=embed)

                regembed = discord.Embed(description=original_message, color = 0x2F3136)
                regembed.set_author(name=message.author, icon_url=message.author.avatar_url)
                if is_very_sus == True: regembed.set_footer(text=f"""deemed very sus, user has been muted! | ID: {message.author.id}
dismiss case:
!unmute {message.author.id} case dismissed. link was not suspicious""")
                else: regembed.set_footer(text=f"ID: {message.author.id}")
                await self.bot.get_channel(757127270874742827).send(f"message by {message.author.mention} had a <:sus:853491206550061056> link",embed=regembed)
                if is_very_sus == True:
                    muterole = message.guild.get_role(self.yaml_data['MuteRole'])
                    if not muterole in message.author.roles:
                        await message.author.add_roles(muterole)
                        mem_embed=discord.Embed(color=message.guild.me.color)
                        mem_embed.set_author(name=f"You've been muted by our automated URL scanning systems", icon_url='https://i.imgur.com/hKNGsMb.png')
                        mem_embed.set_image(url='https://i.imgur.com/hXbvCT4.png')
                        mem_embed.set_footer(text=f'reason: our systems have detected that you have sent a suspicious link - human moderators will check your case soon and take further actions')
                        await message.author.send(embed=mem_embed)
                return

            else:
                await message.remove_reaction('🔃', self.bot.user)
                await message.add_reaction('✅')
                await asyncio.sleep(5)
                await message.remove_reaction('✅', self.bot.user)


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

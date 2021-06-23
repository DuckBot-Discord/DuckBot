import typing, discord, asyncio, random, datetime, json, aiohttp, re
from discord.ext import commands, tasks, timers
from random import randint

class text_commands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # all the emoji are from the bots.gg discord server.
    # If your bot is in there, it'll be able to use them
    def get_user_badges(self, user):
        author_flags = user.public_flags
        flags = dict(author_flags)
        emoji_flags = ""
        if flags['staff'] is True:
            emoji_flags = f"{emoji_flags} <:staff:314068430787706880>"
        if flags['partner'] is True:
            emoji_flags = f"{emoji_flags} <:partnernew:754032603081998336>"
        if flags['hypesquad'] is True:
            emoji_flags = f"{emoji_flags} <:hypesquad:314068430854684672>"
        if flags['bug_hunter'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter:585765206769139723>"
        if flags['hypesquad_bravery'] is True:
            emoji_flags = f"{emoji_flags} <:bravery:585763004218343426>"
        if flags['hypesquad_brilliance'] is True:
            emoji_flags = f"{emoji_flags} <:brilliance:585763004495298575>"
        if flags['hypesquad_balance'] is True:
            emoji_flags = f"{emoji_flags} <:balance:585763004574859273>"
        if flags['early_supporter'] is True:
            emoji_flags = f"{emoji_flags} <:supporter:585763690868113455>"
        if user.premium_since:
            emoji_flags = f"{emoji_flags} <:booster4:585764446178246657>"
        if flags['bug_hunter_level_2'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter_gold:850843414953984041>" #not from bots.gg
        if flags['verified_bot_developer'] is True:
            emoji_flags = f"{emoji_flags} <:earlybotdev:850843591756349450>" #not from bots.gg
        if emoji_flags == "": emoji_flags = None
        return emoji_flags

    ##### .s <text> #####
    # resends the message as the bot

    @commands.command(aliases=['say', 'send'])
    @commands.has_permissions(manage_messages=True)
    async def s(self, ctx, *, message):
        msg=message
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        if ctx.channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg)
            else:
                await ctx.send(msg)
        else:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg, allowed_mentions = discord.AllowedMentions(everyone = False))
            else:
                await ctx.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    ##### .a <TextChannel> <text> ######
    #sends the message in a channel

    @commands.command(aliases=['a', 'an'])
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, msg = "no content"):
        if channel == None:
            await ctx.send("""You must specify a channel
`.announce #channel/ID Message`""")
            return
        if channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                msg = ctx.message.reference.resolved.content
            await channel.send(msg)

        else:
            if ctx.message.reference:
                msg = ctx.message.reference.resolved.content
            await channel.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    @commands.command(aliases=['e'])
    @commands.is_owner()
    async def edit(self, ctx, *, new_message : typing.Optional[str] = '--d'):
        new = new_message
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            try:
                if new.endswith("--s"): await msg.edit(content="{}".format(new[:-3]), suppress=True)
                elif new.endswith('--d'): await msg.delete()
                else: await msg.edit(content=new, suppress=False)
                try: await ctx.message.delete()
                except discord.Forbidden:
                    return
            except: pass
        else:
            await ctx.message.add_reaction('⚠')
            await asyncio.sleep(3)
            try: await ctx.message.delete()
            except discord.Forbidden: return

    #### .jumbo <Emoji> ####
    # makes emoji go big

    @commands.command(aliases=['jumbo'])
    async def emoji(self, ctx, emoji: discord.PartialEmoji):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_image(url = emoji.url)
        await ctx.send(embed=embed)

    #### .uinfo {user} ####
    # gives user info

    @commands.command(aliases = ['userinfo'])
    async def uinfo(self, ctx, user: typing.Optional[discord.Member]):
        if not user: user = ctx.author
        # BADGES
        badges = self.get_user_badges(user)
        if badges: badges = f"\n<:store_tag:658538492409806849>**Badges:**{badges}"
        else: badges = ''
        # USERID
        userid = f"\n<:greyTick:596576672900186113>**ID:** `{user.id}`"
        # NICKNAME
        if user.nick: nick = f"\n<:nickname:850914031953903626>**Nickname:** `{user.nick}`"
        else: nick = ""
        # CREATION DATE
        date = user.created_at.strftime("%b %-d %Y at %-H:%M")
        created = f"\n<:invite:658538493949116428>**Created:** `{date} UTC`"
        # JOIN DATE
        if user.joined_at:
            date = user.joined_at.strftime("%b %-d %Y at %-H:%M")
            joined = f"\n<:joined:849392863557189633>**joined:** `{date} UTC`"
        else: joined = ""
        # GUILD OWNER
        if user is ctx.guild.owner:
            owner = f"\n<:owner:585789630800986114>**Owner:** <:check:314349398811475968>"
        else: owner = ""
        # BOT
        if user.bot:
            bot = f"\n<:botTag:230105988211015680>**Bot:** <:check:314349398811475968>"
        else: bot = ""
        # BOOSTER SINCE
        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else: boost = ""
        # ROLES
        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role: continue
            roles = f"{roles} {role.mention}"
        if roles != "":
            roles = f"\n<:role:808826577785716756>**roles:** {roles}"
        # EMBED
        embed = discord.Embed(color=ctx.me.color, description=f"""{badges}{owner}{bot}{userid}{created}{nick}{joined}{boost}{roles}""")
        embed.set_author(name=user, icon_url=user.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        await ctx.send(embed=embed)

    #### .uuid <mcname> ####
    # gets user's UUID (minecraft)

    @commands.command()
    async def uuid(self, ctx, *, argument: typing.Optional[str] = None):
        if argument == None:
            embed = discord.Embed(description= "please specify a Minecraft Username to look up", color = ctx.me.color)
            await ctx.send(embed=embed)
            return
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                embed = discord.Embed(color = ctx.me.color)
                if cs.status == 204:
                    embed.add_field(name='⚠ ERROR ⚠', value=f"`{argument}` is not a minecraft username!")

                elif cs.status == 400:
                    embed.add_field(name="⛔ ERROR ⛔", value="ERROR 400! Bad request.")
                else:
                    res = await cs.json()
                    user = res["name"]
                    uuid = res["id"]
                    embed.add_field(name=f'Minecraft username: `{user}`', value=f"**UUID:** `{uuid}`")
                await ctx.send(embed=embed)

    @commands.command()
    async def tias(self, ctx):
        try: await ctx.message.delete()
        except: pass
        await ctx.send("https://tryitands.ee/")

    @commands.command(aliases=['inspirobot', 'imageinspire', 'inspirame'])
    async def inspireme(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('http://inspirobot.me/api?generate=true') as r:
                res = await r.text()
                embed = discord.Embed(title='An inspirational image...', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res)
                embed.set_footer(text='by inspirobot.me', icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
                await ctx.send(embed=embed)

    @commands.command(aliases=['inspirequote', 'quote', 'inspire', 'motivateme'])
    async def motivate(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get("https://www.affirmations.dev") as r:
                json_data = await r.json()  
                await ctx.send(json_data["affirmation"])

    @commands.command()
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def afk(self, ctx):
        nick = f'{ctx.author.nick}'
        if nick == 'None':
            nick = f'{ctx.author.name}'
        else:
            nick = nick
        if nick.startswith("[AFK] "):
            try:
                await ctx.author.edit(nick=nick.replace('[AFK] ', ''))
                await ctx.send(f'{ctx.author.mention}, **You are no longer afk**', delete_after=4)
            except discord.Forbidden:
                await ctx.message.add_reaction('⚠')
                return
            await ctx.message.delete()
        else:
            try:
                await ctx.author.edit(nick=f'[AFK] {nick}')
            except discord.Forbidden:
                await ctx.message.add_reaction('⚠')
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('⚠')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
                return
            await ctx.send(f'{ctx.author.mention}, **You are afk**', delete_after=4)
            await ctx.message.delete()

#-------------------------------------------------------------------------#
#------------------------ ANIMALS AND STUFF ------------------------------#
#-------------------------------------------------------------------------#

    ### CAT ###
    # Sends a pic of a cat
    @commands.command(aliases=['meow', 'kitty', 'getcat'])
    async def cat(self, ctx, cat: typing.Optional[str], id:typing.Optional[int]):
        async with aiohttp.ClientSession() as cs:
            if cat == None:
                async with cs.get('https://aws.random.cat/meow') as r:
                    res = await r.json()  # returns dict
                    embed = discord.Embed(title='Here is a cat!', color=random.randint(0, 0xFFFFFF))
                    embed.set_image(url=res["file"])
                    embed.set_footer(text='by random.cat', icon_url='https://purr.objects-us-east-1.dream.io/static/img/random.cat-logo.png')
                    await ctx.send(embed=embed)
            #MANCHAS ======================
            elif cat.lower() == "manchas":
                embed = discord.Embed(title='Here is Manchas!', color=random.randint(0, 0xFFFFFF))
                if id == None:
                    async with cs.get('https://api.manchas.cat/', allow_redirects=True) as cs:
                        url = cs.url
                        embed.set_image(url=url)
                        manchas_id = str(url).split('/')[-1]
                        embed.set_footer(text=f'by api.manchas.cat | ID: {manchas_id}')
                else:
                    async with cs.get(f'https://api.manchas.cat/{id}', allow_redirects=True) as cs:
                        if cs.status == 404:
                            await ctx.send("⚠ Manchas not found", delete_after=5)
                            await asyncio.sleep(5)
                            try:
                                await ctx.message.delete()
                            except discord.forbidden:
                                return
                            return
                    embed.set_image(url=f'https://api.manchas.cat/{id}')
                    embed.set_footer(text=f'by api.manchas.cat | ID: {id}')
                await ctx.send(embed=embed)
            #RORY ==========================
            elif cat.lower() == "rory":
                if id == None:
                    async with cs.get('https://rory.cat/purr') as r:
                        res = await r.json()  # returns dict
                        embed = discord.Embed(title='Here is a Rory!', color=random.randint(0, 0xFFFFFF))
                        embed.set_image(url=res["url"])
                        embed.set_footer(text=f'by rory.cat | ID: {res["id"]}')
                        await ctx.send(embed=embed)
                else:
                    async with cs.get(f'https://rory.cat/purr/{id}') as r:
                        if r.status == 404:
                            await ctx.send("⚠ Rory not found", delete_after=5)
                            await asyncio.sleep(5)
                            try:
                                await ctx.message.delete()
                            except discord.forbidden:
                                return
                            return
                        res = await r.json()  # returns dict
                        embed = discord.Embed(title='Here is a Rory!', color=random.randint(0, 0xFFFFFF))
                        embed.set_image(url=res["url"])
                        embed.set_footer(text=f'by rory.cat | ID: {res["id"]}')
                        await ctx.send(embed=embed)
            elif cat.lower() == 'help':
                embed = discord.Embed(title='Cat help', description="fields: `.cat <cat> <id>`", color=random.randint(0, 0xFFFFFF))
                embed.add_field(name=".cat", value="Gets a totally random cat", inline=False)
                embed.add_field(name=".cat Rory <id>", value="gets a Rory - ID is optional to get a specific Rory image", inline=False)
                embed.add_field(name=".cat Manchas <id>", value="gets a Manchas - ID is optional to get a specific Manchas image", inline=False)
                await ctx.send(embed=embed)
            else:
                async with cs.get('https://aws.random.cat/meow') as r:
                    res = await r.json()  # returns dict
                    embed = discord.Embed(title='Here is a cat!', color=random.randint(0, 0xFFFFFF))
                    embed.set_image(url=res["file"])
                    embed.set_footer(text='by random.cat', icon_url='https://purr.objects-us-east-1.dream.io/static/img/random.cat-logo.png')
                    await ctx.send(embed=embed)

    @commands.command(aliases=['dog', 'pup', 'getdog'])
    async def doggo(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://dog.ceo/api/breeds/image/random') as r:
                res = await r.json()  # returns dict
                embed = discord.Embed(title='Here is a dog!', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res["message"])
                embed.set_footer(text='by dog.ceo', icon_url='https://i.imgur.com/wJSeh2G.png')
                await ctx.send(embed=embed)

    @commands.command(aliases=['getduck', 'quack', 'randomduck'])
    async def duck(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://random-d.uk/api/random?format=json') as r:
                res = await r.json()  # returns dict
                embed = discord.Embed(title='Here is a duck!', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res["url"])
                embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
                await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(text_commands(bot))

import json, random, discord, aiohttp, typing, asyncio, cleverbotfreeapi

from random import randint
from discord.ext import commands


class animals(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['inspirequote', 'quote', 'inspire', 'motivateme'])
    async def motivate(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get("https://www.affirmations.dev") as r:
                json_data = json.loads(r.text)
                await ctx.send(json_data["affirmation"])

    @commands.command()
    async def duckbot(self, ctx, *, input):
        response = cleverbotfreeapi.cleverbot(input)
        await ctx.send(response)

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

    @commands.command(aliases=['inspirobot', 'imageinspire', 'inspirame'])
    async def inspireme(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('http://inspirobot.me/api?generate=true') as r:
                res = await r.text()
                embed = discord.Embed(title='An inspirational image...', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res)
                embed.set_footer(text='by inspirobot.me', icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
                await ctx.send(embed=embed)

    @commands.command()
    async def tias(self, ctx):
        try: await ctx.message.delete()
        except: pass
        await ctx.send("https://tryitands.ee/")

def setup(bot):
    bot.add_cog(animals(bot))

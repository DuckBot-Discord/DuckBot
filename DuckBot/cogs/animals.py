import typing, discord, asyncio, random, datetime, json, aiohttp, re
from discord.ext import commands, tasks, timers
from random import randint

class fun(commands.Cog):
    """🤪 Fun commands!"""
    def __init__(self, bot):
        self.bot = bot

    ### CAT ###
    # Sends a pic of a cat
    @commands.command(  help="Sends a random cat image\nIf specified, can also send a random or specific picture of Manchas or Rory",
                        usage="[rory|manchas] [specific ID]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
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

    @commands.command(help="Sends a random dog image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://dog.ceo/api/breeds/image/random') as r:
                res = await r.json()  # returns dict
                embed = discord.Embed(title='Here is a dog!', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res["message"])
                embed.set_footer(text='by dog.ceo', icon_url='https://i.imgur.com/wJSeh2G.png')
                await ctx.send(embed=embed)

    @commands.command(help="Sends a random duck image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://random-d.uk/api/random?format=json') as r:
                res = await r.json()  # returns dict
                embed = discord.Embed(title='Here is a duck!', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res["url"])
                embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
                await ctx.send(embed=embed)

    @commands.command(help="Try it and see...")
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx):
        try: await ctx.message.delete()
        except: pass
        await ctx.send("https://tryitands.ee/")

    @commands.command(help="shows a funny \"inspirational\" image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('http://inspirobot.me/api?generate=true') as r:
                res = await r.text()
                embed = discord.Embed(title='An inspirational image...', color=random.randint(0, 0xFFFFFF))
                embed.set_image(url=res)
                embed.set_footer(text='by inspirobot.me', icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
                await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(fun(bot))

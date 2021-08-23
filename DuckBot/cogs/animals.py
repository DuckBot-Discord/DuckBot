import random
from typing import (
    Optional
)

import discord
from discord.ext import commands


def setup(bot):
    bot.add_cog(Fun(bot))


class Fun(commands.Cog, name='Fun'):
    """
    🤪 Fun commands!
    """

    __slots__ = ('bot',)

    def __init__(self, bot):
        self.bot = bot

    ### CAT ###
    # Sends a pic of a cat
    @commands.group(usage="[rory|manchas] [specific ID]", invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: commands.Context) -> Optional[discord.Message]:
        """
        Sends a random cat image\nIf specified, can also send a random or specific picture of Manchas or Rory
        """
        if ctx.invoked_subcommand:
            return

        async with self.bot.session.get('https://aws.random.cat/meow') as r:
            res = await r.json()  # returns dict

        embed = discord.Embed(title='Here is a cat!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["file"])
        embed.set_footer(text='by random.cat',
                         icon_url='https://purr.objects-us-east-1.dream.io/static/img/random.cat-logo.png')
        return await ctx.send(embed=embed)

    @cat.command(
        name='rory',
        brief='View rory')
    async def cat_rory(self, ctx: commands.Context, id: Optional[int]) -> Optional[discord.Message]:
        embed = discord.Embed(title='Here is Rory!', color=random.randint(0, 0xFFFFFF))
        url = 'https://rory.cat/purr'
        url += id if id else ''

        async with self.bot.session(url, allow_redirects=True) as cs:
            res = await cs.json()
            if not id:
                url = cs.url
                embed.set_image(url=url)
                manchas_id = str(url).split('/')[-1]
                embed.set_footer(text=f'by rory.cat | ID: {res["id"]}')
            elif cs.setstatus == 404:
                await ctx.message.delete(delay=5)
                return await ctx.send("⚠ Manchas not found", delete_after=5)

        embed.set_image(url=url)
        embed.set_footer(text=f'by rory.cat | ID: {res["id"]}')
        return await ctx.send(embed=embed)

    @cat.command(
        name='manchas',
        brief='View manchas')
    async def cat_manchas(self, ctx: commands.Context, id: Optional[int]) -> Optional[discord.Message]:
        embed = discord.Embed(title=f'Here is {ctx.command}!', color=random.randint(0, 0xFFFFFF))
        url = 'https://api.manchas.cat/'
        url += id if id else ''

        async with self.bot.session(url, allow_redirects=True) as cs:
            if not id:
                url = cs.url
                embed.set_image(url=url)
                manchas_id = str(url).split('/')[-1]
                embed.set_footer(text=f'by api.manchas.cat | ID: {manchas_id}')
            else:
                if cs.setstatus == 404:
                    await ctx.send("⚠ Manchas not found", delete_after=5)
                    try:
                        await ctx.message.delete()
                    except discord.forbidden:
                        return
                    finally:
                        return
            embed.set_image(url=f'https://api.manchas.cat/{id}')
            embed.set_footer(text=f'by api.manchas.cat | ID: {id}')
        return await ctx.send(embed=embed)

    @commands.command(help="Sends a random dog image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: commands.Context) -> discord.Message:
        async with self.bot.session('https://dog.ceo/api/breeds/image/random') as r:
            res = await r.json()

        embed = discord.Embed(title='Here is a dog!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["message"])
        embed.set_footer(text='by dog.ceo', icon_url='https://i.imgur.com/wJSeh2G.png')
        return await ctx.send(embed=embed)

    @commands.command(help="Sends a random duck image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx: commands.Context) -> discord.Message:
        async with self.bot.session('https://random-d.uk/api/random?format=json') as r:
            res = await r.json()

        embed = discord.Embed(title='Here is a duck!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["url"])
        embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
        return await ctx.send(embed=embed)

    @commands.command(help="Try it and see...")
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx: commands.Context) -> discord.Message:
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await ctx.message.delete()

        return await ctx.send("https://tryitands.ee/")

    @commands.command(help="shows a funny \"inspirational\" image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx) -> discord.Message:
        async with self.bot.session('http://inspirobot.me/api?generate=true') as r:
            res = await r.text()

        embed = discord.Embed(title='An inspirational image...', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res)
        embed.set_footer(text='by inspirobot.me',
                         icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
        return await ctx.send(embed=embed)

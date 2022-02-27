import random
import urllib.parse

import aiohttp
import aiowiki
import discord
from discord.ext import commands

from ._base import FunBase
from ...helpers.context import CustomContext
from ...helpers.paginator import ViewPaginator, UrbanPageSource


class Apis(FunBase):
    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random duck image from random-d.uk
        """
        async with self.bot.session.get('https://random-d.uk/api/random?format=json') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.json()

        embed = discord.Embed(title='Here is a duck!',
                              color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["url"])
        embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
        return await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx: CustomContext) -> discord.Message:
        """
        shows a funny "inspirational" image from inspirobot.me
        """
        async with self.bot.session.get('https://inspirobot.me/api?generate=true') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.text()

        embed = discord.Embed(title='An inspirational image...',
                              color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res)
        embed.set_footer(text='by inspirobot.me',
                         icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
        return await ctx.send(embed=embed)

    @commands.command(name='urban', aliases=['ud'])
    async def _urban(self, ctx, *, word):
        """Searches urban dictionary."""

        url = 'https://api.urbandictionary.com/v0/define'
        async with self.bot.session.get(url, params={'term': word}) as resp:
            if resp.status != 200:
                return await ctx.send(f'An error occurred: {resp.status} {resp.reason}')

            js = await resp.json()
            data = js.get('list', [])
            if not data:
                return await ctx.send('No results found, sorry.')

        pages = ViewPaginator(UrbanPageSource(data), ctx=ctx)
        await pages.start()

    @commands.command(name='achievement')
    async def minecraft_achievement(self, ctx: CustomContext, *, text: commands.clean_content):
        text = urllib.parse.quote(str(text))
        await ctx.trigger_typing()
        try:
            async with self.bot.session.get(f'https://api.cool-img-api.ml/achievement?text={text}',
                                            allow_redirects=True) as r:
                return await ctx.send(r.url)
        except aiohttp.ClientConnectionError:
            raise commands.BadArgument('Failed to connect to the API. Try again later?')

    @commands.command(aliases=['wiki'])
    async def wikipedia(self, ctx, *, search: str):
        """ Searches on wikipedia, and shows the 10 best returns """
        async with ctx.typing():
            async with aiowiki.Wiki.wikipedia('en') as w:
                hyperlinked_titles = [f"[{p.title}]({(await p.urls()).view})" for p in (await w.opensearch(search))]

            iterations = 1
            enumerated_titles = []
            for title_hyperlink in hyperlinked_titles:
                enumerated_titles.append(f"{iterations}) {title_hyperlink}")
                iterations += 1

            embed = discord.Embed(description='\n'.join(enumerated_titles),
                                  colour=discord.Colour.random())
            embed.set_author(icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/8/80/"
                                      "Wikipedia-logo-v2.svg/512px-Wikipedia-logo-v2.svg.png",
                             name="Here are the top 10 Wikipedia results:",
                             url="https://en.wikipedia.org/")
            return await ctx.send(embed=embed)


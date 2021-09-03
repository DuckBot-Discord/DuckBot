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

    # CAT
    # Sends a pic of a cat
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: commands.Context) -> Optional[discord.Message]:
        """
        Sends a random cat image
        """

        async with self.bot.session.get('https://aws.random.cat/meow') as r:
            if r.status != 200:
                return await ctx.send("Something broke with the shitty ass cat api."
                                      "\nIll migrate to r/cats soon...TM")
            res = await r.json()  # returns dict

        embed = discord.Embed(title='Here is a cat!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["file"])
        embed.set_footer(text='by random.cat',
                         icon_url='https://purr.objects-us-east-1.dream.io/static/img/random.cat-logo.png')
        return await ctx.send(embed=embed)

    @commands.command(help="Sends a random dog image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: commands.Context) -> discord.Message:
        async with self.bot.session.get('https://dog.ceo/api/breeds/image/random') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.json()

        embed = discord.Embed(title='Here is a dog!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["message"])
        embed.set_footer(text='by dog.ceo', icon_url='https://i.imgur.com/wJSeh2G.png')
        return await ctx.send(embed=embed)

    @commands.command(help="Sends a random duck image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx: commands.Context) -> discord.Message:
        async with self.bot.session.get('https://random-d.uk/api/random?format=json') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.json()

        embed = discord.Embed(title='Here is a duck!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["url"])
        embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
        return await ctx.send(embed=embed)

    @commands.command(help="Try it and see...")
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx: commands.Context) -> discord.Message:
        return await ctx.send("https://tryitands.ee/")

    @commands.command(help="shows a funny \"inspirational\" image")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx) -> discord.Message:
        async with self.bot.session.get('http://inspirobot.me/api?generate=true') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.text()

        embed = discord.Embed(title='An inspirational image...', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res)
        embed.set_footer(text='by inspirobot.me',
                         icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
        return await ctx.send(embed=embed)

    @commands.command()
    async def banana(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        size = random.uniform(8, 25)
        embed = discord.Embed(colour=0xFFCD71)
        embed.description = f"""
                             8{'=' * int(round(size / 2, 0))}D

                             **{member.name}**'s 🍌 is {round(size, 1)} cm
                             """
        embed.set_author(icon_url=member.display_avatar.url, name=member)
        await ctx.send(embed=embed)

    @commands.command()
    async def meme(self, ctx):
        meme = await (await self.bot.reddit.subreddit("memes")).random()
        embed = discord.Embed(color=discord.Color.random(), title=meme.title,
                              description=f"<:upvote:274492025678856192> {meme.score} "
                                          f"({meme.upvote_ratio * 100}%)",
                              url=f"https://reddit.com{meme.permalink}")
        embed.set_image(url=meme.url)
        await ctx.send(embed=embed)

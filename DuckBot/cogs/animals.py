import random
from typing import (
    Optional
)

import discord
from discord.ext import commands

_8ball_good = ['It is certain',
               'It is decidedly so',
               'Without a doubt',
               'Yes - definitely',
               'You may rely on it',
               'As I see it, yes',
               'Most likely',
               'Outlook good',
               'Yes',
               'Signs point to yes']

_8ball_meh = ['Reply hazy, try again',
              'Ask again later',
              'Better not tell you now',
              'Cannot predict now',
              'Concentrate and ask again']

_8ball_bad = ['Don\'t count on it',
              'My reply is no',
              'My sources say no',
              'Outlook not so good',
              'Very doubtful']

_8ball_answers = _8ball_good + _8ball_meh + _8ball_bad


def setup(bot):
    bot.add_cog(Fun(bot))


class Fun(commands.Cog, name='Fun'):
    """
    🤪 Fun commands!
    """

    __slots__ = ('bot',)

    def __init__(self, bot):
        self.bot = bot

    async def reddit(self, subreddit: str) -> discord.Embed:
        post = await (await self.bot.reddit.subreddit(subreddit)).random()

        while 'i.redd.it' not in post.url:
            post = await (await self.bot.reddit.subreddit(subreddit)).random()

        embed = discord.Embed(color=discord.Color.random(),
                              description=f"[{post.title}](https://reddit.com{post.permalink})"
                                          f"\n<:upvote:274492025678856192> {post.score} "
                                          f"({post.upvote_ratio * 100}%)")
        embed.set_image(url=post.url)
        return embed

    # CAT
    # Sends a pic of a cat
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: commands.Context) -> Optional[discord.Message]:
        """ Sends a random cat image """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('cats'))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: commands.Context) -> discord.Message:
        """ Sends a random dog image """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('dog'))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx: commands.Context) -> discord.Message:
        """
        Sends a random duck image
        """
        async with self.bot.session.get('https://random-d.uk/api/random?format=json') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.json()

        embed = discord.Embed(title='Here is a duck!', color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["url"])
        embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
        return await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx: commands.Context) -> discord.Message:
        """
        Try it and see...
        """
        return await ctx.send("https://tryitands.ee/")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx) -> discord.Message:
        """
        shows a funny "inspirational" image from inspirobot.me
        """
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
        """
        Measures your banana 😏
        """
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
        """
        Sends a random meme from reddit.com/r/memes.
        """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('memes'))

    @commands.command(name="8ball")
    async def _8ball(self, ctx, *, question):
        """
        Vaguely answers your question.
        """
        return await ctx.send(f"Q: {question[0:1800]}"
                              f"\nA: {random.choice(_8ball_answers)}")

    @commands.command()
    async def choose(self, ctx: commands.Context, *choices: str):
        """
        Chooses one random word from the list of choices you input.
        If you want multi-word choices, use "Quotes for it" "Like so"
        """
        if len(choices) < 2:
            return await ctx.send("You must input at least 2 choices")
        return await ctx.send(random.choice(choices))
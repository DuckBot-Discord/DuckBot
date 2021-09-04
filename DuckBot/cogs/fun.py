import asyncio
import random

import aiowiki as aiowiki
import discord
import typing
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

    async def reddit(self, subreddit: str, title: bool = True) -> discord.Embed:
        post = await (await self.bot.reddit.subreddit(subreddit)).random()

        while 'i.redd.it' not in post.url or post.over_18:
            post = await (await self.bot.reddit.subreddit(subreddit)).random()

        embed = discord.Embed(color=discord.Color.random(),
                              description=f"🌐 [Original reddit post](https://reddit.com{post.permalink}) | "
                                          f"<:upvote:274492025678856192> {post.score} "
                                          f"({post.upvote_ratio * 100}%)")
        embed.title = post.title if title is True else None
        embed.set_image(url=post.url)
        return embed

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: commands.Context) -> discord.Message:
        """ Sends a random cat image from r/cats """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('cats'))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: commands.Context) -> discord.Message:
        """ Sends a random dog image from r/dog """
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
    async def inspireme(self, ctx: commands.Context) -> discord.Message:
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
    async def banana(self, ctx: commands.Context, member: discord.Member = None) -> discord.Message:
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
        return await ctx.send(embed=embed)

    @commands.command()
    async def meme(self, ctx: commands.Context) -> discord.Message:
        """
        Sends a random meme from reddit.com/r/memes.
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit('memes'))

    @commands.command()
    async def aww(self, ctx: commands.Context) -> discord.Message:
        """
        Sends cute pic from r/aww
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit('aww'))

    @commands.command(name="8ball")
    async def _8ball(self, ctx: commands.Context, *, question: str) -> discord.Message:
        """
        Vaguely answers your question.
        """
        async with ctx.typing():
            await asyncio.sleep(0.5)
            return await ctx.send(f"**Q: {question[0:1800]}**"
                                  f"\nA: {random.choice(_8ball_answers)}")

    @commands.command()
    async def choose(self, ctx: commands.Context, *choices: str) -> discord.Message:
        """
        Chooses one random word from the list of choices you input.
        If you want multi-word choices, use "Quotes for it" "Like so"
        """
        if len(choices) < 2:
            return await ctx.send("You must input at least 2 choices")
        return await ctx.send(random.choice(choices),
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['cf', 'flip', 'coin'])
    async def coinFlip(self, ctx: commands.Context) -> discord.Message:
        """ Flips a VirtualCoin™ """
        return await ctx.send(random.choice([
            '<:heads:883577184499953734> Heads!',
            '<:tails:883577184273461268> Tails!'
        ]))

    @commands.command(aliases=['RandomNumber', 'dice'])
    async def roll(self, ctx: commands.Context, number: typing.Optional[int]) -> discord.Message:
        """
        Rolls a VirtualDice™ or, if specified, sends a random number
        """
        number = number if number and number > 0 else None
        if not number:
            dices = ['<:dice_1:883581027744907304>',
                     '<:dice_2:883581054626177105>',
                     '<:dice_3:883581082803511336>',
                     '<:dice_4:883581104026681365>',
                     '<:dice_5:883581129360285726>',
                     '<:dice_6:883581159412490250>']
            return await ctx.send(random.choice(dices))
        return await ctx.send(random.randint(0, number))

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

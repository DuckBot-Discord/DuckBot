import asyncio
import random
import urllib.parse

import aiowiki
import discord
import typing
from discord.ext import commands

from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers.paginator import ViewPaginator, UrbanPageSource

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
    🤪 General entertainment commands, and all other commands that don't fit within other categories.
    """

    __slots__ = ('bot',)

    def __init__(self, bot):
        self.bot: DuckBot = bot

    async def reddit(self, subreddit: str, title: bool = False, embed_type: str = 'IMAGE') -> discord.Embed:
        subreddit = await self.bot.reddit.subreddit(subreddit)
        post = await subreddit.random()

        if embed_type == 'IMAGE':
            while 'i.redd.it' not in post.url or post.over_18:
                post = await subreddit.random()

            embed = discord.Embed(color=discord.Color.random(),
                                  description=f"🌐 [Post](https://reddit.com{post.permalink}) • "
                                              f"<:upvote:274492025678856192> {post.score} ({post.upvote_ratio * 100}%) "
                                              f"• from [r/{subreddit}](https://reddit.com/r/{subreddit})")
            embed.title = post.title if title is True else None
            embed.set_image(url=post.url)
            return embed

        if embed_type == 'POLL':
            while not hasattr(post, 'poll_data') or not post.poll_data or post.over_18:
                post = await (await self.bot.reddit.subreddit(subreddit)).random()

            iterations: int = 1
            options = []
            emojis = []
            for option in post.poll_data.options:
                num = f"{iterations}\U0000fe0f\U000020e3"
                options.append(f"{num} {option.text}")
                emojis.append(num)
                iterations += 1
                if iterations > 9:
                    iterations = 1

            embed = discord.Embed(color=discord.Color.random(),
                                  description='\n'.join(options))
            embed.title = post.title if title is True else None
            return embed, emojis

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: CustomContext) -> discord.Message:
        """ Sends a random cat image from r/cats """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('cats'))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: CustomContext) -> discord.Message:
        """ Sends a random dog image from r/dog """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('dog'))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random duck image
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
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx: CustomContext) -> discord.Message:
        """
        Try it and see...
        """
        return await ctx.send("https://tryitands.ee/")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx: CustomContext) -> discord.Message:
        """
        shows a funny "inspirational" image from inspirobot.me
        """
        async with self.bot.session.get('http://inspirobot.me/api?generate=true') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.text()

        embed = discord.Embed(title='An inspirational image...',
                              color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res)
        embed.set_footer(text='by inspirobot.me',
                         icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
        return await ctx.send(embed=embed)

    @commands.command(aliases=['pp', 'eggplant', 'cucumber'])
    async def banana(self, ctx: CustomContext, member: discord.Member = None) -> discord.Message:
        """
        Measures your banana 😏
        """
        member = member or ctx.author
        scheme = random.choice([("🍆", 0x744EAA), ("🥒", 0x74AE53), ("🍌", 0xFFCD71)])
        size = random.uniform(8, 25)
        embed = discord.Embed(colour=scheme[1])
        embed.description = f"8{'=' * int(round(size, 0))}D\n\n**{member.name}**'s {scheme[0]} is {round(size, 1)} cm"
        embed.set_author(icon_url=member.display_avatar.url, name=member)
        return await ctx.send(embed=embed)

    @commands.command()
    async def meme(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random meme from reddit.com/r/memes.
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit(random.choice(['memes', 'dankmemes'])))

    @commands.command(aliases=['wyr'])
    async def would_you_rather(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random meme from reddit.com/r/WouldYouRather.
        """
        async with ctx.typing():
            poll: tuple = await self.reddit('WouldYouRather', embed_type='POLL', title=True)
            message = await ctx.send(embed=poll[0])
            for reaction in poll[1]:
                await message.add_reaction(reaction)

    @commands.command()
    async def aww(self, ctx: CustomContext) -> discord.Message:
        """
        Sends cute pic from r/aww
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit('aww'))

    @commands.command(name="8ball")
    async def _8ball(self, ctx: CustomContext, *, question: str) -> discord.Message:
        """
        Vaguely answers your question.
        """
        async with ctx.typing():
            await asyncio.sleep(0.5)
            return await ctx.send(f"**Q: {question[0:1800]}**"
                                  f"\nA: {random.choice(_8ball_answers)}")

    @commands.command()
    async def choose(self, ctx: CustomContext, *choices: str) -> discord.Message:
        """
        Chooses one random word from the list of choices you input.
        If you want multi-word choices, use "Quotes for it" "Like so"
        """
        if len(choices) < 2:
            return await ctx.send("You must input at least 2 choices")
        return await ctx.send(random.choice(choices),
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['cf', 'flip', 'coin'])
    async def coinflip(self, ctx: CustomContext) -> discord.Message:
        """ Flips a VirtualCoin™ """
        return await ctx.send(random.choice([
            '<:heads:883577184499953734> Heads!',
            '<:tails:883577184273461268> Tails!'
        ]))

    @commands.command(aliases=['RandomNumber', 'dice'])
    async def roll(self, ctx: CustomContext, number: typing.Optional[int]) -> discord.Message:
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

    @commands.command(name='urban', aliases=['ud'])
    async def _urban(self, ctx, *, word):
        """Searches urban dictionary."""

        url = 'http://api.urbandictionary.com/v0/define'
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
        text = urllib.parse.quote(text)
        await ctx.trigger_typing()
        async with self.bot.session.get(f'https://api.cool-img-api.ml/achievement?text={text}', allow_redirects=True) as r:
            return await ctx.send(r.url)

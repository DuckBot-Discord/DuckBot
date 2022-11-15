import random
import typing

import discord
from discord.ext import commands
import asyncpraw

from ._base import FunBase
from ...helpers import constants
from ...helpers.context import CustomContext


class Reddit(FunBase):
    @typing.overload
    async def reddit(self, srdt: str, title: bool = False, embed_type: typing.Literal['IMAGE'] = 'IMAGE') -> discord.Embed:
        ...

    @typing.overload
    async def reddit(
        self, srdt: str, title: bool = False, embed_type: typing.Literal['POLL'] = 'POLL'
    ) -> typing.Tuple[discord.Embed, typing.List[str]]:
        ...

    async def reddit(
        self, srdt: str, title: bool = False, embed_type: typing.Literal['IMAGE', 'POLL'] = 'IMAGE'
    ) -> typing.Union[discord.Embed, typing.Tuple]:
        try:
            subreddit: asyncpraw.reddit.Subreddit = await self.bot.reddit.subreddit(srdt)
            post = await subreddit.random()
            if not post:
                return discord.Embed(title='Could not find a post', color=discord.Color.red())

            if embed_type == 'IMAGE':
                while 'i.redd.it' not in post.url or post.over_18:
                    post = await subreddit.random()
                    if not post:
                        return discord.Embed(title='Could not find a post', color=discord.Color.red())

                embed = discord.Embed(
                    color=discord.Color.random(),
                    description=f"🌐 [Post](https://reddit.com{post.permalink}) • "
                    f"{constants.REDDIT_UPVOTE} {post.score} ({post.upvote_ratio * 100}%) "
                    f"• from [r/{subreddit}](https://reddit.com/r/{subreddit})",
                )
                embed.title = post.title if title is True else None
                embed.set_image(url=post.url)
                return embed

            elif embed_type == 'POLL':
                while not hasattr(post, 'poll_data') or not post.poll_data or post.over_18:
                    post: asyncpraw.reddit.Submission | None = await (await self.bot.reddit.subreddit(srdt)).random()
                    if not post:
                        return discord.Embed(title='Could not find a post', color=discord.Color.red())

                iterations: int = 1
                options = []
                emojis = []
                for option in post.poll_data.options:
                    num = f"{iterations}\U0000fe0f\U000020e3"
                    options.append(f"{num} {option.text}")
                    emojis.append(num)
                    iterations += 1
                    if iterations >= 9:
                        iterations = 1

                embed = discord.Embed(
                    color=discord.Color.random(), description='\n'.join(options), url=f"https://reddit.com{post.permalink}"
                )
                embed.set_footer(
                    icon_url='https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Reddit_icon.svg/2048px-Reddit_icon.svg.png',
                    text=f'From reddit.com/r/{srdt}',
                )
                embed.title = post.title if title is True else None
                return embed, emojis
        except:
            await self.bot.on_error('')
            return discord.Embed(description='Whoops! An unexpected error occurred')

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: CustomContext):
        """Sends a random cat image from r/cats"""
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('cats'))

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: CustomContext):
        """Sends a random dog image from r/dog"""
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('dog'))

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    async def meme(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random meme from r/memes
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit(random.choice(['memes', 'dankmemes'])))

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command(aliases=['wyr'])
    async def would_you_rather(self, ctx: CustomContext):
        """
        Sends a random meme from r/WouldYouRather
        """
        async with ctx.typing():
            poll: tuple = await self.reddit('WouldYouRather', embed_type='POLL', title=True)
            message = await ctx.send(embed=poll[0])
            for reaction in poll[1]:
                await message.add_reaction(reaction)

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    async def aww(self, ctx: CustomContext) -> discord.Message:
        """
        Sends cute pic from r/aww
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit('aww'))

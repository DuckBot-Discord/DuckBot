import logging
import random
import traceback
import typing

import discord
from discord.ext import commands

from ._base import FunBase
from ...helpers import constants
from ...helpers.context import CustomContext


class Reddit(FunBase):
    async def reddit(
        self, subreddit: str, title: bool = False, embed_type: str = 'IMAGE'
    ) -> typing.Union[discord.Embed, typing.Tuple]:
        try:
            subreddit = await self.bot.reddit.subreddit(subreddit)
            post = await subreddit.random()

            if embed_type == 'IMAGE':
                while 'i.redd.it' not in post.url or post.over_18:
                    post = await subreddit.random()

                embed = discord.Embed(
                    color=discord.Color.random(),
                    description=f"🌐 [Post](https://reddit.com{post.permalink}) • "
                    f"{constants.REDDIT_UPVOTE} {post.score} ({post.upvote_ratio * 100}%) "
                    f"• from [r/{subreddit}](https://reddit.com/r/{subreddit})",
                )
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

                embed = discord.Embed(color=discord.Color.random(), description='\n'.join(options))
                embed.title = post.title if title is True else None
                return embed, emojis
        except Exception as error:
            for line in "".join(traceback.format_exception(etype=None, value=error, tb=error.__traceback__)).split('\n'):
                logging.info(line)
            await self.bot.get_channel(880181130408636456).send('A reddit error occurred! Please check the console.')
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

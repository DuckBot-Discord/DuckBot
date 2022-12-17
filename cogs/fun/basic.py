import random

import asyncio
import discord
import typing
from discord.ext import commands

from ._base import FunBase
from ...helpers import constants
from ...helpers.context import CustomContext


_8ball_good = [
    'It is certain',
    'It is decidedly so',
    'Without a doubt',
    'Yes - definitely',
    'You may rely on it',
    'As I see it, yes',
    'Most likely',
    'Outlook good',
    'Yes',
    'Signs point to yes',
]

_8ball_meh = [
    'Reply hazy, try again',
    'Ask again later',
    'Better not tell you now',
    'Cannot predict now',
    'Concentrate and ask again',
]

_8ball_bad = ['Don\'t count on it', 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful']

_8ball_answers = _8ball_good + _8ball_meh + _8ball_bad


class BasicFun(FunBase):
    @commands.command(aliases=['pp', 'eggplant', 'cucumber'])
    async def banana(self, ctx: CustomContext, *, member: discord.Member = None) -> discord.Message:
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

    @commands.command(name="8ball")
    async def _8ball(self, ctx: CustomContext, *, question: str) -> discord.Message:
        """
        Vaguely answers your question.
        """
        async with ctx.typing():
            await asyncio.sleep(0.5)
            return await ctx.send(f"**Q: {question[0:1800]}**" f"\nA: {random.choice(_8ball_answers)}")

    @commands.command()
    async def choose(self, ctx: CustomContext, *choices: str) -> discord.Message:
        """
        Chooses one random word from the list of choices you input.
        If you want multi-word choices, use "Quotes for it" "Like so"
        """
        if len(choices) < 2:
            return await ctx.send("You must input at least 2 choices")
        return await ctx.send(random.choice(choices), allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['cf', 'flip', 'coin'])
    async def coinflip(self, ctx: CustomContext) -> discord.Message:
        """Flips a VirtualCoin™"""
        return await ctx.send(random.choice(constants.COINS_STRING))

    @commands.command(aliases=['random-number', 'dice'])
    async def roll(self, ctx: CustomContext, number: typing.Optional[int]) -> discord.Message:
        """
        Rolls a VirtualDice™ or, if specified, sends a random number
        """
        number = number if number and number > 0 else None
        if not number:
            return await ctx.send(random.choice(constants.DICES))
        return await ctx.send(random.randint(1, number))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx: CustomContext) -> discord.Message:
        """
        Try it and see...
        """
        return await ctx.send("https://tryitands.ee/")

    @commands.command(aliases=['cag'])
    async def catch(self, ctx: CustomContext, member: typing.Optional[discord.Member]):
        """Catches someone. 😂"""
        upper_hand = await ctx.send(constants.CAG_UP, reply=False, reminders=False)
        message: discord.Message = await self.bot.wait_for(
            'message', check=lambda m: m.channel == ctx.channel and m.author != ctx.me
        )
        if (member and message.author != member) or message.author == ctx.author:
            await ctx.message.add_reaction(random.choice(constants.DONE))
            return await upper_hand.delete()
        await ctx.send(constants.CAG_DOWN, reply=False, reminders=False)

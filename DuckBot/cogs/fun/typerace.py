import collections
import random

import asyncio

import discord
import typing
from discord.ext import commands
import async_timeout

from ._base import FunBase
from ... import errors
from ...helpers import constants
from ...helpers.context import CustomContext


class TypeRace(FunBase):

    async def message_receiver(self, channel: discord.TextChannel, content: str, timeout: int) -> collections.AsyncIterable[discord.Message]:
        def check(m: discord.Message):
            return m.channel == channel and m.content.lower() == content.lower() and not m.author.bot

        try:
            async with async_timeout.timeout(timeout):
                while True:
                    message = await self.bot.wait_for('message', timeout=timeout, check=check)
                    yield message
        except asyncio.TimeoutError:
            return

    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.command(name='type-race', aliases=['tr'], brief='Starts a type-race game. No cheating!')
    async def type_race(self, ctx: CustomContext, amount: typing.Optional[int] = 6):
        """ Starts a Type-Race game.
        Sends some random words as a sentence.
        """
        messages = []

        if 0 > amount > 25:
            raise commands.BadArgument('Amount must be between 1 and 25 words.')
        res = random.sample(constants.COMMON_WORDS, k=amount)
        words = ' '.join(res)

        inv_ch = '\u200b'
        embed = discord.Embed(title=f'{constants.TYPING_INDICATOR} Type-race:',
                              description="**Type the following words:**\n"
                                          f"```\n{inv_ch.join(words)}\n```",
                              timestamp=ctx.message.created_at)
        embed.set_footer(text=f"Results will appear in {amount * 5} seconds!")
        main = await ctx.send(embed=embed)

        async def update_message(m: discord.Message):
            if m.author.id in [msg.author.id for msg in messages]:
                return
            messages.append(m)
            try:
                await m.add_reaction('🎉')
            except discord.HTTPException:
                pass
            embed.clear_fields()
            embed.add_field(name='Results:', value='\n'.join(
                f'{m.author} ({(m.created_at - main.created_at).total_seconds()}s)' for m in messages))
            try:
                await main.edit(embed=embed)
            except discord.HTTPException:
                raise errors.NoHideout()

        async for message in self.message_receiver(content=words, channel=ctx.channel, timeout=amount * 5):
            self.bot.loop.create_task(update_message(message))

        if not messages:
            embed.add_field(name='Results:', value='No one typed anything!')
            await main.edit(embed=embed)
        else:
            await main.delete(delay=0)
            text = embed.fields[0].value
            lines = text.split('\n')

            winner_lines = []

            winner_emotes = ['🥇', '🥈', '🥉']

            for line in lines:
                try:
                    emoji = winner_emotes[lines.index(line)]
                except IndexError:
                    emoji = '🏅'
                winner_lines.append(f'{emoji} {line}')

                embed = discord.Embed(title=f'💤 Type-race game ended!',
                                      description=f"```\n{words}\n```",
                                      timestamp=ctx.message.created_at)
                embed.add_field(name='Game Winners:', value='\n'.join(winner_lines))
                embed.set_footer(text=f'{len(messages)} players got the words right!')
            await ctx.send(embed=embed, reply=False)

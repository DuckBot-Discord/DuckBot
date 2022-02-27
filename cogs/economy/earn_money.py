import asyncio
import random
import typing
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from DuckBot.errors import (
    CooldownType,
)
from ._base import EconomyBase
from .helper_classes import Wallet, DuckTrack
from .helper_functions import require_setup, reset_cooldown, refresh

if TYPE_CHECKING:
    from DuckBot.helpers.context import CustomContext
else:
    from discord.ext.commands import Context as CustomContext


class EarnMoney(EconomyBase):

    @commands.command()
    @require_setup()
    @reset_cooldown(CooldownType.WORK)
    async def work(self, ctx: CustomContext):
        """ Work to earn a bit of money. """
        async with ctx.wallet as wallet:
            amount = random.randint(20, 50)
            await wallet.add_money(amount)
            await ctx.send(random.choice(self.work_messages).format(coin=self.coin_emoji, amount=amount, currency=self.coin_name))

    @commands.command()
    @require_setup()
    @reset_cooldown(CooldownType.DAILY)
    async def daily(self, ctx: CustomContext):
        """ Gets a daily reward. """
        async with ctx.wallet as wallet:
            amount = random.randint(75, 150)
            await wallet.add_money(amount)
            await ctx.send(f"{self.coin_emoji} **{ctx.me.name}** hands you **{amount} {self.coin_name}** as your daily reward.")

    @commands.command()
    @require_setup()
    @reset_cooldown(CooldownType.WEEKLY)
    async def weekly(self, ctx: CustomContext):
        """ Gets a daily reward. """
        async with ctx.wallet as wallet:
            amount = random.randint(250, 500)
            await wallet.add_money(amount)
            await ctx.send(f"{self.coin_emoji} **{ctx.me.name}** hands you **{amount} {self.coin_name}** as your weekly reward.")

    @commands.command()
    @require_setup()
    @reset_cooldown(CooldownType.MONTHLY)
    async def monthly(self, ctx: CustomContext):
        """ Gets a daily reward. """
        async with ctx.wallet as wallet:
            amount = random.randint(500, 999)
            await wallet.add_money(amount)
            await ctx.send(f"{self.coin_emoji} **{ctx.me.name}** hands you **{amount} {self.coin_name}** as your monthly reward.")

    def bet(self, bet: typing.Union[int, str], wallet: Wallet):
        if (isinstance(bet, str) and bet != 'all') or (isinstance(bet, int) and 1 > bet > wallet.balance):
            raise commands.BadArgument(
                f'❗ You must bet an amount **between 1 and {wallet.balance} {self.coin_name}** (your current balance) or "all" for all your balance.')
        if bet == 'all':
            bet = wallet.balance
        if bet > wallet.balance:
            raise commands.BadArgument(f'❗ You cannot bet more than your current balance of **{wallet.balance} {self.coin_name}**.')
        if bet < 0:
            raise commands.BadArgument(f'❗ You cannot bet a negative amount of **{self.coin_name}**.')
        return bet

    @require_setup()
    @refresh()
    @commands.command()
    async def race(self, ctx: CustomContext, duck: int = None, bet: typing.Union[int, str] = None, fast_forward: bool = False):
        """ Makes 5 ducks race. You can bet some amount of money for one duck.
        If your duck wins, you double your money. If it looses you loose the money you just bet. """
        async with ctx.wallet as wallet:
            if not all(x is not None for x in (duck, bet)):
                raise commands.BadArgument('❗ You must pass all the arguments. '
                                           f'\n> `{ctx.clean_prefix}race <duck> <bet>` where `duck` is the duck you want to bet for, and `bet` the amount of money you want to bet.')

            if not 0 < duck < 6:
                raise commands.BadArgument('❗ There are only **five ducks** in this race!')

            bet = self.bet(bet, wallet)
            ducks = [DuckTrack(number=n, progress=p) for n, p in enumerate([0 for _ in range(5)], start=1)]

            embed = discord.Embed(title="🐣 Duck race!",
                                  description='\n'.join(map(str, ducks)))

            embed.add_field(name='Your bet:',
                            value=f'You bet **{bet} {self.coin_name}** for duck **{duck}**.')
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            if not fast_forward:
                message = await ctx.send(embed=embed, footer=False)
                embed = message.embeds[0]

            while not any(d.has_won for d in ducks):

                for racer in ducks:
                    racer.progress += random.randint(0, 3)

                embed.description = '\n'.join(map(str, ducks))
                if not any(d.has_won for d in ducks):
                    if not fast_forward:
                        await message.edit(embed=embed)
                        await asyncio.sleep(0.6)

            else:
                winners = [d for d in ducks if d.has_won]
                winning_ints = [d.number for d in winners]
                if len(winners) == 1:
                    content = f'🏆 Duck number **{winners[0].number}** won!'
                else:
                    winning_numbers = list(map(str, [d.number for d in winners]))
                    winners = "**, **".join(winning_numbers[:-2] + ["** and **".join(winning_numbers[-2:])])
                    content = f'🏆 Ducks number **{winners}** won!'

                if duck in winning_ints:
                    await wallet.add_money(bet*2)
                    content += f'\n📈 You won **{bet*2} {self.coin_name}**!'
                else:
                    await wallet.remove_money(bet)
                    content += f'\n📉 You lost **{bet} {self.coin_name}**!'

                embed.clear_fields()
                embed.add_field(name='Your bet',
                                value=f'You bet **{bet} {self.coin_name}** for duck **{duck}**.'
                                      f'\n{content}')

                if not fast_forward:
                    await message.edit(embed=embed)
                else:
                    await ctx.send(embed=embed, footer=False)

    @commands.command()
    @require_setup()
    @refresh()
    async def slots(self, ctx: CustomContext, bet: typing.Union[int, str] = None, fast: bool = False):
        """ Play a game of slots. You can bet some amount of money for one game.
        The `fast` argument fast-forwards the animation of the slots. """
        async with ctx.wallet as wallet:
            if bet is None:
                raise commands.BadArgument('❗ You must pass all the arguments. '
                                           f'\n> `{ctx.clean_prefix}slots <bet>` where `bet` is the amount of money you want to bet.')
            bet = self.bet(bet, wallet)
            choices = ['<a:1_:919539346967777320>', '<a:2_:919540321682071562>', '<a:3_:919540400107188224>']
            text = "\u200b>~~\u200b \u200b \u200b {0} \u200b \u200b {1} \u200b \u200b {2} \u200b \u200b \u200b~~<"
            embed = discord.Embed(title="🎰 Slots!", description=text.format(*choices))
            embed.add_field(name='Your bet:', value=f'You bet **{bet} {self.coin_name}**.')
            if fast is False:
                embed.colour = discord.Color.yellow()
                message = await ctx.send(embed=embed, footer=False)
                embed = message.embeds[0]
            for i in range(3):
                choices.pop(-1)
                choices.insert(i, random.choice(self.symbols))
                embed.description = text.format(*choices)
                if fast is False:
                    await asyncio.sleep(0.5)
                    await message.edit(embed=embed)

            if multiplier := self.win_multiplier(choices):
                await wallet.add_money(bet*multiplier)
                embed.clear_fields()
                embed.colour = discord.Color.green()
                em = '<:upward_stonks:739614245997641740>' if multiplier == 2 else '📈'
                embed.add_field(name='Your bet', value=f'You bet **{bet} {self.coin_name}**\n{em}You won **{multiplier}x** that!\n➕ {bet*multiplier} {self.coin_name}')
                if fast is False:
                    await message.edit(embed=embed)
                else:
                    await ctx.send(embed=embed, footer=False)
            else:
                await wallet.remove_money(bet)
                embed.clear_fields()
                embed.colour = discord.Color.red()
                embed.add_field(name='Your bet', value=f'You bet **{bet} {self.coin_name}**\n📉 You lost your money.\n➖ {bet} {self.coin_name}')
                if fast is False:
                    await message.edit(embed=embed)
                else:
                    await ctx.send(embed=embed, footer=False)

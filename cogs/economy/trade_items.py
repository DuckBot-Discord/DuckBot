import typing
from typing import TYPE_CHECKING

import typing
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ._base import EconomyBase
from .helper_classes import Wallet, OwnedItem, MemberPrompt
from .helper_functions import require_setup

if TYPE_CHECKING:
    from DuckBot.helpers.context import CustomContext
else:
    from discord.ext.commands import Context as CustomContext


# noinspection SqlResolve
class TradeItems(EconomyBase):
    @commands.max_concurrency(1, commands.BucketType.user)
    @require_setup()
    @commands.group(invoke_without_command=True)
    async def trade(self, ctx: CustomContext, *, member: discord.Member):
        """Trade with another user."""
        if member == ctx.author:
            raise commands.BadArgument('❗ You can\'t trade with yourself.')
        if member.bot:
            raise commands.BadArgument('❗ You can\'t trade with a bot.')
        if (other_wallet := await self.bot.get_wallet(member)) is None:
            raise commands.BadArgument('❗ That user doesn\'t have a wallet.')

        async with ctx.wallet.trade() as my_wallet:
            my_wallet: Wallet
            message = f'Hey {member.mention}! {ctx.author.mention} wants to trade with you.' f'\n**Do you want to trade?**'
            view = MemberPrompt(ctx, member, message)
            if not await view.prompt():
                return
            async with other_wallet.trade(my_wallet.trade_session) as other_wallet:
                other_wallet: Wallet
                embed = discord.Embed(
                    title='📜 Trading commands',
                    description='`%add` - Add an item to your trade.'
                    '\n`%remove` - Remove an item from your trade.'
                    '\n`%end` - Accept the trade.'.replace('%', f'{ctx.prefix}trade '),
                )
                await view.message.edit(
                    content=f'{member.mention}, You have accepted to trade with {ctx.author.mention}.',
                    embed=embed,
                    view=view,
                )

    @require_setup()
    @trade.command(name='add')
    async def trade_add(self, ctx: CustomContext, amount: typing.Optional[int] = 1, *, item: OwnedItem):
        """Adds an item to the trade."""
        if not ctx.wallet.trade_session:
            raise commands.BadArgument('❗ You are not trading with anyone.')
        await ctx.wallet.trade_session.add_item(ctx.wallet, item, amount)
        await ctx.send(f'➕ Added **{amount} {item.name}** to the trade.')

    @require_setup()
    @trade.command(name='remove')
    async def trade_remove(self, ctx: CustomContext, amount: typing.Optional[int] = 1, *, item: OwnedItem):
        """Removes an item from the trade."""
        if not ctx.wallet.trade_session:
            raise commands.BadArgument('❗ You are not trading with anyone.')
        await ctx.wallet.trade_session.remove_item(ctx.wallet, item, amount)

    @require_setup()
    @trade.command(name='finish', aliases=['done', 'end', 'accept', 'confirm', 'deny', 'cancel'])
    async def trade_finish(self, ctx: CustomContext):
        """Finishes the trade."""
        if not ctx.wallet.trade_session:
            raise commands.BadArgument('❗ You are not trading with anyone.')
        await ctx.wallet.trade_session.prompt(ctx)

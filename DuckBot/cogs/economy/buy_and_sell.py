import math
import math
import typing
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ._base import EconomyBase
from .helper_classes import ShopItem, OwnedItem
from .helper_functions import require_setup, refresh

if TYPE_CHECKING:
    from DuckBot.helpers.context import CustomContext
else:
    from discord.ext.commands import Context as CustomContext


# noinspection SqlResolve
class BuyAndSell(EconomyBase):

    @commands.command(name='inventory', aliases=['items', 'storagebox', 'storage-box', 'inv'])
    @require_setup()
    async def inventory(self, ctx: CustomContext, page: typing.Optional[int] = 1, *, search: str = None):
        """ View all the items in your inventory. """
        if search is not None:
            query = "SELECT inventory.item_id, item_name, price, amount FROM inventory, items WHERE SIMILARITY(item_name, $2) > 0.5 AND user_id = $3 AND items.item_id = inventory.item_id AND amount > 0 LIMIT 20 OFFSET $1"
            result = await self.bot.db.fetch(query, (page - 1) * 10, search, ctx.author.id)
        else:
            query = 'SELECT inventory.item_id, item_name, price, amount FROM items, inventory WHERE user_id = $2 AND items.item_id = inventory.item_id AND amount > 0 LIMIT 20 OFFSET $1'
            result = await self.bot.db.fetch(query, (page - 1) * 10, ctx.author.id)
        if not result and search:
            raise commands.BadArgument('❗ I couldn\'t find anything like that in your **📦 Storage Box**.')
        elif not result and page > 1:
            raise commands.BadArgument('❗ Sorry but you don\'t have that many items in your **📦 Storage Box** maybe **try a smaller page?**.')
        elif not result:
            raise commands.BadArgument('❗ Your **📦 Storage Box** is empty!')

        table = []
        for index_number, item in enumerate(result, start=((page-1)*10)+1):
            item_id, item_name, price, stock = item
            price = int(price - (price / 10))
            time = discord.utils.snowflake_time(item_id).strftime('%Y-%m-%d %H:%M:%S')
            table.append(f'[{index_number})](https://tiny.one/duckbot "ITEM ID: {item_id}\nADDED AT: {time}") **{item_name}** ◦ {price} {self.coin_name} ◦ {stock} in your inventory')

        embed = discord.Embed(title=f'📦 Your Storage Box', description='\n'.join(table), timestamp=ctx.message.created_at)
        count = await self.bot.db.fetchval("SELECT COUNT(*) FROM items")
        embed.set_footer(text=f'Page {page} / {math.ceil(count/10)}')
        await ctx.send(embed=embed)

    @commands.command(name='market', aliases=['shop', 'store'])
    @require_setup()
    async def market(self, ctx: CustomContext, page: typing.Optional[int] = 1, *, search: str = None):
        """ View the market. You can buy items with this command.
        You can also search for items by name. """
        if search is not None:
            query = ""
            result = await self.bot.db.fetch(query, (page - 1) * 10, search)
        else:
            query = 'SELECT item_id, item_name, price, stock FROM items ORDER BY stock DESC OFFSET $1 LIMIT 20'
            result = await self.bot.db.fetch(query, (page - 1) * 10)
        if not result and search:
            raise commands.BadArgument('❗ No items found with that search and/or page.')
        elif not result and page > 1:
            raise commands.BadArgument('❗ No items found at that page.')
        elif not result:
            raise commands.BadArgument('❗ No items in the market yet.')

        table = []
        for index_number, item in enumerate(result, start=((page-1)*10)+1):
            item_id, item_name, price, stock = item
            time = discord.utils.snowflake_time(item_id).strftime('%Y-%m-%d %H:%M:%S')
            table.append(f'[{index_number})](https://tiny.one/duckbot "ITEM ID: {item_id}\nADDED AT: {time}") **{item_name}** ◦ {price} {self.coin_name} ◦ {stock} in stock')

        embed = discord.Embed(title=f'🛒 {self.coin_name} Market', description='\n'.join(table), timestamp=ctx.message.created_at)
        count = await self.bot.db.fetchval("SELECT COUNT(*) FROM items")
        embed.set_footer(text=f'Page {page} / {math.ceil(count/10)}')
        await ctx.send(embed=embed)

    @commands.command(name='buy', aliases=['purchase', 'buyitem', 'purchaseitem'])
    @require_setup()
    @refresh()
    @commands.max_concurrency(1, wait=True)
    async def buy(self, ctx: CustomContext, quantity: typing.Optional[int] = 1, *, item: ShopItem):
        """ Buy an item from the market. """
        async with ctx.wallet as wallet:
            if quantity > item.stock:
                raise commands.BadArgument(f'❗ Sorry, we only have {item.stock} of that in stock.')
            if (item.price * quantity) > wallet.balance:
                raise commands.BadArgument(f'❗ Sorry, but that items costs **{item.price} {self.coin_name} each** ({item.price * quantity} total) and **you only have {wallet.balance} {self.coin_name}**.')
            await wallet.purchase_items(item, quantity)
            await ctx.send(f'Added **{quantity} {item.name}** to your **📦 Storage Box**.'
                           f'\n➖ {item.price * quantity} {self.coin_name} removed from your wallet.')

    @commands.command(name='sell', aliases=['sellitem', 'sellitems'])
    @require_setup()
    @refresh()
    async def sell(self, ctx: CustomContext, quantity: typing.Optional[int] = 1, *, item: OwnedItem):
        """ Sell an item to the market. """
        async with ctx.wallet as wallet:
            if quantity > item.inventory:
                raise commands.BadArgument(f'❗ Sorry, you only have **{item.inventory}** of that in your **📦 Storage Box**.')
            await wallet.sell_items(item, quantity)
            await ctx.send(f'Removed **{quantity} {item.name}** from your **📦 Storage Box**.'
                           f'\n➕ {math.ceil(item.price * quantity - (item.price / 6.5 * quantity))} {self.coin_name} added to your wallet.')


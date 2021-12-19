import asyncio
import contextlib
import datetime
import logging
import math
import os
import random
import typing
from collections import defaultdict
from typing import TYPE_CHECKING

import asyncpg
import discord
from discord import Interaction

from discord.ext import commands

from DuckBot.errors import (
    EconomyNotSetup,
    AccountNotFound,
    AccountAlreadyExists,
    EconomyOnCooldown,
    CooldownType,
    WalletInUse,
)

from DuckBot.helpers.time_inputs import human_timedelta

if TYPE_CHECKING:
    from DuckBot.__main__ import DuckBot
    from DuckBot.helpers.context import CustomContext
else:
    from discord.ext.commands import Bot as DuckBot, BadArgument
    from discord.ext.commands import Context as CustomContext


class MemberPrompt(discord.ui.View):
    def __init__(self, ctx: CustomContext, member: discord.Member, prompt_message: str, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.member = member
        self.ctx = ctx
        self.message: discord.Message = None
        self.value: bool = None
        self.prompt_message = prompt_message

    @discord.ui.button(label='Confirm', emoji='✅')
    async def confirm(self, _, interaction: Interaction):
        if interaction.user.id == self.member.id:
            await interaction.response.defer()
            self.value = True
            self.stop()
        else:
            await interaction.response.defer()

    @discord.ui.button(label='Deny', emoji='❌')
    async def deny(self, _, interaction: Interaction):
        if interaction.user.id == self.ctx.author.id:
            await interaction.response.edit_message(content=f"{self.ctx.author.mention}, you have cancelled the challenge.", view=None)
        else:
            await interaction.response.edit_message(content=f"{self.ctx.author.mention}, {self.member} has denied your challenge.", view=None)
        self.value = False
        self.stop()

    # Start method
    async def prompt(self) -> typing.Optional[bool]:
        self.message = await self.ctx.send(self.prompt_message, view=self)
        await self.wait()
        for i in self.children:
            i.disabled = True
        return self.value

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id in (self.ctx.author.id, self.member.id):
            return True
        await interaction.response.defer()

    async def on_timeout(self) -> None:
        await self.message.edit(content=f"{self.ctx.author.mention}, did not respond in time to the challenge!", view=None)
        self.stop()


class ShopItem:
    def __init__(self, name: str = None, iid: int = None, price: int = None, stock: int = None, inventory: int = None,
                 noises: list = None, messages: list = None):
        self.name: int = name
        self.id: int = iid
        self.price: int = price
        self.stock: int = stock
        self.inventory = inventory
        self.noises: typing.List[str] = noises or []
        self.messages: typing.List[str] = messages or []

    @classmethod
    def from_db(cls, row: dict):
        return cls(row.get('item_name'), row.get('item_id'), row.get('price'), row.get('stock'), row.get('amount'),
                   row.get('noises'), row.get('messages'))

    async def convert(self, ctx: CustomContext, argument: str):
        if argument.isdigit():
            row = await ctx.bot.db.fetchrow("SELECT * FROM items WHERE item_id = $1::int LIMIT 1", argument)
        else:
            row = await ctx.bot.db.fetchrow("SELECT * FROM items WHERE UPPER(item_name) = UPPER($1) LIMIT 1", argument)
        if not row:
            raise commands.BadArgument(f"{argument} is not in the market.")
        else:
            return self.from_db(row)


class OwnedItem(ShopItem):
    async def convert(self, ctx: CustomContext, argument: str):
        if argument.isdigit():
            row = await ctx.bot.db.fetchrow(
                "SELECT items.item_id, stock, amount, price, item_name FROM inventory, items "
                "WHERE user_id = $1 AND inventory.item_id = $2::bigint AND items.item_id = inventory.item_id",
                ctx.author.id, argument)
        else:
            row = await ctx.bot.db.fetchrow(
                "SELECT items.item_id, stock, amount, price, item_name, noises FROM inventory, items WHERE user_id = $1 AND UPPER(items.item_name) = UPPER($2) AND items.item_id = inventory.item_id LIMIT 1", ctx.author.id, argument)
        if not row:
            raise commands.BadArgument(f"❗ **{argument[0:100]}** is not in your **📦 Storage Box**.")
        else:
            item = self.from_db(row)
            if item.inventory == 0:
                raise commands.BadArgument(f"❗ **{row.get('item_name', argument[0:100])}** is not in your **📦 Storage Box**.")
            return item

    async def use(self, ctx: CustomContext):
        if self.inventory <= 0:
            raise commands.BadArgument(f"❗ **{self.name}** is not in your **📦 Storage Box**.")
        await ctx.bot.db.execute(
            "UPDATE inventory SET amount = amount - 1 WHERE user_id = $1 AND item_id = $2", ctx.author.id, self.id)
        self.inventory -= 1
        return self


class DuckTrack:
    def __init__(self, number: int, progress: int, track_length: int = 10):
        self.number = number
        self._progress = progress
        self.track_length = track_length

    @property
    def has_won(self):
        return self.progress >= self.track_length

    @property
    def progress(self):
        if self._progress > 0:
            return self._progress
        return 0

    @progress.setter
    def progress(self, value):
        self._progress = value

    def __str__(self):
        icon = '<:stay:918620043066097694>' if self.has_won else '<a:walk:918618986562867210>'
        meta = '🏅' if self.has_won else '🏁'
        return f"`{self.number}` - {meta} {'- ' * (self.track_length - self.progress)}{icon}"

    def __repr__(self):
        return f'<Dog number={self.number} progress={self.progress} ' \
               f'track_length={self.track_length}>'


class TradeSession:
    def __init__(self, main_wallet, other_wallet = None):
        self.wallet1: Wallet = main_wallet
        self.wallet2: Wallet = other_wallet
        self.items1: typing.DefaultDict[OwnedItem, int] = defaultdict(int)
        self.items2: typing.DefaultDict[OwnedItem, int] = defaultdict(int)
        self.money1: int = 0
        self.money2: int = 0
        self.closed1: bool = None
        self.closed2: bool = None
        self.lock1 = asyncio.Lock()
        self.lock2 = asyncio.Lock()

    async def end_session(self, wallet, channel: discord.TextChannel, result: bool):
        wallet: Wallet
        if wallet == self.wallet1:
            if self.closed1:
                return await channel.send(f"❗ **{wallet.user.name}**, you have already done this.")
            self.closed1 = result
        elif wallet == self.wallet2:
            if self.closed2:
                return await channel.send(f"❗ **{wallet.user.name}**, you have already done this.")
            self.closed2 = result
        if result is False:
            self.wallet1.trade_session = None
            if self.wallet2:
                self.wallet2.trade_session = None
                await channel.send(f"❗ **{wallet.user.name}** has cancelled the trade with **{self.wallet2.user}**.")
            else:
                await channel.send(f"❗ **{wallet.user.name}** has cancelled the trade.")
            return
        if self.closed1 is not None and self.closed2 is not None:
            await channel.send(f'Both **{self.wallet1.user.name}** and **{self.wallet2.user.name}** confirmed to trade. {wallet.bot.user.name} is updating all wallets and storage boxes...')
            try:
                async with self.wallet1.bot.db.acquire() as conn:
                    for item, amount in self.items1.items():
                        try:
                            await self.wallet1._remove_item(conn, item, amount)
                        except Exception as e:
                            logging.error(f"Error removing item {item.name} from {self.wallet1.user.name}'s wallet", exc_info=e)
                        try:
                            await self.wallet2._add_item(conn, item, amount)
                        except Exception as e:
                            logging.error(f"Error adding item {item.name} to {self.wallet2.user.name}'s wallet", exc_info=e)
                    for item, amount in self.items2.items():
                        try:
                            await self.wallet2._remove_item(conn, item, amount)
                        except Exception as e:
                            logging.error(f"Error removing item {item.name} from {self.wallet2.user.name}'s wallet", exc_info=e)
                        try:
                            await self.wallet1._add_item(conn, item, amount)
                        except Exception as e:
                            logging.error(f"Error adding item {item.name} to {self.wallet1.user.name}'s wallet", exc_info=e)
            finally:
                self.wallet1.trade_session = None
                self.wallet2.trade_session = None
        else:
            await channel.send(f'**{wallet.user.name}** has confirmed his trade.')

    async def prompt(self, ctx):
        if not self.wallet2:
            raise commands.BadArgument('❗ The other user has not accepted the trade yet.')
        prompt = await ctx.confirm(f'🔃 Do you want to confirm this trade?'
                                   f'\n**To continue trading, wait 15 seconds for this menu to disappear.**',
                                   timeout=15, buttons=(('✔', 'Confirm and end', discord.ButtonStyle.green),
                                                        ('❌', 'Cancel and end', discord.ButtonStyle.grey)),
                                   delete_after_confirm=True, delete_after_timeout=True)
        if prompt is not None:
            await self.end_session(ctx.wallet, ctx.channel, prompt)

    async def add_item(self, wallet, item: OwnedItem, amount: int):
        wallet: Wallet
        if wallet == self.wallet1:
            print('wallet one')
            async with self.lock1:
                if self.closed1:
                    return
                added = self.items1.get(item, 0)
                if added + amount > item.inventory:
                    raise commands.BadArgument(f'❗ You do not have enough **{item.name}**.')
                self.items1[item] += amount
        elif wallet == self.wallet2:
            print('wallet two')
            async with self.lock2:
                if self.closed2:
                    return
                added = self.items2.get(item, 0)
                if added + amount > item.inventory:
                    raise commands.BadArgument(f'❗ You do not have enough **{item.name}**.')
                self.items2[item] += amount

    async def remove_item(self, wallet, item: OwnedItem, amount: int):
        wallet: Wallet
        if wallet == self.wallet1:
            async with self.lock1:
                removed = self.items1.get(item, 0)
                if removed < amount:
                    raise commands.BadArgument(f'❗ You do not have enough **{item.name}**.')
                self.items1[item] -= amount
        elif wallet == self.wallet2:
            async with self.lock2:
                removed = self.items2.get(item, 0)
                if removed < amount:
                    raise commands.BadArgument(f'❗ The other user does not have enough **{item.name}**.')
                self.items2[item] -= amount

    def get_items(self, wallet):
        wallet: Wallet
        if wallet == self.wallet1:
            return self.items1
        elif wallet == self.wallet2:
            return self.items2

    def get_money(self, wallet):
        wallet: Wallet
        if wallet == self.wallet1:
            return self.money1
        elif wallet == self.wallet2:
            return self.money2


class Wallet:
    def __init__(self, bot: DuckBot, user: discord.User, account: asyncpg.Record):
        self.user = user
        self.bot = bot
        self.trade_session: TradeSession = None
        self.balance = account.get("balance", 0)
        self._last_worked: datetime.datetime = account.get("last_worked")
        self._last_daily: datetime.datetime = account.get("last_daily")
        self._last_weekly: datetime.datetime = account.get("last_weekly")
        self._last_monthly: datetime.datetime = account.get("last_monthly")
        self._deleted: bool = account.get('deleted', False)
        self.lock = asyncio.Lock()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.user.id == other.user.id

    async def __aenter__(self):
        if self.lock.locked():
            raise WalletInUse(self.user)
        await self.lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

    @contextlib.asynccontextmanager
    async def trade(self, session: TradeSession = None):
        if self.trade_session:
            raise WalletInUse(self.user)
        try:
            await self.lock.acquire()
            self.trade_session: TradeSession = session or TradeSession(main_wallet=self)
            if session:
                session.wallet2 = self
            yield self
        finally:
            self.lock.release()

    # Properties
    @property
    def next_work(self):
        if not self._last_worked:
            return discord.utils.utcnow()
        return self._last_worked + datetime.timedelta(minutes=10)

    @property
    def can_work(self):
        return self.next_work <= discord.utils.utcnow()

    @property
    def next_daily(self):
        if not self._last_daily:
            return discord.utils.utcnow()
        return self._last_daily + datetime.timedelta(days=1)

    @property
    def can_daily(self):
        return self.next_daily <= discord.utils.utcnow()

    @property
    def next_weekly(self):
        if not self._last_weekly:
            return discord.utils.utcnow()
        return self._last_weekly + datetime.timedelta(days=7)

    @property
    def can_weekly(self):
        return self.next_weekly <= discord.utils.utcnow()

    @property
    def next_monthly(self):
        if not self._last_monthly:
            return discord.utils.utcnow()
        return self._last_monthly + datetime.timedelta(days=30)

    @property
    def can_monthly(self):
        return self.next_monthly <= discord.utils.utcnow()

    @property
    def deleted(self):
        return self._deleted

    @deleted.setter
    def deleted(self, value):
        self._deleted = value

    # Explicit setters
    async def update_last_work(self, value: datetime.datetime = None):
        value = value or discord.utils.utcnow()
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE economy SET last_worked = $1 WHERE user_id = $2", value, self.user.id)
            self._last_worked = value

    async def update_last_daily(self, value: datetime.datetime = None):
        value = value or discord.utils.utcnow()
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE economy SET last_daily = $1 WHERE user_id = $2", value, self.user.id)
            self._last_daily = value

    async def update_last_weekly(self, value: datetime.datetime = None):
        value = value or discord.utils.utcnow()
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE economy SET last_weekly = $1 WHERE user_id = $2", value, self.user.id)
            self._last_weekly = value

    async def update_last_monthly(self, value: datetime.datetime = None):
        value = value or discord.utils.utcnow()
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE economy SET last_monthly = $1 WHERE user_id = $2", value, self.user.id)
            self._last_monthly = value

    # Money management
    async def transfer_money(self, to: discord.User, amount: int):
        async with self.bot.db.acquire() as conn:
            account = await self.bot.get_wallet(to)
            async with account as a:
                if amount > self.balance:
                    raise commands.BadArgument("You don't have enough money to do that.")
                await a._add_money(conn, amount)
                await self._remove_money(conn, amount)

    async def add_money(self, amount: int):
        async with self.bot.db.acquire() as conn:
            await self._add_money(conn, amount)

    async def remove_money(self, amount: int):
        async with self.bot.db.acquire() as conn:
            await self._remove_money(conn, amount)

    async def update_balance(self, amount: int):
        async with self.bot.db.acquire() as conn:
            await self.refresh()
            amount = amount - self.balance
            await self._add_money(conn, amount)

    async def purchase_items(self, item: ShopItem, amount: int):
        async with self.bot.db.acquire() as conn:
            if item.price * amount > self.balance:
                raise commands.BadArgument("You don't have enough money to do that.")
            if amount > item.stock:
                raise commands.BadArgument("There's not enough of that item in stock.")
            await self._purchase_items(conn, item, amount)

    async def add_items(self, item: ShopItem, amount: int):
        async with self.bot.db.acquire() as conn:
            if item.price * amount > self.balance:
                raise commands.BadArgument("You don't have enough money to do that.")
            if amount > item.stock:
                raise commands.BadArgument("There's not enough of that item in stock.")
            await self._purchase_items(conn, item, amount)

    async def sell_items(self, item: OwnedItem, amount: int):
        async with self.bot.db.acquire() as conn:
            if amount > item.inventory:
                raise commands.BadArgument("You don't have that many of that item.")
            await self._sell_items(conn, item, amount)

    async def remove_items(self, item: OwnedItem, amount: int):
        async with self.bot.db.acquire() as conn:
            if amount > item.inventory:
                raise commands.BadArgument("You don't have that many of that item.")
            await self._remove_item(conn, item, amount)

    async def refresh(self):
        async with self.bot.db.acquire() as conn:
            self.balance, self._deleted = await conn.fetchrow("SELECT balance, deleted FROM economy WHERE user_id = $1", self.user.id)

    async def _add_money(self, conn: asyncpg.Connection, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        self.balance = await conn.fetchval("UPDATE economy SET balance = $1 WHERE user_id = $2 RETURNING balance", self.balance + amount, self.user.id)

    async def _remove_money(self, conn: asyncpg.Connection, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        if amount > self.balance:
            amount = self.balance
        self.balance = await conn.fetchval("UPDATE economy SET balance = $1 WHERE user_id = $2 RETURNING balance", self.balance - amount, self.user.id)

    async def _purchase_items(self, conn: asyncpg.Connection, item: ShopItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await self._remove_money(conn, item.price * amount)
        await conn.execute('INSERT INTO inventory (user_id, item_id, amount) VALUES ($1, $2, $3)'
                           'ON CONFLICT (user_id, item_id) DO UPDATE SET amount = inventory.amount + $3',
                           self.user.id, item.id, amount)
        await conn.execute('UPDATE items SET stock = $1 WHERE item_id = $2', item.stock - amount, item.id)

    async def _sell_items(self, conn: asyncpg.Connection, item: OwnedItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await self._add_money(conn, int(item.price * amount - (item.price / 10 * amount)))
        await conn.execute('UPDATE inventory SET amount = $3 WHERE user_id = $1 AND item_id = $2', self.user.id, item.id, item.inventory - amount)
        await conn.execute('UPDATE items SET stock = stock + $1 WHERE item_id = $2', amount, item.id)

    async def _add_item(self, conn: asyncpg.Connection, item: ShopItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await conn.execute('INSERT INTO inventory (user_id, item_id, amount) VALUES ($1, $2, $3) '
                           'ON CONFLICT (user_id, item_id) DO UPDATE SET amount = inventory.amount + $3',
                           self.user.id, item.id, amount)

    async def _remove_item(self, conn: asyncpg.Connection, item: ShopItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await conn.execute('UPDATE inventory SET amount = amount - $3 WHERE user_id = $1 AND item_id = $2', self.user.id, item.id, amount)

    # Wallet management methods
    async def delete(self):
        if self._deleted:
            with contextlib.suppress(KeyError):
                del self.bot.wallets[self.user.id]
            raise AccountNotFound(self.user)
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE economy SET deleted = TRUE, "
                               "balance = 200 "
                               "where user_id = $1", self.user.id)
            self._deleted = True

    @classmethod
    async def from_context(cls, ctx: CustomContext):
        account = await ctx.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        if not account or account.get('deleted'):
            raise AccountNotFound(ctx.author)
        return cls(ctx.bot, ctx.author, account)

    @classmethod
    async def from_user(cls, bot: DuckBot, user: discord.User):
        account = await bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user.id)
        if not account or account.get('deleted'):
            raise AccountNotFound(user)
        return cls(bot, user, account)

    @classmethod
    async def create(cls, bot: DuckBot, user: discord.User):
        async with bot.db.acquire() as conn:
            try:
                account = await conn.fetchrow("INSERT INTO economy (user_id) VALUES ($1) RETURNING *", user.id)
            except asyncpg.UniqueViolationError:
                account = await conn.fetchrow("SELECT * FROM economy WHERE user_id = $1", user.id) or {}
                if account.get('deleted'):
                    account = await conn.fetchrow("UPDATE economy SET deleted = FALSE WHERE user_id = $1 RETURNING *", user.id)
                else:
                    raise AccountAlreadyExists(user)
            wallet = cls(bot, user, account)
            bot.wallets[user.id] = wallet
            return wallet


def setup(bot: DuckBot):
    bot.add_cog(Economy(bot))


def require_setup(prompt: bool = False):
    async def predicate(ctx: CustomContext):
        try:
            await ctx.get_wallet()
            if ctx.wallet.deleted:
                await ctx.wallet.delete()
            return True
        except Exception as e:
            print('error in require_setup:', e)
            raise EconomyNotSetup(prompt=prompt)

    return commands.check(predicate)


def refresh():
    async def predicate(ctx: CustomContext):
        if ctx.wallet:
            try:
                await ctx.wallet.refresh()
            except Exception as e:
                logging.error('Silently failed to refresh wallet for {}: {}'.format(ctx.author, e), exc_info=e)
        return True
    return commands.check(predicate)


def reset_cooldown(cooldown_type: CooldownType):
    async def predicate(ctx: CustomContext):
        wallet = ctx.wallet or await ctx.get_wallet()

        if cooldown_type == CooldownType.WORK:
            if not wallet.can_work:
                raise EconomyOnCooldown(cooldown_type, wallet.next_work)
            if ctx.invoked_with == 'work':
                await wallet.update_last_work()
            return True

        elif cooldown_type == CooldownType.DAILY:
            if not wallet.can_daily:
                raise EconomyOnCooldown(cooldown_type, wallet.next_daily)
            if ctx.invoked_with == 'daily':
                await wallet.update_last_daily()
            return True

        elif cooldown_type == CooldownType.WEEKLY:
            if not wallet.can_weekly:
                raise EconomyOnCooldown(cooldown_type, wallet.next_weekly)
            if ctx.invoked_with == 'weekly':
                await wallet.update_last_weekly()
            return True

        elif cooldown_type == CooldownType.MONTHLY:
            if not wallet.can_monthly:
                raise EconomyOnCooldown(cooldown_type, wallet.next_monthly)
            if ctx.invoked_with == 'monthly':
                await wallet.update_last_monthly()
            return True

        else:
            raise ValueError("Invalid cooldown type.")

    return commands.check(predicate)


class Economy(commands.Cog):
    """ 🪙 Economy commands! This is a work in progress.
    **To get started run the `%PRE%eco start` command**
    See more useful commands in the `%PRE%help eco` command. """

    def __init__(self, bot: DuckBot):
        self.symbols = ['💵', '💎', '🍇', '7️⃣', '🍉', '🍒', '\U0001fa99']
        self.bot = bot
        self.coin_name = "duckcoins"
        self.coin_emoji = "\U0001fa99"
        self.select_emoji = "\U0001fa99"
        self.select_brief = "WORK IN PROGRESS economy commands."

        # Work messages
        self.work_messages = [
            "{coin} You worked hard and earned **{amount} {currency}**.",
            "{coin} You worked and earned **{amount} {currency}**.",
            "{coin} You sold your body and earned **{amount} {currency}**.",
            "{coin} You sold some bread and earned **{amount} {currency}**.",
            "{coin} Someone bought a beer from you for **{amount} {currency}**.",
            "{coin} You did some freelancing and earned **{amount} {currency}**.",
            "{coin} An artist bought your painting for **{amount} {currency}**.",
            "{coin} You sold your soul to the devil and earned **{amount} {currency}**.",
        ]

    @require_setup()
    @refresh()
    @commands.command(name="balance", aliases=["bal", "money", "cash", 'wallet'])
    async def balance(self, ctx: CustomContext, *, user: discord.User = None):
        """ Shows your current balance. """
        if user:
            wallet = await self.bot.get_wallet(user)
            return await ctx.send(f"{self.coin_emoji} **{wallet.user}** has **{wallet.balance} {self.coin_name}**.")
        await ctx.send(f"{self.coin_emoji} **You** have **{ctx.wallet.balance} {self.coin_name}**.")

    @require_setup()
    @refresh()
    @commands.command(name="pay", aliases=["give", "transfer"])
    async def pay(self, ctx: CustomContext, user: discord.User, amount: int):
        """ Pay another user some money. """
        async with ctx.wallet as wallet:
            await wallet.transfer_money(user, amount)
            await ctx.send(f"{self.coin_emoji} **You** gave **{amount} {self.coin_name}** to **{user}**.")

    @commands.group(name='eco', aliases=['economy'], invoke_without_command=True, usage='',
                    brief='Economy management/information commands')
    async def economy(self, ctx: CustomContext, x=None):
        """ The `eco` command group. **These are mostly for statistics, information and setup of the economy.** See other economy-related, located in the `Economy` category, by running `%PRE%help Economy`. """
        if not x:
            await ctx.send_help(ctx.command)
        else:
            raise commands.BadArgument(f'Unknown subcommand "{x[0:50]}".')

    @economy.command(name='start')
    async def eco_start(self, ctx: CustomContext):
        """ Creates a wallet for the user.
        (Aka opts-in to the economy commands.) """
        await Wallet.create(ctx.bot, ctx.author)
        await ctx.send(f"{self.coin_emoji} **{ctx.me.name}** gifts you this **👛 Duck Wallet** with **200 {self.coin_emoji} {self.coin_name}** and a **📦 Storage box**.")

    @require_setup()
    @refresh()
    @economy.command(name='stop')
    async def eco_stop(self, ctx: CustomContext):
        """ Returns your wallet to the bot.
        (aka opts-out of the economy commands.) """
        async with ctx.wallet:
            if ctx.wallet.balance < 200:
                raise commands.BadArgument(f"❗ Sorry but opting out costs **200 {self.coin_name}**.")
            prompt = await ctx.confirm(f"**__Are you sure you want to do that?__**"
                                       f"\n\n{ctx.bot.constants.ARROW} This will:"
                                       f"\n- Return your **👛 Duck Wallet** the me."
                                       f"\n- Throw away your **📦 Storage Box**."
                                       f"\n\n{ctx.bot.constants.ARROW} This will **not**:"
                                       f"\n- Reset your **⏲ Cooldown**"
                                       "\n\n**This action cannot be undone.**",
                                       delete_after_confirm=True, buttons=(
                                           ('✋', 'Return wallet', discord.ButtonStyle.gray),
                                           ('🗑', None, discord.ButtonStyle.red)))
            if not prompt:
                return
            await ctx.wallet.delete()
            await ctx.send(f"{self.coin_emoji} **{ctx.me.name}** took your **👛 Duck Wallet** and thew away your **📦 Storage Box**.")

    @require_setup()
    @economy.command(name='cooldowns', aliases=['cd', 'cooldown'])
    async def eco_cd(self, ctx: CustomContext):
        """ Shows the cooldowns for the economy commands. """
        async with ctx.wallet as wallet:
            embed = discord.Embed(title="Your cooldowns")
            embed.add_field(name=f"{ctx.tick(wallet.can_work)} Work", inline=False,
                            value=f"Next available: {discord.utils.format_dt(wallet.next_work, style='R')}"
                                  f"\n(in {human_timedelta(wallet.next_work, accuracy=2)})" if not wallet.can_work
                            else "Available: Now\n(every 10 minutes)")
            embed.add_field(name=f"{ctx.tick(wallet.can_daily)} Daily", inline=False,
                            value=f"Next available: {discord.utils.format_dt(wallet.next_daily, style='R')}"
                                  f"\n(in {human_timedelta(wallet.next_daily, accuracy=2)})" if not wallet.can_daily
                            else "Available: Now\n(every 24 hours)")
            embed.add_field(name=f"{ctx.tick(wallet.can_weekly)} Weekly", inline=False,
                            value=f"Next available: {discord.utils.format_dt(wallet.next_weekly, style='R')}"
                                  f"\n(in {human_timedelta(wallet.next_weekly, accuracy=2)})" if not wallet.can_weekly
                            else "Available: Now\n(every 7 days)")
            embed.add_field(name=f"{ctx.tick(wallet.can_monthly)} Monthly", inline=False,
                            value=f"Next available: {discord.utils.format_dt(wallet.next_monthly, style='R')}"
                                  f"\n(in {human_timedelta(wallet.next_monthly, accuracy=2)})" if not wallet.can_monthly
                            else "Available: Now\n(every 30 days)")
            embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed, footer=False)

    @economy.command(name='leaderboard', aliases=['lb', 'top'])
    async def eco_leaderboard(self, ctx: CustomContext, page: int = 1):
        """ Shows the top richest users in the economy. """
        if page < 1:
            raise commands.BadArgument("Page must be greater than 0.")
        page -= 1
        count = await ctx.bot.db.fetchval("SELECT COUNT(*) FROM economy")
        if count == 0:
            raise commands.BadArgument("❗ There are no users in the economy yet.")
        users = await ctx.bot.db.fetch("SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 10 OFFSET $1", page * 10)
        if not users:
            raise commands.BadArgument("❗ That page does not exist.")
        embed = discord.Embed(title=f"Top {count} richest users (page {page+1}/{math.ceil(count / 10)})")
        leaderboard = []
        for number, entry in enumerate(users, start=page * 10 + 1):
            user = discord.utils.escape_markdown(str(ctx.bot.get_user(entry.get('user_id', 0)) or 'Unknown User'))
            leaderboard.append(f"`{number}`) **{user}** - {entry.get('balance')} {self.coin_emoji}")
        embed.description = "\n".join(leaderboard)
        max_page = page * 10 + 10
        max_page = max_page if max_page < count else count
        embed.set_footer(text=f"Showing users {page * 10 + 1}-{max_page} of {count}.")
        await ctx.send(embed=embed)

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

    @staticmethod
    def win_multiplier(bets) -> int:
        if len(set(bets)) == 1:
            return 2
        elif len(set(bets)) == 2:
            return 1
        else:
            return 0

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

    async def play_in_voice(self, ctx, file: str):
        user = ctx.author
        voice_channel = user.voice.channel if user.voice else None
        if voice_channel is None:
            return False
        if not voice_channel.permissions_for(user.guild.me).connect:
            return False
        file_name = f"./secrets/audio/{file}"
        if not os.path.exists(file_name):
            return False
        try:
            vc = await voice_channel.connect()
        except discord.errors.ClientException:
            return False
        else:
            try:
                with contextlib.suppress(discord.HTTPException):
                    await ctx.message.add_reaction('🎶')
                file = await self.bot.loop.run_in_executor(None, discord.FFmpegPCMAudio, file_name)
                vc.play(file)
                while vc.is_playing():
                    await asyncio.sleep(1)
                await asyncio.sleep(0.5)
                vc.stop()
            finally:
                await vc.disconnect()
                return True

    @require_setup()
    @commands.command()
    async def use(self, ctx: CustomContext, *, item: OwnedItem):
        """ Uses an item in your inventory. """
        async with ctx.wallet:
            used = False
            if item.noises:
                used = await self.play_in_voice(ctx, random.choice(item.noises))
                if used:
                    await item.use(ctx)
                    return await ctx.send(f'🎵 {item.name} 🎵')
            if item.messages:
                await item.use(ctx)
                await ctx.send(random.choice(item.messages))
            if used:
                return
            else:
                raise commands.BadArgument('❗ That item has no use yet.')

    @commands.max_concurrency(1, commands.BucketType.user)
    @require_setup()
    @commands.group(invoke_without_command=True)
    async def trade(self, ctx: CustomContext, *, member: discord.Member):
        """ Trade with another user. """
        if member == ctx.author:
            raise commands.BadArgument('❗ You can\'t trade with yourself.')
        if member.bot:
            raise commands.BadArgument('❗ You can\'t trade with a bot.')
        if (other_wallet := await self.bot.get_wallet(member)) is None:
            raise commands.BadArgument('❗ That user doesn\'t have a wallet.')

        async with ctx.wallet.trade() as my_wallet:
            my_wallet: Wallet
            message = f'Hey {member.mention}! {ctx.author.mention} wants to trade with you.' \
                      f'\n**Do you want to trade?**'
            view = MemberPrompt(ctx, member, message)
            if not await view.prompt():
                return
            async with other_wallet.trade(my_wallet.trade_session) as other_wallet:
                other_wallet: Wallet
                embed = discord.Embed(title='📜 Trading commands',
                                      description='`%add` - Add an item to your trade.'
                                                  '\n`%remove` - Remove an item from your trade.'
                                                  '\n`%end` - Accept the trade.'.replace('%', f'{ctx.prefix}trade '))
                await view.message.edit(content=f'{member.mention}, You have accepted to trade with {ctx.author.mention}.', embed=embed, view=view)

    @require_setup()
    @trade.command(name='add')
    async def trade_add(self, ctx: CustomContext, amount: typing.Optional[int] = 1, *, item: OwnedItem):
        """ Adds an item to the trade. """
        if not ctx.wallet.trade_session:
            raise commands.BadArgument('❗ You are not trading with anyone.')
        await ctx.wallet.trade_session.add_item(ctx.wallet, item, amount)
        await ctx.send(f'➕ Added **{amount} {item.name}** to the trade.')

    @require_setup()
    @trade.command(name='remove')
    async def trade_remove(self, ctx: CustomContext, amount: typing.Optional[int] = 1, *, item: OwnedItem):
        """ Removes an item from the trade. """
        if not ctx.wallet.trade_session:
            raise commands.BadArgument('❗ You are not trading with anyone.')
        await ctx.wallet.trade_session.remove_item(ctx.wallet, item, amount)

    @require_setup()
    @trade.command(name='finish', aliases=['done', 'end', 'accept', 'confirm', 'deny', 'cancel'])
    async def trade_finish(self, ctx: CustomContext):
        """ Finishes the trade. """
        if not ctx.wallet.trade_session:
            raise commands.BadArgument('❗ You are not trading with anyone.')
        await ctx.wallet.trade_session.prompt(ctx)

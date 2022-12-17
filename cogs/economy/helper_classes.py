from typing import TYPE_CHECKING

from discord import Interaction

if TYPE_CHECKING:
    from bot import DuckBot
    from helpers.context import CustomContext
else:
    from discord.ext.commands import Bot as DuckBot, BadArgument
    from discord.ext.commands import Context as CustomContext

import asyncio
import contextlib
import datetime
import logging
import typing
from collections import defaultdict
from typing import TYPE_CHECKING

import asyncpg
import discord

from discord.ext import commands

from errors import (
    AccountNotFound,
    AccountAlreadyExists,
    WalletInUse,
)

if TYPE_CHECKING:
    from bot import DuckBot
    from helpers.context import CustomContext
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
    async def confirm(self, interaction: Interaction, _):
        if interaction.user.id == self.member.id:
            await interaction.response.defer()
            self.value = True
            self.stop()
        else:
            await interaction.response.defer()

    @discord.ui.button(label='Deny', emoji='❌')
    async def deny(self, interaction: Interaction, _):
        if interaction.user.id == self.ctx.author.id:
            await interaction.response.edit_message(
                content=f"{self.ctx.author.mention}, you have cancelled the challenge.", view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"{self.ctx.author.mention}, {self.member} has denied your challenge.", view=None
            )
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


# noinspection SqlResolve
class ShopItem:
    def __init__(
        self,
        name: str = None,
        iid: int = None,
        price: int = None,
        stock: int = None,
        inventory: int = None,
        noises: list = None,
        messages: list = None,
    ):
        self.name: int = name
        self.id: int = iid
        self.price: int = price
        self.stock: int = stock
        self.inventory = inventory
        self.noises: typing.List[str] = noises or []
        self.messages: typing.List[str] = messages or []

    @classmethod
    def from_db(cls, row: dict):
        return cls(
            row.get('item_name'),
            row.get('item_id'),
            row.get('price'),
            row.get('stock'),
            row.get('amount'),
            row.get('noises'),
            row.get('messages'),
        )

    async def convert(self, ctx: CustomContext, argument: str):
        if argument.isdigit():
            row = await ctx.bot.db.fetchrow("SELECT * FROM items WHERE item_id = $1::int LIMIT 1", argument)
        else:
            row = await ctx.bot.db.fetchrow("SELECT * FROM items WHERE UPPER(item_name) = UPPER($1) LIMIT 1", argument)
        if not row:
            raise commands.BadArgument(f"{argument} is not in the market.")
        else:
            return self.from_db(row)


# noinspection SqlResolve
class OwnedItem(ShopItem):
    async def convert(self, ctx: CustomContext, argument: str):
        if argument.isdigit():
            row = await ctx.bot.db.fetchrow(
                "SELECT items.item_id, stock, amount, price, item_name FROM inventory, items "
                "WHERE user_id = $1 AND inventory.item_id = $2::bigint AND items.item_id = inventory.item_id",
                ctx.author.id,
                argument,
            )
        else:
            row = await ctx.bot.db.fetchrow(
                "SELECT items.item_id, stock, amount, price, item_name, noises FROM inventory, items WHERE user_id = $1 AND UPPER(items.item_name) = UPPER($2) AND items.item_id = inventory.item_id LIMIT 1",
                ctx.author.id,
                argument,
            )
        if not row:
            raise commands.BadArgument(f"❗ **{argument[0:100]}** is not in your **📦 Storage Box**.")
        else:
            item = self.from_db(row)
            if item.inventory == 0:
                raise commands.BadArgument(
                    f"❗ **{row.get('item_name', argument[0:100])}** is not in your **📦 Storage Box**."
                )
            return item

    async def use(self, ctx: CustomContext):
        if self.inventory <= 0:
            raise commands.BadArgument(f"❗ **{self.name}** is not in your **📦 Storage Box**.")
        await ctx.bot.db.execute(
            "UPDATE inventory SET amount = amount - 1 WHERE user_id = $1 AND item_id = $2", ctx.author.id, self.id
        )
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
        return f'<Dog number={self.number} progress={self.progress} ' f'track_length={self.track_length}>'


class TradeSession:
    def __init__(self, main_wallet, other_wallet=None):
        self.wallet1: Wallet = main_wallet
        self.wallet2: Wallet = other_wallet
        self.items1: typing.DefaultDict[OwnedItem, int] = defaultdict(int)
        self.items2: typing.DefaultDict[OwnedItem, int] = defaultdict(int)
        self.money1: int = 0
        self.money2: int = 0
        self.closed1: bool = None  # type: ignore
        self.closed2: bool = None  # type: ignore
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
            await channel.send(
                f'Both **{self.wallet1.user.name}** and **{self.wallet2.user.name}** confirmed to trade. {wallet.bot.user.name} is updating all wallets and storage boxes...'
            )
            try:
                async with self.wallet1.bot.db.acquire() as conn:
                    for item, amount in self.items1.items():
                        try:
                            await self.wallet1._remove_item(conn, item, amount)
                        except Exception as e:
                            logging.error(
                                f"Error removing item {item.name} from {self.wallet1.user.name}'s wallet", exc_info=e
                            )
                        try:
                            await self.wallet2._add_item(conn, item, amount)
                        except Exception as e:
                            logging.error(f"Error adding item {item.name} to {self.wallet2.user.name}'s wallet", exc_info=e)
                    for item, amount in self.items2.items():
                        try:
                            await self.wallet2._remove_item(conn, item, amount)
                        except Exception as e:
                            logging.error(
                                f"Error removing item {item.name} from {self.wallet2.user.name}'s wallet", exc_info=e
                            )
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
        prompt = await ctx.confirm(
            f'🔃 Do you want to confirm this trade?'
            f'\n**To continue trading, wait 15 seconds for this menu to disappear.**',
            timeout=15,
            buttons=(('✔', 'Confirm and end', discord.ButtonStyle.green), ('❌', 'Cancel and end', discord.ButtonStyle.grey)),
            delete_after_confirm=True,
            delete_after_timeout=True,
        )
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


# noinspection SqlResolve
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
            self.balance, self._deleted = await conn.fetchrow(
                "SELECT balance, deleted FROM economy WHERE user_id = $1", self.user.id
            )

    async def _add_money(self, conn: asyncpg.Connection, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        self.balance = await conn.fetchval(
            "UPDATE economy SET balance = $1 WHERE user_id = $2 RETURNING balance", self.balance + amount, self.user.id
        )

    async def _remove_money(self, conn: asyncpg.Connection, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        if amount > self.balance:
            amount = self.balance
        self.balance = await conn.fetchval(
            "UPDATE economy SET balance = $1 WHERE user_id = $2 RETURNING balance", self.balance - amount, self.user.id
        )

    async def _purchase_items(self, conn: asyncpg.Connection, item: ShopItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await self._remove_money(conn, item.price * amount)
        await conn.execute(
            'INSERT INTO inventory (user_id, item_id, amount) VALUES ($1, $2, $3)'
            'ON CONFLICT (user_id, item_id) DO UPDATE SET amount = inventory.amount + $3',
            self.user.id,
            item.id,
            amount,
        )
        await conn.execute('UPDATE items SET stock = $1 WHERE item_id = $2', item.stock - amount, item.id)

    async def _sell_items(self, conn: asyncpg.Connection, item: OwnedItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await self._add_money(conn, int(item.price * amount - (item.price / 10 * amount)))
        await conn.execute(
            'UPDATE inventory SET amount = $3 WHERE user_id = $1 AND item_id = $2',
            self.user.id,
            item.id,
            item.inventory - amount,
        )
        await conn.execute('UPDATE items SET stock = stock + $1 WHERE item_id = $2', amount, item.id)

    async def _add_item(self, conn: asyncpg.Connection, item: ShopItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await conn.execute(
            'INSERT INTO inventory (user_id, item_id, amount) VALUES ($1, $2, $3) '
            'ON CONFLICT (user_id, item_id) DO UPDATE SET amount = inventory.amount + $3',
            self.user.id,
            item.id,
            amount,
        )

    async def _remove_item(self, conn: asyncpg.Connection, item: ShopItem, amount: int):
        if self._deleted:
            raise AccountNotFound(self.user)
        await conn.execute(
            'UPDATE inventory SET amount = amount - $3 WHERE user_id = $1 AND item_id = $2', self.user.id, item.id, amount
        )

    # Wallet management methods
    async def delete(self):
        if self._deleted:
            with contextlib.suppress(KeyError):
                del self.bot.wallets[self.user.id]
            raise AccountNotFound(self.user)
        async with self.bot.db.acquire() as conn:
            await conn.execute("UPDATE economy SET deleted = TRUE, " "balance = 200 " "where user_id = $1", self.user.id)
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
                    account = await conn.fetchrow(
                        "UPDATE economy SET deleted = FALSE WHERE user_id = $1 RETURNING *", user.id
                    )
                else:
                    raise AccountAlreadyExists(user)
            wallet = cls(bot, user, account)
            bot.wallets[user.id] = wallet
            return wallet
